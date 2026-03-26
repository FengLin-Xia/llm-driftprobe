from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .base import BaseChatAdapter, ChatRequest, ChatResponse, ChatMessage


def _build_prompt(tokenizer: Any, messages: List[ChatMessage]) -> str:
    """
    尽量使用 tokenizer 的 chat template；否则回退到简单拼接。
    Qwen 系列 tokenizer 通常支持 apply_chat_template。
    """
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # fallback：role/content 直接拼接（不保证兼容所有模型）
    parts: List[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"{role}: {content}")
    parts.append("assistant:")
    return "\n".join(parts)


class TransformersLocalAdapter(BaseChatAdapter):
    """
    本地直接加载模型进行推理。

    注意：
    - 这个 adapter 不依赖 Ollama。
    - 是否用 GPU、dtype、量化等需要你后续根据实际环境调整（v0 skeleton 先保证结构）。
    """

    def __init__(
        self,
        *,
        model_name_or_path: str,
        device: str = "auto",
        torch_dtype: str = "auto",
        default_max_new_tokens: int = 512,
    ) -> None:
        self._model_name_or_path = model_name_or_path
        self._default_max_new_tokens = default_max_new_tokens

        if device == "auto":
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self._device = device

        if torch_dtype == "auto":
            self._dtype = torch.float16 if self._device == "cuda" else torch.float32
        else:
            self._dtype = getattr(torch, torch_dtype)

        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name_or_path, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_name_or_path,
            torch_dtype=self._dtype,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        self._model.to(self._device)
        self._model.eval()
        # v0：为了降低推理过程的显存/内存峰值，关闭 KV cache
        if hasattr(self._model.config, "use_cache"):
            self._model.config.use_cache = False

    async def chat(self, request: ChatRequest, *, timeout: Optional[float] = None) -> ChatResponse:
        # transformers 推理是同步的，放到线程避免阻塞事件循环（runner 后续用 asyncio）
        return await asyncio.to_thread(self._chat_sync, request)

    def _chat_sync(self, request: ChatRequest) -> ChatResponse:
        messages = request["messages"]
        prompt = _build_prompt(self._tokenizer, messages)

        inputs = self._tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        max_new_tokens = int(request.get("max_tokens", self._default_max_new_tokens))
        temperature = float(request.get("temperature", 0.7))

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=temperature if temperature > 0 else None,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        input_len = inputs["input_ids"].shape[-1]
        gen_ids = output_ids[0][input_len:]
        content = self._tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

        # 显式释放张量，降低长跑时的内存残留（主要对 GPU）
        try:
            del output_ids
            del gen_ids
            del inputs
        except Exception:
            pass
        if self._device == "cuda":
            torch.cuda.empty_cache()

        return ChatResponse(
            provider=request.get("provider", "local/transformers"),
            model=request["model"],
            content=content,
        )


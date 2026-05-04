from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .base import BaseChatAdapter, ChatRequest, ChatResponse


class OpenAILikeAdapter(BaseChatAdapter):
    """OpenAI-compatible chat completions adapter."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        provider_name: str = "openai_compatible",
        default_model: str = "provider-selected",
        default_timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_timeout = default_timeout
        self._client = httpx.AsyncClient(timeout=default_timeout)
        self.provider_name = provider_name
        self.model_name = default_model
        self.supports_stream = False
        self.supports_tools = False
        self.supports_search = False
        self.supports_reasoning_summary = False

    async def chat(self, request: ChatRequest, *, timeout: Optional[float] = None) -> ChatResponse:
        url = f"{self._base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": request["model"],
            "messages": request["messages"],
            "temperature": request.get("temperature", 0.7),
            "max_tokens": request.get("max_tokens", 600),
        }

        resp = await self._client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout or self._default_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]

        return ChatResponse(
            provider=self.provider_name,
            model=request["model"],
            content=content,
            raw=data,
        )


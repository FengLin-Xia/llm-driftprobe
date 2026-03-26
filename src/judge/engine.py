from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List

from ..adapters.base import BaseChatAdapter, ChatMessage
from .prompt import JUDGE_SYSTEM_PROMPT


@dataclass
class JudgeConfig:
    model: str


class JudgeEngine:
    """使用本地 Qwen2.5-7B 对单轮对话打标签。"""

    def __init__(self, adapter: BaseChatAdapter, config: JudgeConfig) -> None:
        self._adapter = adapter
        self._config = config

    async def label_turn(
        self,
        *,
        case_id: str,
        turn_index: int,
        transcript_snippet: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        v0 最小实现：
        - 将 transcript_snippet 格式化成 prompt
        - 调用本地模型，尽量解析 JSON（容错解析：抓取 {...}）
        """
        # 取当前轮附近上下文：snippet 里包含 user_message/assistant_message
        # 注意：snippet 不要求严格只包含当前轮，judge 会自行判断
        last_turns = transcript_snippet[-2:] if transcript_snippet else []

        lines: List[str] = []
        max_chars_each = 800  # judge 只需要片段证据，不需要完整长文本
        for t in last_turns:
            um = t.get("user_message", "")
            am = t.get("assistant_message", "")
            ti = t.get("turn_index", "?")
            um_short = (um or "")[:max_chars_each]
            am_short = (am or "")[:max_chars_each]
            lines.append(f"Turn {ti} user_message:\n{um_short}")
            lines.append(f"Turn {ti} assistant_message:\n{am_short}")

        user_prompt = f"""
case_id: {case_id}
turn_index: {turn_index}

对话片段：
{chr(10).join(lines)}

输出 JSON（只包含 label 字段 + evidence）
""".strip()

        messages: List[ChatMessage] = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        resp = await self._adapter.chat(
            {
                "provider": "local/transformers",
                "model": self._config.model,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 128,
            }
        )

        text = (resp.get("content") or "").strip()
        parsed = self._try_parse_json(text)
        if not parsed:
            # 如果解析失败，返回“全 0 / null”，保证 pipeline 不崩
            return {
                "addressed_current_turn": 0,
                "obeyed_scope_constraint": 0,
                "monologue": 0,
                "flattery": 0,
                "repair_attempt": 0,
                "fake_repair": 0,
                "context_recall": None,
                "continuity_masking": 0,
                "evidence": [],
            }

        # 保障字段齐全（缺失则补 0/null）
        return {
            "addressed_current_turn": int(parsed.get("addressed_current_turn", 0) or 0),
            "obeyed_scope_constraint": int(parsed.get("obeyed_scope_constraint", 0) or 0),
            "monologue": int(parsed.get("monologue", 0) or 0),
            "flattery": int(parsed.get("flattery", 0) or 0),
            "repair_attempt": int(parsed.get("repair_attempt", 0) or 0),
            "fake_repair": int(parsed.get("fake_repair", 0) or 0),
            "context_recall": parsed.get("context_recall", None),
            "continuity_masking": int(parsed.get("continuity_masking", 0) or 0),
            "evidence": parsed.get("evidence", []) or [],
        }

    def _try_parse_json(self, text: str) -> Dict[str, Any]:
        # 快速路径：纯 JSON
        try:
            v = json.loads(text)
            if isinstance(v, dict):
                return v
        except Exception:
            pass

        # 容错：抓取 {...}
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}

        candidate = text[start : end + 1]
        try:
            v = json.loads(candidate)
            if isinstance(v, dict):
                return v
        except Exception:
            return {}

        return {}


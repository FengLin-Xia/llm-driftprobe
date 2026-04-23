from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional

from ..adapters.base import BaseChatAdapter, ChatMessage
from .prompt import ACTOR_SYSTEM_PROMPT


@dataclass
class ActorConfig:
    model: str


class ActorEngine:
    """使用本地 Qwen2.5-7B（transformers 直接加载）生成下一轮 user_message。"""

    def __init__(self, adapter: BaseChatAdapter, config: ActorConfig) -> None:
        self._adapter = adapter
        self._config = config

    async def choose_action_and_utterance(
        self,
        *,
        case_spec: Dict[str, Any],
        transcript: List[Dict[str, Any]],
        current_state: str,
    ) -> Dict[str, Any]:
        """
        TODO v0.1:
        - 将 case_spec/current_state/transcript 格式化成 prompt
        - 调用本地模型，解析 JSON
        """
        allowed_actions = case_spec.get("allowed_actions", [])
        states_obj = case_spec.get("states") or {}
        state_obj = states_obj.get(current_state) or {}
        state_desc = state_obj.get("description", "")
        goal = case_spec.get("goal", "")
        recent_user_messages = [str(t.get("user_message", "")).strip() for t in transcript[-3:] if t.get("user_message")]

        # 列出所有合法 state 供 actor 选择（修复：之前 prompt 里缺这个，导致 actor 输出无效 state）
        states_lines = [
            f"  {sid}: {(sdata or {}).get('description', '')}"
            for sid, sdata in states_obj.items()
        ]
        states_block = "\n".join(states_lines) if states_lines else "(未指定)"
        recent_user_block = "\n".join(f"- {m}" for m in recent_user_messages) if recent_user_messages else "(无)"

        # 只给最近两轮对话，降低 token 成本 + 提升稳定性
        last_turns = transcript[-2:]
        history_lines: List[str] = []
        max_chars_each = 500
        for t in last_turns:
            um = t.get("user_message", "")
            am = t.get("assistant_message", "")
            um_short = (um or "")[:max_chars_each]
            am_short = (am or "")[:max_chars_each]
            history_lines.append(f"用户: {um_short}")
            history_lines.append(f"助手: {am_short}")
        history_block = "\n".join(history_lines) if history_lines else "(无)"

        user_prompt = f"""
Case 目标：
{goal}

当前 state：{current_state}
描述：{state_desc}

允许的动作（chosen_action 必须从中选一个）：
{', '.join(allowed_actions) if allowed_actions else '(未指定，允许任意动作)'}

可选的下一状态（state 字段必须从中选一个）：
{states_block}

到目前为止的最近两轮对话：
{history_block}

最近几轮你已经生成过的 user_message（避免重复）：
{recent_user_block}

任务：
1) 选择下一步动作 chosen_action
2) 生成面向目标模型的 user_message（中文）
3) 选择下一状态 state（必须是上面列出的 state ID 之一）

额外约束：
- 不要与“最近几轮已生成 user_message”完全相同。
- 在语义保持一致的前提下，优先使用不同表达和句式。

输出必须是严格 JSON（不能包含任何额外解释文字）。
""".strip()

        messages: List[ChatMessage] = [
            {"role": "system", "content": ACTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        resp = await self._adapter.chat(
            {
                "provider": "local/transformers",
                "model": self._config.model,
                "messages": messages,
                "temperature": 0.35,
                "max_tokens": 128,
            }
        )

        text = (resp.get("content") or "").strip()
        parsed = self._try_parse_json(text)
        parse_ok = bool(parsed)

        # 最小容错：保证字段存在
        chosen_action = parsed.get("chosen_action") if isinstance(parsed, dict) else None
        user_message = parsed.get("user_message") if isinstance(parsed, dict) else None
        next_state = parsed.get("state") if isinstance(parsed, dict) else None

        if not chosen_action and allowed_actions:
            chosen_action = allowed_actions[0]
        if not chosen_action:
            chosen_action = "end_conversation"

        if allowed_actions and chosen_action not in allowed_actions:
            chosen_action = allowed_actions[0]

        if not user_message:
            user_message = "好的，请继续。"

        if next_state and (next_state in (case_spec.get("states") or {})):
            state_out = next_state
        else:
            state_out = current_state

        # 若与最近 user_message 完全重复，触发一次重采样，提升多样性。
        normalized_recent = {self._normalize_msg(x) for x in recent_user_messages if x}
        duplicate_retry_used = False
        if normalized_recent and self._normalize_msg(user_message) in normalized_recent:
            duplicate_retry_used = True
            retry_prompt = (
                user_prompt
                + "\n\n上一次输出与历史重复。请改写成明显不同句式，但保持 case 目标与动作一致。"
            )
            retry_messages: List[ChatMessage] = [
                {"role": "system", "content": ACTOR_SYSTEM_PROMPT},
                {"role": "user", "content": retry_prompt},
            ]
            retry_resp = await self._adapter.chat(
                {
                    "provider": "local/transformers",
                    "model": self._config.model,
                    "messages": retry_messages,
                    "temperature": 0.65,
                    "max_tokens": 160,
                }
            )
            retry_text = (retry_resp.get("content") or "").strip()
            retry_parsed = self._try_parse_json(retry_text)
            if isinstance(retry_parsed, dict):
                retry_action = retry_parsed.get("chosen_action")
                retry_message = retry_parsed.get("user_message")
                retry_state = retry_parsed.get("state")

                if retry_action and (not allowed_actions or retry_action in allowed_actions):
                    chosen_action = retry_action
                if retry_message and self._normalize_msg(retry_message) not in normalized_recent:
                    user_message = retry_message
                if retry_state and (retry_state in (case_spec.get("states") or {})):
                    state_out = retry_state

        return {
            "state": state_out,
            "chosen_action": chosen_action,
            "user_message": user_message,
            "_actor_meta": {
                "parse_ok": parse_ok,
                "duplicate_retry_used": duplicate_retry_used,
            },
        }

    def _try_parse_json(self, text: str) -> Dict[str, Any]:
        """
        容错解析：尽量从文本中抽取 {...} 并 json.loads。
        """
        # 快速路径：如果已经是纯 JSON
        try:
            v = json.loads(text)
            if isinstance(v, dict):
                return v
        except Exception:
            pass

        # 尝试抽取首尾大括号
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

    def _normalize_msg(self, text: str) -> str:
        """用于判重的轻量归一化。"""
        return " ".join((text or "").strip().split())


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

        # 列出所有合法 state 供 actor 选择（修复：之前 prompt 里缺这个，导致 actor 输出无效 state）
        states_lines = [
            f"  {sid}: {(sdata or {}).get('description', '')}"
            for sid, sdata in states_obj.items()
        ]
        states_block = "\n".join(states_lines) if states_lines else "(未指定)"

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

任务：
1) 选择下一步动作 chosen_action
2) 生成面向目标模型的 user_message（中文）
3) 选择下一状态 state（必须是上面列出的 state ID 之一）

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
                "temperature": 0.2,
                "max_tokens": 128,
            }
        )

        text = (resp.get("content") or "").strip()
        parsed = self._try_parse_json(text)

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

        return {
            "state": state_out,
            "chosen_action": chosen_action,
            "user_message": user_message,
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


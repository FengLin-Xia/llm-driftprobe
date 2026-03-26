from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ChatMessage(Dict[str, Any]):
    """
    统一的消息结构：
    {
        "role": "system" | "user" | "assistant",
        "content": "..."
    }
    """


class ChatRequest(Dict[str, Any]):
    """
    统一的调用结构：
    {
        "provider": "openrouter",
        "model": "anthropic/claude-3.7-sonnet",
        "messages": [ChatMessage, ...],
        "temperature": 0.7,
        "max_tokens": 600,
    }
    """


class ChatResponse(Dict[str, Any]):
    """
    统一的返回结构（v0 简化）：
    {
        "provider": "...",
        "model": "...",
        "content": "...",  # assistant 文本
        "raw": {...},      # provider 原始返回（可选）
    }
    """


class BaseChatAdapter(ABC):
    """所有外部/本地模型适配器的抽象基类。"""

    @abstractmethod
    async def chat(self, request: ChatRequest, *, timeout: Optional[float] = None) -> ChatResponse:
        raise NotImplementedError


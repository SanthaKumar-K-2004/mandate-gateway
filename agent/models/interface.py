"""
S02.1 — Model Provider Adapter Interface & Dataclass Schema.

Defines abstract boundary protocol and request/response models for LLM integration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent.graph.types import AgentMessage


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Model invocation parameters and hyper-parameters."""

    model_name: str = "test-model-v1"
    temperature: float = 0.0
    max_tokens: int = 1000
    timeout_seconds: float = 10.0


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Structured LLM request container."""

    messages: list[AgentMessage]
    available_tools: list[dict[str, Any]] = field(default_factory=list)
    config: ModelConfig = field(default_factory=ModelConfig)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Structured LLM response container."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"  # "stop", "tool_calls", "content_filter", "error"
    raw_response: dict[str, Any] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: datetime = field(default_factory=_utc_now)


class ModelAdapterInterface(ABC):
    """Abstract model adapter interface insulating domain runtime from specific LLM providers."""

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        """
        Generate a response for the model request.

        Must raise AgentModelError on provider failure or timeout.
        """
        pass

"""
S02.1 — Deterministic Test Model Adapter.

Provides fully offline, reproducible, scripted model responses for unit, integration,
security, and failure-injection testing.
"""

from __future__ import annotations

from typing import Callable

from agent.graph.errors import AgentModelError, AgentTimeoutError
from agent.models.interface import ModelAdapterInterface, ModelRequest, ModelResponse


class TestModelAdapter(ModelAdapterInterface):
    """
    Deterministic mock model adapter for testing S02.1 graph execution without network access.
    """

    def __init__(self) -> None:
        self._scripted_responses: list[ModelResponse] = []
        self._response_generator: Callable[[ModelRequest], ModelResponse] | None = None
        self._simulate_timeout: bool = False
        self._simulate_model_failure: bool = False
        self._failure_message: str = "Simulated model provider error"
        self.request_history: list[ModelRequest] = []

    def set_scripted_responses(self, responses: list[ModelResponse]) -> None:
        """Configure a sequence of scripted ModelResponse objects."""
        self._scripted_responses = list(responses)

    def set_response_generator(self, generator: Callable[[ModelRequest], ModelResponse]) -> None:
        """Set a dynamic request-to-response generator callback."""
        self._response_generator = generator

    def set_simulate_timeout(self, enabled: bool = True) -> None:
        """Simulate a model request timeout."""
        self._simulate_timeout = enabled

    def set_simulate_model_failure(
        self, enabled: bool = True, message: str = "Simulated model provider error"
    ) -> None:
        """Simulate a model provider failure."""
        self._simulate_model_failure = enabled
        self._failure_message = message

    def reset(self) -> None:
        """Reset history and configuration."""
        self._scripted_responses.clear()
        self._response_generator = None
        self._simulate_timeout = False
        self._simulate_model_failure = False
        self.request_history.clear()

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate response from scripted queue or dynamic generator."""
        self.request_history.append(request)

        if self._simulate_timeout:
            raise AgentTimeoutError("Model provider request timed out.")

        if self._simulate_model_failure:
            raise AgentModelError(self._failure_message)

        if self._response_generator is not None:
            return self._response_generator(request)

        if self._scripted_responses:
            return self._scripted_responses.pop(0)

        # Default fallback response
        return ModelResponse(
            content="Standard deterministic test model response.",
            finish_reason="stop",
        )

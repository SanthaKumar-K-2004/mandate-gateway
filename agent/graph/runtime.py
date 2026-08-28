"""
S02.1 — Agent Runtime & Bounded Execution Engine.

Orchestrates the agent graph loop with strict iteration bounds, tool limits, timeout handling,
cancellation support, infinite loop detection, and fail-closed security guarantees.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from agent.graph.errors import (
    AgentCancellationError,
    AgentError,
    AgentLoopLimitExceededError,
    AgentSecurityViolationError,
    AgentStateTransitionError,
    AgentTimeoutError,
    AgentToolLimitExceededError,
)
from agent.graph.nodes import (
    NodeFinalize,
    NodePlanning,
    NodePrepareProposal,
    NodeProcessToolResult,
    NodeReceiveInput,
    NodeToolExecution,
)
from agent.graph.state import AgentState
from agent.graph.types import AgentConfig, AgentStateEnum
from agent.models.interface import ModelAdapterInterface
from agent.tools.registry import ToolRegistry

logger = logging.getLogger("mandate_gateway.agent")


class AgentRuntime:
    """
    Bounded execution runtime for stateful agent graphs.

    Enforces:
    1. Maximum iteration limits.
    2. Maximum tool invocation limits.
    3. Wall-clock timeout limits.
    4. Explicit cancellation checking.
    5. Infinite tool loop detection.
    6. Context isolation and prompt injection defense.
    """

    def __init__(
        self,
        model_adapter: ModelAdapterInterface,
        tool_registry: ToolRegistry,
        config: AgentConfig | None = None,
    ) -> None:
        self.model_adapter: ModelAdapterInterface = model_adapter
        self.tool_registry: ToolRegistry = tool_registry
        self.config: AgentConfig = config or AgentConfig()

    def run(
        self,
        state: AgentState,
        user_prompt: str,
        cancellation_token: dict[str, bool] | None = None,
    ) -> AgentState:
        """
        Execute the bounded agent graph loop from user prompt input to completion or failure.

        Returns updated AgentState.
        """
        start_time = time.monotonic()
        tool_history_tracker: list[str] = []

        try:
            # Step 1: Receive Input
            NodeReceiveInput.process(state, user_prompt)

            # Execution Loop
            while not state.current_state.is_terminal:
                # Check 1: Cancellation Token
                if cancellation_token and cancellation_token.get("cancelled", False):
                    state.transition_to(AgentStateEnum.CANCELLED, detail="Cancelled by user/system signal")
                    state.set_failure_reason("Execution cancelled by token")
                    raise AgentCancellationError("Agent execution was explicitly cancelled.")

                # Check 2: Wall-clock Timeout
                elapsed = time.monotonic() - start_time
                if elapsed > self.config.timeout_seconds:
                    state.transition_to(AgentStateEnum.TIMED_OUT, detail=f"Timeout of {self.config.timeout_seconds}s exceeded")
                    state.set_failure_reason(f"Timeout of {self.config.timeout_seconds}s exceeded")
                    raise AgentTimeoutError(f"Agent execution timed out after {elapsed:.2f}s.")

                # Check 3: Max Iteration Limit
                curr_iter = state.increment_iteration()
                if curr_iter > self.config.max_iterations:
                    state.transition_to(AgentStateEnum.FAILED, detail=f"Exceeded max iterations ({self.config.max_iterations})")
                    state.set_failure_reason(f"Exceeded max iterations ({self.config.max_iterations})")
                    raise AgentLoopLimitExceededError(
                        f"Execution loop exceeded maximum allowed iterations ({self.config.max_iterations})."
                    )

                # Node Execution Branching
                current = state.current_state

                if current == AgentStateEnum.PLANNING:
                    NodePlanning.process(state, self.model_adapter, self.tool_registry)

                elif current == AgentStateEnum.TOOL_REQUESTED:
                    # Check 4: Max Tool Call Limit
                    if state.tool_call_count >= self.config.max_tool_calls:
                        state.transition_to(AgentStateEnum.FAILED, detail=f"Exceeded max tool calls ({self.config.max_tool_calls})")
                        state.set_failure_reason(f"Exceeded max tool calls ({self.config.max_tool_calls})")
                        raise AgentToolLimitExceededError(
                            f"Exceeded maximum allowed tool invocations ({self.config.max_tool_calls})."
                        )

                    # Check 5: Infinite Tool Loop Detection (3 duplicate calls in sequence)
                    pending = state.pending_tool_call or {}
                    tool_sig = f"{pending.get('name')}:{pending.get('arguments')}"
                    tool_history_tracker.append(tool_sig)
                    if len(tool_history_tracker) >= 3 and tool_history_tracker[-3:] == [tool_sig, tool_sig, tool_sig]:
                        state.transition_to(AgentStateEnum.FAILED, detail="Infinite loop detected in tool requests")
                        state.set_failure_reason("Infinite tool loop detected")
                        raise AgentSecurityViolationError(
                            f"Infinite loop detected for tool request {pending.get('name')!r}."
                        )

                    NodeToolExecution.process(state, self.tool_registry)

                elif current == AgentStateEnum.PROCESSING_TOOL_RESULT:
                    NodeProcessToolResult.process(state)

                elif current == AgentStateEnum.PROPOSAL_READY:
                    NodePrepareProposal.process(state)

                elif current == AgentStateEnum.WAITING_FOR_GATEWAY:
                    NodeFinalize.process(state, success=True, reason="Proposal ready for gateway")
                    break

                else:
                    NodeFinalize.process(state, success=False, reason=f"Unhandled runtime state {current.value}")
                    break

            return state

        except (
            AgentCancellationError,
            AgentTimeoutError,
            AgentLoopLimitExceededError,
            AgentToolLimitExceededError,
            AgentSecurityViolationError,
            AgentStateTransitionError,
        ) as e:
            logger.warning(f"Agent runtime stopped due to controlled error: {e}")
            if not state.current_state.is_terminal:
                try:
                    state.transition_to(AgentStateEnum.FAILED, detail=str(e))
                except Exception:
                    pass
            state.set_failure_reason(str(e))
            raise

        except Exception as e:
            logger.error(f"Unhandled exception during agent execution: {e}")
            if not state.current_state.is_terminal:
                try:
                    state.transition_to(AgentStateEnum.FAILED, detail=f"Unhandled error: {e}")
                except Exception:
                    pass
            state.set_failure_reason(str(e))
            raise AgentError(f"Agent execution failed: {e}")

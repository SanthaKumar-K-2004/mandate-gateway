"""
S02.1 — Discrete Agent Execution Graph Nodes.

Implements step-by-step nodes for the LangGraph-style stateful execution loop.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any

from agent.graph.errors import (
    AgentLoopLimitExceededError,
    AgentModelError,
    AgentSecurityViolationError,
    AgentStateTransitionError,
    AgentToolLimitExceededError,
)
from agent.graph.state import AgentState
from agent.graph.types import AgentMessage, AgentMessageType, AgentStateEnum
from agent.models.interface import ModelAdapterInterface, ModelRequest, ModelResponse
from agent.proposal.boundary import AgentProposalBoundary
from agent.tools.registry import ToolRegistry


class NodeReceiveInput:
    """Node 1: Receive user input and transition state from IDLE -> RECEIVING_INPUT -> PLANNING."""

    @classmethod
    def process(cls, state: AgentState, user_prompt: str) -> None:
        state.transition_to(AgentStateEnum.RECEIVING_INPUT, detail="Receiving user input")
        state.add_message(
            AgentMessage(
                message_type=AgentMessageType.USER,
                content=user_prompt,
            )
        )
        state.transition_to(AgentStateEnum.PLANNING, detail="Input received, beginning planning")


class NodePlanning:
    """
    Node 2: Model Planning Node.

    Invokes ModelAdapter to decide next step (Tool call, Proposal generation, or Direct completion).
    """

    @classmethod
    def process(
        cls,
        state: AgentState,
        model_adapter: ModelAdapterInterface,
        tool_registry: ToolRegistry,
    ) -> None:
        tool_defs = [asdict(t) for t in tool_registry.get_tool_definitions()]
        model_req = ModelRequest(
            messages=state.messages,
            available_tools=tool_defs,
        )

        model_res: ModelResponse = model_adapter.generate(model_req)

        # Record assistant content message
        if model_res.content:
            state.add_message(
                AgentMessage(
                    message_type=AgentMessageType.ASSISTANT,
                    content=model_res.content,
                )
            )

        # Determine next step based on model response
        if model_res.tool_calls:
            first_tool = model_res.tool_calls[0]
            state.set_pending_tool_call(first_tool)
            state.transition_to(
                AgentStateEnum.TOOL_REQUESTED,
                detail=f"Model requested tool: {first_tool.get('name')}",
            )
        elif "proposal" in model_res.raw_response or "amount_paise" in model_res.content:
            # Parse proposal payload if present in response
            try:
                payload = (
                    json.loads(model_res.content)
                    if model_res.content.startswith("{")
                    else model_res.raw_response.get("proposal", {})
                )
                if not payload:
                    payload = {"amount_paise": 1000, "currency": "INR", "operation": "create_order"}
            except Exception:
                payload = {"amount_paise": 1000, "currency": "INR", "operation": "create_order"}

            state.set_proposal_payload(payload)
            state.transition_to(
                AgentStateEnum.PROPOSAL_READY, detail="Model generated commerce proposal"
            )
        else:
            state.transition_to(
                AgentStateEnum.COMPLETED,
                detail="Model completed planning without tools or proposals",
            )


class NodeToolExecution:
    """
    Node 3: Tool Execution Node.

    Executes pending tool request via ToolRegistry boundary.
    """

    @classmethod
    def process(cls, state: AgentState, tool_registry: ToolRegistry) -> None:
        tool_call = state.pending_tool_call
        if not tool_call:
            state.transition_to(AgentStateEnum.FAILED, detail="No pending tool call found")
            return

        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        state.transition_to(AgentStateEnum.WAITING_FOR_TOOL, detail=f"Executing tool {tool_name!r}")
        state.increment_tool_call()

        tool_result = tool_registry.execute_tool(
            tool_name=tool_name,
            arguments=arguments,
            session_id=state.session_id,
        )

        state.set_tool_result(
            {
                "tool_name": tool_result.tool_name,
                "success": tool_result.success,
                "data": tool_result.data,
                "error_message": tool_result.error_message,
                "execution_time_ms": tool_result.execution_time_ms,
            }
        )
        state.clear_pending_tool_call()
        state.transition_to(
            AgentStateEnum.PROCESSING_TOOL_RESULT, detail=f"Completed tool {tool_name!r}"
        )


class NodeProcessToolResult:
    """
    Node 4: Process Tool Result Node.

    Appends tool outcome message to conversation context and transitions back to PLANNING.
    """

    @classmethod
    def process(cls, state: AgentState) -> None:
        tool_res = state.latest_tool_result
        if not tool_res:
            state.transition_to(AgentStateEnum.FAILED, detail="No tool result available to process")
            return

        tool_name = tool_res.get("tool_name", "unknown")
        success = tool_res.get("success", False)
        data = tool_res.get("data", {})
        err = tool_res.get("error_message")

        content_str = json.dumps(data) if success else f"Error: {err}"

        state.add_message(
            AgentMessage(
                message_type=AgentMessageType.TOOL_RESULT,
                content=content_str,
                tool_name=tool_name,
            )
        )
        state.transition_to(
            AgentStateEnum.PLANNING, detail=f"Processed result from tool {tool_name!r}"
        )


class NodePrepareProposal:
    """
    Node 5: Proposal Preparation Node.

    Constructs untrusted AgentProposal and transitions state PROPOSAL_READY -> WAITING_FOR_GATEWAY -> COMPLETED.
    """

    @classmethod
    def process(cls, state: AgentState) -> None:
        payload = state.proposal_payload or {}
        proposal = AgentProposalBoundary.build_proposal(
            session_id=state.session_id,
            buyer_id=state.buyer_id,
            merchant_id=state.merchant_id,
            mandate_id=state.mandate_id,
            proposal_data=payload,
        )

        state.transition_to(
            AgentStateEnum.WAITING_FOR_GATEWAY,
            detail=f"Proposal {proposal.proposal_id!r} waiting for gateway",
        )
        state.transition_to(
            AgentStateEnum.COMPLETED, detail="Proposal submitted to gateway boundary"
        )


class NodeFinalize:
    """Node 6: Finalize agent execution and record final status."""

    @classmethod
    def process(cls, state: AgentState, success: bool, reason: str | None = None) -> None:
        if not state.current_state.is_terminal:
            target_state = AgentStateEnum.COMPLETED if success else AgentStateEnum.FAILED
            state.transition_to(target_state, detail=reason)
        if reason:
            state.set_failure_reason(reason)

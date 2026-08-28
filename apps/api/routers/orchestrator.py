"""
S03.2 — End-to-End Commerce Orchestrator API Router.

Implements REST API endpoints for invoking end-to-end user intent execution
(Section 24 & Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from typing import Any, Callable

from agent.orchestrator.engine import CommerceOrchestrator
from agent.orchestrator.types import EndToEndExecutionResult, OrchestratorExecutionRequest

try:
    from fastapi import APIRouter, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any  # type: ignore[misc,assignment]

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_400_BAD_REQUEST = 400


_ORCHESTRATOR = CommerceOrchestrator()


if HAS_FASTAPI:
    orchestrator_router: Any = APIRouter(
        prefix="/api/orchestrator", tags=["End-to-End Commerce Orchestrator"]
    )
else:

    class DummyRouter:
        def post(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    orchestrator_router: Any = DummyRouter()  # type: ignore[no-redef]


@orchestrator_router.post(
    "/execute",
    response_model=EndToEndExecutionResult,
    status_code=status.HTTP_200_OK,
)
def execute_end_to_end_intent(payload: OrchestratorExecutionRequest) -> EndToEndExecutionResult:
    """Trigger end-to-end execution of a user commerce intent prompt."""
    return _ORCHESTRATOR.execute_intent(payload)

"""
S02.7 — Red-Team Chaos Lab API Router.

Implements REST API endpoints for invoking the 8 mandatory red-team attack vectors
and running the full suite (Section 28 & Section 21, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from typing import Any, Callable

from agent.redteam.engine import RedTeamChaosEngine
from agent.redteam.types import AttackStatus, AttackType, RedTeamAttackRequest
from apps.api.contracts.redteam import RedTeamAttackResponse, RedTeamRunAllResponse

try:
    from fastapi import APIRouter, Depends, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any
    Depends = Any

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200


if HAS_FASTAPI:
    redteam_router = APIRouter(prefix="/api/redteam", tags=["Red Team Chaos Lab"])
else:

    class DummyRouter:
        def post(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    redteam_router = DummyRouter()


def get_redteam_engine() -> RedTeamChaosEngine:
    """Dependency provider for RedTeamChaosEngine."""
    return RedTeamChaosEngine()


@redteam_router.post(
    "/prompt-injection",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 1 — Catalog Prompt Injection",
)
def attack_prompt_injection(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.PROMPT_INJECTION, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/cart-tamper",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 2 — Cart Tampering After Authorization",
)
def attack_cart_tamper(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.CART_TAMPER, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/replay",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 3 — Nonce Replay & Second-Use Submission",
)
def attack_replay(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.NONCE_REPLAY, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/double-spend",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 4 — Concurrent Double Spend Against Shared Budget",
)
def attack_double_spend(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.DOUBLE_SPEND, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/timeout",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 5 — Network Timeout Retry & Idempotent Query",
)
def attack_timeout(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.TIMEOUT_RETRY, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/expired-mandate",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 6 — Execution Under Expired Mandate",
)
def attack_expired_mandate(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.EXPIRED_MANDATE, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/merchant-policy",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 7 — Merchant Policy Violation",
)
def attack_merchant_policy(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.MERCHANT_POLICY, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/unauthorized-tool",
    response_model=RedTeamAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate Attack 8 — Direct Call to Unauthorized / Masked MCP Tool",
)
def attack_unauthorized_tool(
    request: RedTeamAttackRequest | None = None,
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamAttackResponse:
    payload = request.custom_payload if request else None
    result = engine.run_attack(AttackType.UNAUTHORIZED_TOOL, custom_payload=payload)
    return RedTeamAttackResponse(**result.model_dump())


@redteam_router.post(
    "/run-all",
    response_model=RedTeamRunAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Full 8-Attack Red-Team Chaos Suite",
)
def run_all_attacks(
    engine: RedTeamChaosEngine = Depends(get_redteam_engine),
) -> RedTeamRunAllResponse:
    results = engine.run_all_attacks()
    total = len(results)
    blocked = sum(1 for r in results if r.status == AttackStatus.BLOCKED)
    exploited = sum(1 for r in results if r.status == AttackStatus.EXPLOITED)

    response_list = [RedTeamAttackResponse(**r.model_dump()) for r in results]

    return RedTeamRunAllResponse(
        total_attacks=total,
        total_blocked=blocked,
        total_exploited=exploited,
        all_passed=(blocked == total and exploited == 0),
        results=response_list,
    )

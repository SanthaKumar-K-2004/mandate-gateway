"""
Mandate Gateway — Operational SLI, SLO & Error Budget Architecture
Milestone M13 — SRE Controls Foundation

Defines explicit Service Level Indicators (SLIs), Service Level Objectives (SLOs),
and Error Budget tracking for production operations.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List


@dataclasses.dataclass(frozen=True)
class SLODefinition:
    name: str
    target_percentage: float
    measurement_window: str
    description: str
    warning_threshold_percentage: float
    critical_threshold_percentage: float


# Production Service Level Objectives
SLO_AVAILABILITY = SLODefinition(
    name="api_availability",
    target_percentage=99.9,
    measurement_window="30d",
    description="Percentage of HTTP requests returning non-5xx status codes.",
    warning_threshold_percentage=99.95,
    critical_threshold_percentage=99.90,
)

SLO_PAYMENT_CORRECTNESS = SLODefinition(
    name="payment_correctness",
    target_percentage=100.0,
    measurement_window="30d",
    description="Percentage of payments processed without duplicate provider execution or state corruption.",
    warning_threshold_percentage=100.0,
    critical_threshold_percentage=100.0,
)

SLO_EXECUTION_LATENCY = SLODefinition(
    name="execution_latency",
    target_percentage=99.0,
    measurement_window="30d",
    description="Percentage of payment execution requests completed within 500ms.",
    warning_threshold_percentage=99.5,
    critical_threshold_percentage=99.0,
)

SLO_RECOVERY_TIME = SLODefinition(
    name="recovery_time",
    target_percentage=99.9,
    measurement_window="30d",
    description="Percentage of ambiguous EXECUTING transactions reconciled within 60s.",
    warning_threshold_percentage=99.95,
    critical_threshold_percentage=99.90,
)

SLO_OUTBOX_DELIVERY = SLODefinition(
    name="outbox_delivery_latency",
    target_percentage=99.9,
    measurement_window="30d",
    description="Percentage of transactional outbox events dispatched within 5s.",
    warning_threshold_percentage=99.95,
    critical_threshold_percentage=99.90,
)


ALL_SLOS: List[SLODefinition] = [
    SLO_AVAILABILITY,
    SLO_PAYMENT_CORRECTNESS,
    SLO_EXECUTION_LATENCY,
    SLO_RECOVERY_TIME,
    SLO_OUTBOX_DELIVERY,
]


def calculate_error_budget(
    total_events: int, failed_events: int, target_percentage: float
) -> Dict[str, Any]:
    """Calculates current error budget consumption and remaining percentage."""
    if total_events <= 0:
        return {
            "total_events": 0,
            "failed_events": 0,
            "error_budget_consumed_percentage": 0.0,
            "error_budget_remaining_percentage": 100.0,
            "status": "HEALTHY",
        }

    allowed_failure_rate = (100.0 - target_percentage) / 100.0
    allowed_failures = total_events * allowed_failure_rate

    if allowed_failures <= 0:
        consumed_percentage = 100.0 if failed_events > 0 else 0.0
    else:
        consumed_percentage = min(100.0, (failed_events / allowed_failures) * 100.0)

    remaining_percentage = round(100.0 - consumed_percentage, 2)

    if consumed_percentage >= 100.0:
        status = "EXHAUSTED"
    elif consumed_percentage >= 80.0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "total_events": total_events,
        "failed_events": failed_events,
        "error_budget_consumed_percentage": round(consumed_percentage, 2),
        "error_budget_remaining_percentage": remaining_percentage,
        "status": status,
    }

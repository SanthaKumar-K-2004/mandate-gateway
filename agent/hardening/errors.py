"""
M04 — Deep System Hardening Error Code Taxonomy & Exceptions.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class M04HardeningErrorCode(str, Enum):
    """Error codes for M04 deep system hardening operations."""

    TRUST_BOUNDARY_VIOLATION = "TRUST_BOUNDARY_VIOLATION"
    STATE_MACHINE_ILLEGAL_TRANSITION = "STATE_MACHINE_ILLEGAL_TRANSITION"
    CONTRACT_INCONSISTENCY = "CONTRACT_INCONSISTENCY"
    CONCURRENCY_RACE_DETECTED = "CONCURRENCY_RACE_DETECTED"
    FAIL_CLOSED_VIOLATION = "FAIL_CLOSED_VIOLATION"
    CONTROLLED_INJECTION_FAILED = "CONTROLLED_INJECTION_FAILED"


class M04HardeningError(Exception):
    """Domain exception raised during M04 system hardening audit failures."""

    def __init__(self, code: M04HardeningErrorCode, detail: str) -> None:
        super().__init__(f"[{code.value}] {detail}")
        self.code = code
        self.detail = detail

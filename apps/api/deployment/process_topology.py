"""
Production Service Process Topology & Lifecycle Control.
Section M16 — Workstream 4: Service Topology & Process Separation.
"""

from __future__ import annotations

from enum import Enum
import logging
from typing import Any, Dict

logger = logging.getLogger("mandate_gateway.process_topology")


class ProcessRole(str, Enum):
    API_SERVICE = "api_service"
    OUTBOX_WORKER = "outbox_worker"
    RECOVERY_WORKER = "recovery_worker"
    MAINTENANCE = "maintenance"


class ProcessTopologyManager:
    """Manages process identity, role isolation, and execution contracts for Razerpay runtime services."""

    def __init__(self, role: ProcessRole = ProcessRole.API_SERVICE) -> None:
        self.role = role
        self._is_alive = True
        self._is_ready = False

    def get_process_metadata(self) -> Dict[str, Any]:
        """Returns process identity, role, and capabilities."""
        return {
            "role": self.role.value,
            "is_api": self.role == ProcessRole.API_SERVICE,
            "is_outbox_worker": self.role == ProcessRole.OUTBOX_WORKER,
            "is_recovery_worker": self.role == ProcessRole.RECOVERY_WORKER,
            "is_maintenance": self.role == ProcessRole.MAINTENANCE,
            "handles_http_traffic": self.role == ProcessRole.API_SERVICE,
            "handles_outbox_events": self.role == ProcessRole.OUTBOX_WORKER,
            "handles_recovery_scans": self.role == ProcessRole.RECOVERY_WORKER,
        }

    def set_ready(self, ready: bool = True) -> None:
        self._is_ready = ready

    def set_alive(self, alive: bool = True) -> None:
        self._is_alive = alive

    def check_liveness(self) -> Dict[str, Any]:
        """Returns process liveness indicator."""
        return {
            "status": "ALIVE" if self._is_alive else "DEAD",
            "role": self.role.value,
            "liveness": self._is_alive,
        }

    def check_readiness(self) -> Dict[str, Any]:
        """Returns process readiness indicator."""
        return {
            "status": "READY" if (self._is_alive and self._is_ready) else "NOT_READY",
            "role": self.role.value,
            "readiness": self._is_alive and self._is_ready,
        }


process_topology = ProcessTopologyManager()

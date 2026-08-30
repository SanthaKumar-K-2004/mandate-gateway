"""
Mandate Gateway — Application Lifecycle Management
Section S00.4 — Application Runtime Foundation
"""

import enum
import threading
from typing import Callable, List, Optional


class LifecycleState(str, enum.Enum):
    """Supported application lifecycle states."""

    BOOTING = "BOOTING"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class AppLifecycle:
    """
    Thread-safe lifecycle manager for Mandate Gateway application runtime.
    Controls state transitions deterministically and prevents partially initialized runtimes from reporting READY.
    """

    def __init__(self) -> None:
        self._state = LifecycleState.BOOTING
        self._lock = threading.Lock()
        self._startup_hooks: List[Callable[[], None]] = []
        self._shutdown_hooks: List[Callable[[], None]] = []
        self._failure_reason: Optional[str] = None

    @property
    def state(self) -> LifecycleState:
        with self._lock:
            return self._state

    @property
    def failure_reason(self) -> Optional[str]:
        with self._lock:
            return self._failure_reason

    def is_ready(self) -> bool:
        with self._lock:
            return self._state == LifecycleState.READY

    def is_stopped(self) -> bool:
        with self._lock:
            return self._state == LifecycleState.STOPPED

    def mark_ready(self) -> None:
        with self._lock:
            self._state = LifecycleState.READY

    def add_startup_hook(self, hook: Callable[[], None]) -> None:
        with self._lock:
            if self._state != LifecycleState.BOOTING:
                raise RuntimeError(f"Cannot add startup hook in state {self._state}")
            self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: Callable[[], None]) -> None:
        with self._lock:
            self._shutdown_hooks.append(hook)

    def startup(self) -> None:
        """Executes startup sequence and transitions to READY."""
        with self._lock:
            if self._state not in (LifecycleState.BOOTING, LifecycleState.STOPPED):
                raise RuntimeError(f"Cannot start application from state {self._state}")
            self._state = LifecycleState.INITIALIZING

        try:
            for hook in self._startup_hooks:
                hook()
            with self._lock:
                self._state = LifecycleState.READY
        except Exception as err:
            with self._lock:
                self._state = LifecycleState.FAILED
                self._failure_reason = str(err)
            raise

    def shutdown(self) -> None:
        """Executes shutdown sequence and transitions to STOPPED."""
        with self._lock:
            if self._state in (LifecycleState.SHUTTING_DOWN, LifecycleState.STOPPED):
                return
            self._state = LifecycleState.SHUTTING_DOWN

        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception:
                pass  # Suppress shutdown hook errors to ensure complete cleanup

        with self._lock:
            self._state = LifecycleState.STOPPED

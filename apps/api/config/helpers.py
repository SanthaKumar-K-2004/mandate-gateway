"""
Mandate Gateway — Configuration Helpers & Cache Singleton
Section S00.3 — Configuration & Secrets Management
"""

import threading
from typing import Optional

from apps.api.config.settings import Settings

_settings_instance: Optional[Settings] = None
_settings_lock = threading.Lock()


def get_settings(env_file: Optional[str] = None) -> Settings:
    """
    Returns the cached Settings singleton instance.
    Loads configuration on first access in a thread-safe manner using double-checked locking.

    Architecture Decision:
      The cached singleton is retained to avoid repeated disk I/O (.env file parsing)
      and process environment overhead on every application or route import.
      Thread safety is enforced via threading.Lock().
    """
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = Settings.from_env(env_file=env_file)
    return _settings_instance


def reset_settings_cache() -> None:
    """
    Resets the cached Settings singleton instance.
    Primarily used by test suites to ensure complete test isolation when mutating environment state.
    """
    global _settings_instance
    with _settings_lock:
        _settings_instance = None


def config_check_summary(settings: Optional[Settings] = None) -> str:
    """
    Returns a formatted, safe CLI configuration summary string.
    Guarantees secret redaction — sensitive keys display [REDACTED].
    """
    s = settings or get_settings()
    d = s.to_dict(redact=True)

    lines = [
        "============================================================",
        " Mandate Gateway — Effective Configuration Summary",
        " Section S00.3 — Configuration & Secrets Management",
        "============================================================",
        f" Environment (APP_ENV)    : {d['APP_ENV']}",
        f" Application Name         : {d['APP_NAME']}",
        f" Log Level (LOG_LEVEL)    : {d['LOG_LEVEL']}",
        f" Host Context Mode        : {d['HOST_CONTEXT']}",
        "--- Infrastructure Endpoints ---",
        f" PostgreSQL Host          : {d['POSTGRES_HOST']}",
        f" PostgreSQL Port          : {d['POSTGRES_PORT']}",
        f" PostgreSQL Database      : {d['POSTGRES_DB']}",
        f" PostgreSQL User          : {d['POSTGRES_USER']}",
        f" PostgreSQL Password      : {d['POSTGRES_PASSWORD']}",
        f" Redis Host               : {d['REDIS_HOST']}",
        f" Redis Port               : {d['REDIS_PORT']}",
        f" Redis DB                 : {d['REDIS_DB']}",
        "============================================================",
    ]
    return "\n".join(lines)

"""
Mandate Gateway — Authoritative Settings Architecture
Section S00.3 — Configuration & Secrets Management
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from apps.api.config.env_loader import load_env_file
from apps.api.config.types import (
    ConfigurationError,
    Environment,
    LogLevel,
    SecretString,
)


@dataclass(frozen=True)
class Settings:
    """
    Authoritative, typed, fail-fast configuration contract for Mandate Gateway.
    Centralized boundary enforcing secret redaction, host/container separation, and fail-closed security.
    """

    app_env: Environment
    app_name: str
    log_level: LogLevel

    # Infrastructure Host Context Boundary
    host_context: bool

    # Database Infrastructure Configuration (PostgreSQL 16)
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: SecretString

    # Redis Infrastructure Configuration (Redis 7)
    redis_host: str
    redis_port: int
    redis_db: int

    @classmethod
    def load(cls, host_context: bool = True) -> "Settings":
        """Convenience loader for Settings."""
        return cls.from_env(host_context=host_context)

    @classmethod
    def from_env(
        cls,
        env_dict: Optional[Dict[str, str]] = None,
        env_file: Optional[str] = None,
        host_context: Optional[bool] = None,
    ) -> "Settings":
        """
        Loads and validates configuration following explicit precedence:
          1. env_dict (or os.environ if env_dict is None)
          2. Local .env file (if present)
          3. Safe code-level defaults (for non-sensitive settings)
        """
        # Read .env file if specified or default root .env exists
        file_vars: Dict[str, str] = {}
        target_env_file = env_file or ".env"
        if os.path.isfile(target_env_file):
            file_vars = load_env_file(target_env_file)

        # Source values: process environment takes precedence over .env file
        source: Dict[str, str] = {}
        source.update(file_vars)
        if env_dict is not None:
            source.update(env_dict)
        else:
            source.update({k: v for k, v in os.environ.items()})

        # Helper to get raw value safely as string
        def get_val(key: str, default: str = "") -> str:
            if key in source:
                v = source[key]
                return v.strip() if v is not None else ""
            return default

        # 1. Environment & Logging
        raw_env = get_val("APP_ENV", "development")
        app_env = Environment.from_str(raw_env)

        app_name = get_val("APP_NAME", "mandate-gateway")

        raw_log_level = get_val("LOG_LEVEL", "INFO")
        log_level = LogLevel.from_str(raw_log_level)

        # 2. Host vs Container Context Boundary
        raw_host_context = get_val("HOST_CONTEXT", "false").lower()
        host_context = raw_host_context in ("true", "1", "yes")

        # Ports validation helper
        def parse_port(var_name: str, default_val: int) -> int:
            raw = get_val(var_name, str(default_val))
            try:
                p = int(raw)
                if not (1 <= p <= 65535):
                    raise ValueError()
                return p
            except (ValueError, TypeError):
                raise ConfigurationError(
                    f"Invalid {var_name}: '{raw}'. Must be an integer between 1 and 65535."
                )

        # 3. Database Infrastructure
        # Determine default host: container DNS ("postgres") by default, "127.0.0.1" for host context
        default_pg_host = "127.0.0.1" if host_context else "postgres"
        postgres_host = get_val("POSTGRES_HOST", default_pg_host)

        postgres_port = parse_port("POSTGRES_PORT", 5432)

        postgres_db = get_val("POSTGRES_DB", "mandate_gateway")
        if not postgres_db:
            raise ConfigurationError("POSTGRES_DB cannot be empty.")

        postgres_user = get_val("POSTGRES_USER", "postgres")
        if not postgres_user:
            raise ConfigurationError("POSTGRES_USER cannot be empty.")

        raw_pg_pass = get_val("POSTGRES_PASSWORD", "CHANGE_ME_LOCAL_ONLY")
        postgres_password = SecretString(raw_pg_pass)

        # 4. Redis Infrastructure
        default_redis_host = "127.0.0.1" if host_context else "redis"
        redis_host = get_val("REDIS_HOST", default_redis_host)

        redis_port = parse_port("REDIS_PORT", 6379)

        raw_redis_db = get_val("REDIS_DB", "0")
        try:
            redis_db = int(raw_redis_db)
            if redis_db < 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise ConfigurationError(
                f"Invalid REDIS_DB: '{raw_redis_db}'. Must be a non-negative integer."
            )

        # 5. Fail-Fast Validation Policies
        # Security Policy: Production mode MUST NOT run with empty, default, or placeholder passwords
        if app_env == Environment.PRODUCTION:
            pass_val = postgres_password.get_secret_value()
            if not pass_val or pass_val in (
                "CHANGE_ME_LOCAL_ONLY",
                "postgres",
                "password",
            ):
                raise ConfigurationError(
                    "POSTGRES_PASSWORD must be explicitly set to a secure value in production environment."
                )

        # Container Boundary Protection: Inside container mode, hostnames should not be localhost
        if not host_context and app_env in (
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION,
        ):
            if postgres_host == "localhost":
                raise ConfigurationError(
                    "POSTGRES_HOST cannot be 'localhost' in container environment. Use Compose DNS name 'postgres'."
                )
            if redis_host == "localhost":
                raise ConfigurationError(
                    "REDIS_HOST cannot be 'localhost' in container environment. Use Compose DNS name 'redis'."
                )

        return cls(
            app_env=app_env,
            app_name=app_name,
            log_level=log_level,
            host_context=host_context,
            postgres_host=postgres_host,
            postgres_port=postgres_port,
            postgres_db=postgres_db,
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
        )

    def to_dict(self, redact: bool = True) -> Dict[str, Any]:
        """Returns configuration dictionary with optional secret redaction."""
        return {
            "APP_ENV": self.app_env.value,
            "APP_NAME": self.app_name,
            "LOG_LEVEL": self.log_level.value,
            "HOST_CONTEXT": self.host_context,
            "POSTGRES_HOST": self.postgres_host,
            "POSTGRES_PORT": self.postgres_port,
            "POSTGRES_DB": self.postgres_db,
            "POSTGRES_USER": self.postgres_user,
            "POSTGRES_PASSWORD": (
                "[REDACTED]" if redact else self.postgres_password.get_secret_value()
            ),
            "REDIS_HOST": self.redis_host,
            "REDIS_PORT": self.redis_port,
            "REDIS_DB": self.redis_db,
        }

    def __repr__(self) -> str:
        d = self.to_dict(redact=True)
        items = [f"{k}={v!r}" for k, v in d.items()]
        return f"Settings({', '.join(items)})"

    def __str__(self) -> str:
        return self.__repr__()


def validate_production_config(settings: Settings) -> None:
    """
    Enforces fail-fast startup validation for production mode (APP_ENV=production).
    Rejects insecure defaults, missing passwords, or unsafe log levels before accepting traffic.
    """
    if settings.app_env != Environment.PRODUCTION:
        return

    pwd = settings.postgres_password.get_secret_value()
    if not pwd or pwd.lower() in (
        "postgres",
        "password",
        "secret",
        "change_me",
        "change_me_local_only",
        "admin",
    ):
        raise ConfigurationError(
            "Insecure or default POSTGRES_PASSWORD prohibited in production mode."
        )

    if not settings.postgres_host:
        raise ConfigurationError("POSTGRES_HOST must be explicitly specified in production mode.")

    if not settings.redis_host:
        raise ConfigurationError("REDIS_HOST must be explicitly specified in production mode.")

    if settings.log_level == LogLevel.DEBUG:
        raise ConfigurationError("LOG_LEVEL=DEBUG is prohibited in production mode.")

    import os

    provider_secret = os.environ.get("PROVIDER_API_KEY")
    if provider_secret and provider_secret.lower() in (
        "default",
        "secret",
        "test_key",
        "change_me",
    ):
        raise ConfigurationError(
            "Insecure or default PROVIDER_API_KEY prohibited in production mode."
        )

    webhook_secret = os.environ.get("WEBHOOK_SECRET")
    if webhook_secret and webhook_secret.lower() in (
        "default",
        "secret",
        "test_secret",
        "change_me",
    ):
        raise ConfigurationError(
            "Insecure or default WEBHOOK_SECRET prohibited in production mode."
        )

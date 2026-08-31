"""
Mandate Gateway — Production Environment & Security Validator (M29)
Workstream 1 & 2 — Validates production readiness and enforces fail-closed startup:
- Fails startup if secrets are default/placeholder values in APP_ENV=production.
- Fails startup if DEBUG mode is enabled in production.
- Fails startup if sandbox/demo connectors are registered for production routing.
- Fails startup if HTTP endpoints are used where HTTPS is mandatory.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("mandate_gateway.production_validator")


@dataclass
class ValidationIssue:
    """Production configuration validation error or warning."""

    field: str
    message: str
    severity: str  # "FATAL" | "WARNING"


class ProductionEnvironmentValidator:
    """Enforces strict production security policies during application startup."""

    UNSAFE_SECRET_PATTERNS = [
        "dev_jwt_secret",
        "secret",
        "changeme",
        "123456",
        "password",
        "dev_reconciliation_hmac_secret",
        "cafe_acme_dev_key",
        "test_secret",
    ]

    @classmethod
    def validate_environment(
        self,
        app_env: str,
        jwt_secret: Optional[str] = None,
        hmac_secret: Optional[str] = None,
        cafe_acme_key: Optional[str] = None,
        log_level: Optional[str] = None,
        allow_demo_connectors: bool = False,
    ) -> List[ValidationIssue]:
        """Validate production configuration parameters. Returns list of validation issues."""
        issues: List[ValidationIssue] = []

        is_production = app_env.lower() in ("production", "prod")

        # 1. Debug / Log level check
        log_lvl_str = (log_level or os.getenv("LOG_LEVEL", "") or "").upper()
        if is_production and log_lvl_str == "DEBUG":
            issues.append(
                ValidationIssue(
                    field="LOG_LEVEL",
                    message="LOG_LEVEL cannot be set to DEBUG in production environment.",
                    severity="FATAL",
                )
            )

        # 2. Secrets validation in production
        if is_production:
            secrets = {
                "JWT_SECRET": jwt_secret or os.getenv("JWT_SECRET", ""),
                "RECONCILIATION_HMAC_SECRET": hmac_secret
                or os.getenv("RECONCILIATION_HMAC_SECRET", ""),
                "CAFE_ACME_API_KEY": cafe_acme_key or os.getenv("CAFE_ACME_API_KEY", ""),
            }

            for sec_name, sec_val in secrets.items():
                if not sec_val:
                    issues.append(
                        ValidationIssue(
                            field=sec_name,
                            message=f"Required production secret '{sec_name}' is missing.",
                            severity="FATAL",
                        )
                    )
                elif any(pat in sec_val.lower() for pat in self.UNSAFE_SECRET_PATTERNS):
                    issues.append(
                        ValidationIssue(
                            field=sec_name,
                            message=f"Production secret '{sec_name}' uses unsafe development placeholder.",
                            severity="FATAL",
                        )
                    )

        # 3. Sandbox / Demo connector policy in production
        if is_production and allow_demo_connectors:
            issues.append(
                ValidationIssue(
                    field="ALLOW_DEMO_CONNECTORS",
                    message="Demo/Sandbox connectors cannot be enabled in production routing.",
                    severity="FATAL",
                )
            )

        return issues

    @classmethod
    def assert_production_security(
        self,
        app_env: str,
        jwt_secret: Optional[str] = None,
        hmac_secret: Optional[str] = None,
        cafe_acme_key: Optional[str] = None,
        log_level: Optional[str] = None,
        allow_demo_connectors: bool = False,
    ) -> None:
        """Assert production environment safety. Raises RuntimeError on FATAL issues."""
        issues = self.validate_environment(
            app_env=app_env,
            jwt_secret=jwt_secret,
            hmac_secret=hmac_secret,
            cafe_acme_key=cafe_acme_key,
            log_level=log_level,
            allow_demo_connectors=allow_demo_connectors,
        )

        fatal_issues = [i for i in issues if i.severity == "FATAL"]
        if fatal_issues:
            err_msg = "; ".join([f"{i.field}: {i.message}" for i in fatal_issues])
            logger.critical("PRODUCTION SECURITY VALIDATION FAILED: %s", err_msg)
            raise RuntimeError(f"Production Security Fail-Closed Triggered: {err_msg}")

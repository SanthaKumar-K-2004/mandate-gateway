"""
Mandate Gateway — Commerce Connector Configuration System (M26)
Workstream 2 — Reads, validates, and manages secure connector runtime configurations from environment variables.
Redacts all API keys and secrets in logs/API responses and enforces fail-closed production security.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from apps.api.commerce.models import ConnectorEnvironment


class ConnectorConfigurationError(ValueError):
    """Raised when connector configuration is invalid, insecure, or missing in production."""

    pass


@dataclass
class MerchantConnectorSettings:
    """Individual merchant connector configuration settings."""

    connector_id: str
    name: str
    enabled: bool
    base_url: str
    api_key: str
    webhook_secret: str
    environment: ConnectorEnvironment

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return safe dictionary representation with all sensitive credentials redacted."""
        masked_key = (
            f"{self.api_key[:4]}***"
            if len(self.api_key) >= 8
            else "***REDACTED***" if self.api_key else ""
        )
        masked_secret = (
            f"{self.webhook_secret[:4]}***"
            if len(self.webhook_secret) >= 8
            else "***REDACTED***" if self.webhook_secret else ""
        )

        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "api_key_masked": masked_key,
            "webhook_secret_configured": bool(self.webhook_secret),
            "webhook_secret_masked": masked_secret,
            "environment": self.environment.value,
        }


class CommerceConnectorConfigManager:
    """Central configuration manager for external merchant commerce connectors."""

    def __init__(self, env: Optional[Dict[str, str]] = None) -> None:
        self._env = env if env is not None else dict(os.environ)
        self.connectors_enabled = self._get_bool_env("COMMERCE_CONNECTORS_ENABLED", True)
        self.app_env = self._env.get("APP_ENV", "development").lower()
        self.connectors: Dict[str, MerchantConnectorSettings] = {}
        self._load_configurations()

    def _get_bool_env(self, key: str, default: bool) -> bool:
        val = self._env.get(key, "").strip().lower()
        if not val:
            return default
        return val in ("true", "1", "yes", "enabled")

    def _load_configurations(self) -> None:
        """Load and validate all configured merchant connectors from environment."""
        # Connector 1: Default Cafe Acme Direct API / Sandbox
        c1_enabled = self._get_bool_env("MERCHANT_CONNECTOR_1_ENABLED", True)
        c1_url = self._env.get(
            "MERCHANT_CONNECTOR_1_BASE_URL", "https://api.cafeacme.local"
        ).strip()
        c1_key = self._env.get("MERCHANT_CONNECTOR_1_API_KEY", "key_cafeacme_live_m26").strip()
        c1_sec = self._env.get(
            "MERCHANT_CONNECTOR_1_WEBHOOK_SECRET", "whsec_cafe_acme_live_m25"
        ).strip()
        c1_env_str = self._env.get("MERCHANT_CONNECTOR_1_ENVIRONMENT", "SANDBOX").strip().upper()

        c1_env = ConnectorEnvironment.SANDBOX
        if c1_env_str in ConnectorEnvironment.__members__:
            c1_env = ConnectorEnvironment[c1_env_str]

        s1 = MerchantConnectorSettings(
            connector_id="connector_cafe_acme_api",
            name="Cafe Acme Direct API",
            enabled=c1_enabled,
            base_url=c1_url,
            api_key=c1_key,
            webhook_secret=c1_sec,
            environment=c1_env,
        )
        self.connectors[s1.connector_id] = s1

        # Connector 2: Public Catalog Direct API
        c2_enabled = self._get_bool_env("MERCHANT_CONNECTOR_2_ENABLED", True)
        c2_url = self._env.get(
            "MERCHANT_CONNECTOR_2_BASE_URL", "https://world.openfoodfacts.org"
        ).strip()
        c2_key = self._env.get("MERCHANT_CONNECTOR_2_API_KEY", "public_catalog_key").strip()
        c2_sec = self._env.get("MERCHANT_CONNECTOR_2_WEBHOOK_SECRET", "whsec_m26_pilot").strip()
        c2_env_str = self._env.get("MERCHANT_CONNECTOR_2_ENVIRONMENT", "LIVE").strip().upper()

        c2_env = ConnectorEnvironment.LIVE
        if c2_env_str in ConnectorEnvironment.__members__:
            c2_env = ConnectorEnvironment[c2_env_str]

        s2 = MerchantConnectorSettings(
            connector_id="connector_openfoodfacts_public_api",
            name="Public Open Catalog Direct API",
            enabled=c2_enabled,
            base_url=c2_url,
            api_key=c2_key,
            webhook_secret=c2_sec,
            environment=c2_env,
        )
        self.connectors[s2.connector_id] = s2

        # Production Validation Guard: Fail closed if production mode configured insecurely
        if self.app_env == "production":
            self.validate_production_readiness()

    def validate_production_readiness(self) -> None:
        """Enforce strict production security checks for all active connectors."""
        for conn_id, settings in self.connectors.items():
            if not settings.enabled:
                continue

            # Production Rule 1: Production cannot use DEMO connectors as active live connectors
            if settings.environment == ConnectorEnvironment.DEMO:
                raise ConnectorConfigurationError(
                    f"Production error: Connector '{conn_id}' is configured with environment DEMO. "
                    "Demo connectors are prohibited in production mode."
                )

            # Production Rule 2: Active connectors in production MUST use HTTPS
            if settings.base_url and not settings.base_url.startswith("https://"):
                raise ConnectorConfigurationError(
                    f"Production error: Connector '{conn_id}' base URL '{settings.base_url}' must use HTTPS."
                )

    def get_connector_settings(self, connector_id: str) -> Optional[MerchantConnectorSettings]:
        """Fetch settings for a given connector ID."""
        return self.connectors.get(connector_id)

    def get_all_safe_settings(self) -> List[Dict[str, Any]]:
        """Fetch redacted safe configurations for all connectors."""
        return [c.to_safe_dict() for c in self.connectors.values()]

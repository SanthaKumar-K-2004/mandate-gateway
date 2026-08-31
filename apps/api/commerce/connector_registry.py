"""
Mandate Gateway — Commerce Connector Registry (M24)
Workstream 7 — Central registry for registering and resolving commerce connectors.
Rejects duplicate or conflicting connector registrations.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from apps.api.commerce.connectors.base import CommerceConnector, CommerceConnectorError
from apps.api.commerce.connectors.generic_web import GenericWebCheckoutConnector


class CommerceConnectorRegistry:
    """Production-grade Registry for Commerce Connectors."""

    def __init__(self) -> None:
        self._connectors: Dict[str, CommerceConnector] = {}
        self._domain_map: Dict[str, str] = {}
        self._generic_fallback = GenericWebCheckoutConnector()

    def register_connector(
        self, connector: CommerceConnector, target_domains: Optional[List[str]] = None
    ) -> None:
        """Register an authorized commerce connector."""
        cid = connector.connector_id
        if cid in self._connectors:
            raise CommerceConnectorError(f"Duplicate connector registration rejected for '{cid}'.")

        self._connectors[cid] = connector

        if target_domains:
            for domain in target_domains:
                domain_clean = domain.strip().lower()
                if domain_clean in self._domain_map:
                    err_msg = (
                        f"Domain conflict detected: Domain '{domain_clean}' is already "
                        f"registered to '{self._domain_map[domain_clean]}'."
                    )
                    raise CommerceConnectorError(err_msg)
                self._domain_map[domain_clean] = cid

    def resolve_connector(self, domain: str) -> CommerceConnector:
        """Resolve target connector for domain, falling back to GenericWebCheckoutConnector."""
        if not domain:
            return self._generic_fallback

        domain_clean = domain.strip().lower()
        cid = self._domain_map.get(domain_clean)
        if cid and cid in self._connectors:
            return self._connectors[cid]

        for connector in self._connectors.values():
            if connector.supports_domain(domain_clean):
                return connector

        return self._generic_fallback

    def get_connector(self, connector_id: str) -> Optional[CommerceConnector]:
        """Fetch connector by ID."""
        return self._connectors.get(connector_id)

    def list_active_connectors(self) -> List[CommerceConnector]:
        """List active CommerceConnector objects registered."""
        result: List[CommerceConnector] = [self._generic_fallback]
        for conn in self._connectors.values():
            if conn not in result:
                result.append(conn)
        return result

    def list_connectors(self) -> List[Dict[str, str]]:
        """List metadata for all registered connectors."""
        output = [
            {
                "connector_id": self._generic_fallback.connector_id,
                "capability": self._generic_fallback.capability.value,
                "description": "Generic Web Checkout Handoff Connector",
            }
        ]
        for conn in self._connectors.values():
            output.append(
                {
                    "connector_id": conn.connector_id,
                    "capability": conn.capability.value,
                    "description": f"Authorized Connector ({conn.connector_id})",
                }
            )
        return output

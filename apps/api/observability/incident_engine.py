"""
Section M15 — Incident Classification & Automated Anomaly Detection Engine.

Provides deterministic, rule-based anomaly detection across security, reliability,
data integrity, and API abuse categories with formal incident tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from apps.api.app.context import get_full_context

logger = logging.getLogger("mandate_gateway.observability.incidents")


@dataclass
class IncidentRecord:
    """Production Incident Record representation."""

    incident_id: str
    classification: str  # SECURITY, RELIABILITY, DATA_INTEGRITY, ABUSE
    severity: str  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    status: str  # OPEN, INVESTIGATING, MITIGATED, RESOLVED
    rule_id: str
    evidence_summary: str
    correlation_id: str
    merchant_id: Optional[str]
    detected_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "classification": self.classification,
            "severity": self.severity,
            "status": self.status,
            "rule_id": self.rule_id,
            "evidence_summary": self.evidence_summary,
            "correlation_id": self.correlation_id,
            "merchant_id": self.merchant_id,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


class IncidentEngine:
    """Incident Detection & Lifecycle Management Engine."""

    def __init__(self, max_incidents: int = 500) -> None:
        self._incidents: List[IncidentRecord] = []
        self._max_incidents = max_incidents
        self._auth_failure_counts: Dict[str, List[datetime]] = {}
        self._rate_limit_counts: Dict[str, List[datetime]] = {}
        self._webhook_forgery_counts: Dict[str, List[datetime]] = {}
        self._replay_attack_counts: Dict[str, List[datetime]] = {}

    def _utc_now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def raise_incident(
        self,
        classification: str,
        severity: str,
        rule_id: str,
        evidence_summary: str,
        merchant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IncidentRecord:
        """Creates and registers a new production incident."""
        ctx = get_full_context()
        inc_id = f"inc_{uuid.uuid4().hex}"
        corr = correlation_id or ctx.get("correlation_id") or ctx.get("request_id") or "corr_anon"
        mer_id = merchant_id or ctx.get("merchant_id")

        incident = IncidentRecord(
            incident_id=inc_id,
            classification=classification,
            severity=severity,
            status="OPEN",
            rule_id=rule_id,
            evidence_summary=evidence_summary,
            correlation_id=corr,
            merchant_id=mer_id,
            detected_at=self._utc_now(),
            metadata=metadata or {},
        )

        self._incidents.append(incident)
        if len(self._incidents) > self._max_incidents:
            self._incidents.pop(0)

        logger.warning(
            "INCIDENT RAISED [%s/%s] '%s': %s (ID: %s)",
            classification,
            severity,
            rule_id,
            evidence_summary,
            inc_id,
        )
        return incident

    def record_auth_failure(
        self, credential_fingerprint: str, merchant_id: Optional[str] = None
    ) -> Optional[IncidentRecord]:
        """Track auth failure & detect auth abuse anomaly."""
        now = self._utc_now()
        history = self._auth_failure_counts.setdefault(credential_fingerprint, [])
        history.append(now)
        # Filter within 60 second window
        recent = [t for t in history if (now - t).total_seconds() <= 60]
        self._auth_failure_counts[credential_fingerprint] = recent

        if len(recent) >= 5:
            summary = (
                f"Detected {len(recent)} failed auth attempts within 60s "
                f"for credential fingerprint '{credential_fingerprint}'"
            )
            return self.raise_incident(
                classification="SECURITY",
                severity="HIGH",
                rule_id="AUTH_ABUSE_DETECTED",
                evidence_summary=summary,
                merchant_id=merchant_id,
                metadata={
                    "credential_fingerprint": credential_fingerprint,
                    "failure_count": len(recent),
                },
            )
        return None

    def record_rate_limit_violation(
        self, key: str, category: str, merchant_id: Optional[str] = None
    ) -> Optional[IncidentRecord]:
        """Track rate limit violation & detect rate limit abuse anomaly."""
        now = self._utc_now()
        history = self._rate_limit_counts.setdefault(key, [])
        history.append(now)
        recent = [t for t in history if (now - t).total_seconds() <= 60]
        self._rate_limit_counts[key] = recent

        if len(recent) >= 5:
            summary = f"Detected {len(recent)} rate limit violations for key '{key}' in category '{category}'"
            return self.raise_incident(
                classification="ABUSE",
                severity="MEDIUM",
                rule_id="RATE_LIMIT_ABUSE_DETECTED",
                evidence_summary=summary,
                merchant_id=merchant_id,
                metadata={"rate_limit_key": key, "category": category, "count": len(recent)},
            )
        return None

    def record_tenant_isolation_violation(
        self, authenticated_merchant_id: str, target_merchant_id: str
    ) -> IncidentRecord:
        """Trigger tenant probing security incident."""
        summary = (
            f"Merchant '{authenticated_merchant_id}' attempted cross-tenant access "
            f"targeting merchant '{target_merchant_id}'"
        )
        return self.raise_incident(
            classification="SECURITY",
            severity="CRITICAL",
            rule_id="TENANT_PROBING_DETECTED",
            evidence_summary=summary,
            merchant_id=authenticated_merchant_id,
            metadata={
                "authenticated_merchant_id": authenticated_merchant_id,
                "target_merchant_id": target_merchant_id,
            },
        )

    def record_webhook_forgery(
        self, event_type: str, merchant_id: Optional[str] = None
    ) -> Optional[IncidentRecord]:
        """Track invalid webhook HMAC signature & raise security incident."""
        now = self._utc_now()
        key = merchant_id or "anon"
        history = self._webhook_forgery_counts.setdefault(key, [])
        history.append(now)
        recent = [t for t in history if (now - t).total_seconds() <= 60]
        self._webhook_forgery_counts[key] = recent

        if len(recent) >= 2:
            summary = f"Detected {len(recent)} invalid webhook HMAC signatures for event type '{event_type}'"
            return self.raise_incident(
                classification="SECURITY",
                severity="HIGH",
                rule_id="WEBHOOK_FORGERY_DETECTED",
                evidence_summary=summary,
                merchant_id=merchant_id,
                metadata={"event_type": event_type, "forgery_count": len(recent)},
            )
        return None

    def record_replay_attack(
        self, idempotency_key: str, merchant_id: Optional[str] = None
    ) -> Optional[IncidentRecord]:
        """Track duplicate replay attack attempt."""
        now = self._utc_now()
        key = idempotency_key
        history = self._replay_attack_counts.setdefault(key, [])
        history.append(now)
        recent = [t for t in history if (now - t).total_seconds() <= 60]
        self._replay_attack_counts[key] = recent

        if len(recent) >= 2:
            summary = (
                f"Detected repeated duplicate replay fingerprint attempts "
                f"for idempotency key '{idempotency_key}'"
            )
            return self.raise_incident(
                classification="SECURITY",
                severity="HIGH",
                rule_id="REPLAY_ATTACK_DETECTED",
                evidence_summary=summary,
                merchant_id=merchant_id,
                metadata={"idempotency_key": idempotency_key, "count": len(recent)},
            )
        return None

    def query_incidents(
        self,
        classification: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        merchant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[IncidentRecord]:
        """Queries registered incidents."""
        results: List[IncidentRecord] = []
        for inc in reversed(self._incidents):
            if classification and inc.classification != classification:
                continue
            if severity and inc.severity != severity:
                continue
            if status and inc.status != status:
                continue
            if merchant_id and inc.merchant_id != merchant_id:
                continue
            results.append(inc)
            if len(results) >= limit:
                break
        return results

    def get_incident_by_id(self, incident_id: str) -> Optional[IncidentRecord]:
        """Resolves incident by ID."""
        for inc in self._incidents:
            if inc.incident_id == incident_id:
                return inc
        return None

    def clear(self) -> None:
        """Resets engine state."""
        self._incidents.clear()
        self._auth_failure_counts.clear()
        self._rate_limit_counts.clear()
        self._webhook_forgery_counts.clear()
        self._replay_attack_counts.clear()


# Global Incident Engine Instance
incident_engine = IncidentEngine()

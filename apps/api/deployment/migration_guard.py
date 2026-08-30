"""
Production Database Migration Guard & Deployment Compatibility Validator.
Section M16 — Workstream 3: Database Migration Deployment Safety.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mandate_gateway.migration_guard")

KNOWN_HEAD_REVISION = "001_initial_schema"


class MigrationGuard:
    """Validates database schema readiness and migration state before application startup."""

    def __init__(self, expected_head_revision: str = KNOWN_HEAD_REVISION) -> None:
        self.expected_head_revision = expected_head_revision

    async def get_db_revision(self, session: AsyncSession) -> Optional[str]:
        """Queries the current alembic_version from the database."""
        try:
            res = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = res.fetchone()
            if row and row[0]:
                return str(row[0])
            return None
        except Exception:
            # Table might not exist or database uninitialized
            return None

    async def check_migration_status(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Inspects database migration status against expected HEAD revision.
        Returns detailed status dictionary.
        """
        current_rev = await self.get_db_revision(session)

        if current_rev == self.expected_head_revision:
            return {
                "status": "UP_TO_DATE",
                "current_revision": current_rev,
                "head_revision": self.expected_head_revision,
                "is_ready": True,
            }

        # Check if tables exist even if alembic_version table is absent (e.g., in-memory SQLite create_all)
        tables_exist = False
        try:
            await session.execute(text("SELECT 1 FROM merchants LIMIT 1"))
            tables_exist = True
        except Exception:
            tables_exist = False

        if tables_exist and current_rev is None:
            # SQLite or dev DB bootstrapped via Base.metadata.create_all
            return {
                "status": "BOOTSTRAPPED_READY",
                "current_revision": "001_initial_schema (bootstrapped)",
                "head_revision": self.expected_head_revision,
                "is_ready": True,
            }

        if current_rev is None and not tables_exist:
            return {
                "status": "UNINITIALIZED",
                "current_revision": None,
                "head_revision": self.expected_head_revision,
                "is_ready": False,
                "error": "Database tables do not exist and no Alembic revision recorded.",
            }

        return {
            "status": "SCHEMA_MISMATCH",
            "current_revision": current_rev,
            "head_revision": self.expected_head_revision,
            "is_ready": False,
            "error": f"Database revision '{current_rev}' does not match expected head '{self.expected_head_revision}'.",
        }

    async def verify_schema_ready(self, session: AsyncSession) -> Tuple[bool, str]:
        """
        Verifies database schema is ready for traffic.
        Fails closed by returning (False, error_message) or raising ConfigurationError if required.
        """
        status_info = await self.check_migration_status(session)
        if not status_info["is_ready"]:
            err_msg = status_info.get("error", "Database migration status is not ready.")
            logger.error(
                f"Migration verification failed: {err_msg}",
                extra={"event": "migration.verification_failed", "status_info": status_info},
            )
            return False, err_msg
        return True, "Schema is up to date."


migration_guard = MigrationGuard()

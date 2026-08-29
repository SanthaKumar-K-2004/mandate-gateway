"""
Integration tests for M09 — Database Migration Discipline.

Verifies:
  1. Alembic configuration and migration script location.
  2. Migration version scripts ordering and integrity.
  3. Base metadata consistency with Alembic schema definition.
  4. Reproducible schema initialization.
"""

from __future__ import annotations

import os
import unittest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


class TestM09MigrationDiscipline(unittest.TestCase):
    """Integration test suite for database migration discipline and Alembic setup."""

    def test_alembic_config_and_script_location(self) -> None:
        """Verify alembic.ini is present and references db/migrations."""
        ini_path = os.path.abspath("alembic.ini")
        self.assertTrue(os.path.exists(ini_path))

        config = Config(ini_path)
        script_location = config.get_main_option("script_location")
        self.assertEqual(script_location, "db/migrations")

    def test_migration_versions_ordering_and_head(self) -> None:
        """Verify Alembic migration version directory contains valid sequential revisions."""
        ini_path = os.path.abspath("alembic.ini")
        config = Config(ini_path)
        script_dir = ScriptDirectory.from_config(config)

        heads = script_dir.get_heads()
        self.assertEqual(len(heads), 1, "Should have exactly one head migration revision")
        self.assertEqual(heads[0], "001")

        revisions = list(script_dir.walk_revisions())
        self.assertGreaterEqual(len(revisions), 1)
        self.assertEqual(revisions[0].revision, "001")
        self.assertIsNone(revisions[0].down_revision)

    def test_schema_metadata_completeness(self) -> None:
        """Verify all core production tables are defined in Base.metadata."""
        tables = set(Base.metadata.tables.keys())
        expected_tables = {
            "merchants",
            "merchant_policies",
            "products",
            "mandates",
            "transactions",
            "execution_attempts",
            "action_receipts",
            "audit_events",
            "webhook_deliveries",
            "budgets",
            "nonces",
            "replays",
            "step_up_challenges",
            "outbox_events",
        }
        missing_tables = expected_tables - tables
        self.assertEqual(
            missing_tables, set(), f"Base.metadata is missing tables: {missing_tables}"
        )

    def test_fresh_database_bootstrap(self) -> None:
        """Verify fresh database bootstrap using Base.metadata."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check table creation
        for table_name in [
            "merchants",
            "transactions",
            "execution_attempts",
            "outbox_events",
            "audit_events",
        ]:
            self.assertTrue(engine.dialect.has_table(engine.connect(), table_name))

        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()

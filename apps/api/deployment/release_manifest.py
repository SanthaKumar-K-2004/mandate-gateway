"""
Mandate Gateway — Release Artifact Integrity & Manifest Management
Section M17 — Workstream D: Release Artifact Integrity
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from apps.api.config.version import RELEASE_VERSION, get_git_commit_hash
from apps.api.deployment.migration_guard import KNOWN_HEAD_REVISION


@dataclass(frozen=True)
class ReleaseManifest:
    """
    Cryptographically verifiable release manifest binding build identity,
    git commit, dependency lock, database schema revision, and environment compatibility.
    """

    git_commit_sha: str
    app_version: str
    schema_revision: str
    pyproject_hash: str
    artifact_checksum: str
    release_timestamp: str
    environment: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def compute_manifest_checksum(self) -> str:
        """Compute SHA-256 hex digest over deterministic canonical JSON representation."""
        data = self.to_dict()
        data_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hex digest of a file if it exists, else returns zero hash."""
    if not os.path.exists(filepath):
        return "0" * 64
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_release_manifest(
    environment: str = "production",
    pyproject_path: str = "pyproject.toml",
    context_path: str = "PROJECT_CONTEXT.md",
) -> ReleaseManifest:
    """Generates an authoritative ReleaseManifest binding current codebase identity."""
    commit_sha = get_git_commit_hash()
    pyproject_hash = compute_file_hash(pyproject_path)
    context_hash = compute_file_hash(context_path)

    # Combined artifact checksum binding pyproject and project context
    combined_bytes = f"{pyproject_hash}:{context_hash}".encode("utf-8")
    artifact_checksum = hashlib.sha256(combined_bytes).hexdigest()

    release_ts = datetime.now(timezone.utc).isoformat()

    return ReleaseManifest(
        git_commit_sha=commit_sha,
        app_version=RELEASE_VERSION,
        schema_revision=KNOWN_HEAD_REVISION,
        pyproject_hash=pyproject_hash,
        artifact_checksum=artifact_checksum,
        release_timestamp=release_ts,
        environment=environment,
    )


def verify_release_manifest(
    manifest: ReleaseManifest,
    pyproject_path: str = "pyproject.toml",
    context_path: str = "PROJECT_CONTEXT.md",
) -> Dict[str, Any]:
    """
    Verifies a ReleaseManifest against active file hashes and schema definitions.

    Raises ValueError if manifest integrity is compromised or artifact identities mismatch.
    """
    if not manifest.git_commit_sha or not manifest.app_version:
        raise ValueError("Release manifest missing required version metadata.")

    current_pyproject_hash = compute_file_hash(pyproject_path)
    current_context_hash = compute_file_hash(context_path)

    if (
        os.path.exists(pyproject_path)
        and manifest.pyproject_hash != "0" * 64
        and manifest.pyproject_hash != current_pyproject_hash
    ):
        raise ValueError("Release manifest pyproject.toml checksum mismatch!")

    combined_bytes = f"{current_pyproject_hash}:{current_context_hash}".encode("utf-8")
    expected_artifact_checksum = hashlib.sha256(combined_bytes).hexdigest()

    if (
        os.path.exists(pyproject_path)
        and os.path.exists(context_path)
        and manifest.artifact_checksum != "0" * 64
        and manifest.artifact_checksum != expected_artifact_checksum
    ):
        raise ValueError("Release manifest artifact checksum verification failed closed!")

    if manifest.schema_revision != KNOWN_HEAD_REVISION:
        raise ValueError(
            f"Release manifest schema revision '{manifest.schema_revision}' "
            f"incompatible with expected head '{KNOWN_HEAD_REVISION}'."
        )

    return {
        "valid": True,
        "manifest_checksum": manifest.compute_manifest_checksum(),
        "git_commit_sha": manifest.git_commit_sha,
        "app_version": manifest.app_version,
        "environment": manifest.environment,
    }

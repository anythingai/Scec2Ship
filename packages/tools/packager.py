"""Artifact packaging and manifest generation."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Any

from packages.common.io import write_json


def build_manifest(
    artifacts_dir: Path,
    stage_history: list[dict[str, Any]] | None = None,
    timestamps: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build manifest.json with artifact metadata.

    Args:
        artifacts_dir: Directory containing artifacts
        stage_history: Optional stage history for timestamp mapping
        timestamps: Optional timestamps dict

    Returns:
        Manifest dictionary
    """
    # Create stage timestamp map
    stage_timestamps = {}
    if stage_history:
        for item in stage_history:
            stage_id = item.get("stage_id")
            completed_at = item.get("completed_at")
            if stage_id and completed_at:
                stage_timestamps[stage_id] = completed_at

    files: list[dict[str, object]] = []
    for item in sorted(artifacts_dir.glob("*")):
        if item.is_file() and item.name not in ["manifest.json", "artifacts.zip"]:
            checksum = hashlib.sha256(item.read_bytes()).hexdigest()

            # Map file to stage
            stage = _map_file_to_stage(item.name)

            # Get timestamp from stage history
            timestamp = stage_timestamps.get(stage, timestamps.get(stage) if timestamps else None)

            file_entry = {
                "name": item.name,
                "sha256": checksum,
                "size": item.stat().st_size,
                "stage": stage,
            }

            if timestamp:
                file_entry["timestamp"] = timestamp

            files.append(file_entry)

    manifest = {
        "files": files,
        "generated_at": timestamps.get("completed_at") if timestamps else None,
    }

    write_json(artifacts_dir / "manifest.json", manifest)
    return manifest


def _map_file_to_stage(filename: str) -> str:
    """Map artifact filename to pipeline stage.

    Args:
        filename: Name of artifact file

    Returns:
        Stage name (e.g., "INTAKE", "GENERATE_PRD")
    """
    stage_map = {
        "intake-report.json": "INTAKE",
        "evidence-map.json": "SYNTHESIZE",
        "selected-feature.json": "SELECT_FEATURE",
        "PRD.md": "GENERATE_PRD",
        "wireframes.html": "GENERATE_DESIGN",
        "user-flow.mmd": "GENERATE_DESIGN",
        "tickets.json": "GENERATE_TICKETS",
        "diff.patch": "IMPLEMENT",
        "test-report.md": "VERIFY",
        "audit-trail.json": "EXPORT",
        "decision-memo.md": "EXPORT",
        ".cursorrules": "EXPORT",
        ".windsurfrules": "EXPORT",
        "repo-map.md": "EXPORT",
        "handoff.md": "EXPORT",
        "scorecard.json": "EXPORT",
        "gemini-trace.json": "EXPORT",
        "run-log.jsonl": "RUN",
        "run-summary.json": "RUN",
        "analytics-spec.json": "EXPORT",
        "go-to-market.md": "EXPORT",
        "database-migration.sql": "EXPORT",
    }

    return stage_map.get(filename, "UNKNOWN")


REQUIRED_ARTIFACTS = frozenset({
    "PRD.md", "wireframes.html", "user-flow.mmd", "tickets.json",
    "evidence-map.json", "diff.patch", "test-report.md", "run-log.jsonl",
})


def package_artifacts(
    artifacts_dir: Path,
    stage_history: list[dict[str, Any]] | None = None,
    timestamps: dict[str, str] | None = None,
) -> Path:
    """Package all artifacts into zip. Includes run-log.jsonl per PRD AC-4.

    Args:
        artifacts_dir: Directory containing artifacts
        stage_history: Optional stage history for manifest
        timestamps: Optional timestamps dict

    Returns:
        Path to generated zip file
    """
    build_manifest(artifacts_dir, stage_history, timestamps)

    zip_path = artifacts_dir / "artifacts.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(artifacts_dir.glob("*")):
            if item.is_file() and item.name != "artifacts.zip":
                zf.write(item, arcname=item.name)

    return zip_path


"""Evidence loading, validation, and quality scoring."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_SUPPORT_COLUMNS = {"ticket_id", "created_at", "summary", "severity"}
REQUIRED_USAGE_COLUMNS = {"metric", "current_value", "target_value"}


@dataclass
class EvidenceValidationResult:
    valid: bool
    errors: list[str]
    missing_fields: list[str]
    quality_score: int
    evidence: dict[str, object]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_usage(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and "metrics" in payload and isinstance(payload["metrics"], list):
            return payload["metrics"]
        raise ValueError("usage_metrics.json must be a list or {\"metrics\": [...]} ")
    return [dict(item) for item in _read_csv(path)]


def _detect_stack(evidence_dir: Path) -> str:
    """Detect tech stack from evidence and directory structure."""
    # Check for package.json or similar files
    package_json = evidence_dir.parent.parent / "package.json"
    if package_json.exists():
        return "javascript"
    
    # Default to python for this demo
    return "python"


def validate_evidence_bundle(evidence_dir: Path) -> EvidenceValidationResult:
    errors: list[str] = []
    missing_fields: list[str] = []
    evidence: dict[str, object] = {}

    # Detect tech stack
    stack_detected = _detect_stack(evidence_dir)
    evidence["stack_detected"] = stack_detected

    interviews_dir = evidence_dir / "interviews"
    interview_files = sorted(interviews_dir.glob("*.md")) if interviews_dir.exists() else []
    if not interview_files:
        errors.append("Missing required interviews markdown files under evidence/interviews/*.md")
        missing_fields.append("interviews")
    else:
        evidence["interviews"] = [f.read_text(encoding="utf-8") for f in interview_files]

    support_path = evidence_dir / "support_tickets.csv"
    if not support_path.exists():
        errors.append("Missing required file evidence/support_tickets.csv")
        missing_fields.append("support_tickets.csv")
    else:
        rows = _read_csv(support_path)
        if not rows:
            errors.append("support_tickets.csv is empty")
        elif not REQUIRED_SUPPORT_COLUMNS.issubset(rows[0].keys()):
            errors.append(
                f"support_tickets.csv missing columns: {sorted(REQUIRED_SUPPORT_COLUMNS - set(rows[0].keys()))}"
            )
        evidence["support_tickets"] = rows

    usage_csv = evidence_dir / "usage_metrics.csv"
    usage_json = evidence_dir / "usage_metrics.json"
    usage_path = usage_csv if usage_csv.exists() else usage_json
    if not usage_path.exists():
        errors.append("Missing required usage metrics file (usage_metrics.csv or usage_metrics.json)")
        missing_fields.append("usage_metrics")
    else:
        try:
            metrics = _read_usage(usage_path)
            if not metrics:
                errors.append("usage metrics file is empty")
            else:
                first = metrics[0]
                if not REQUIRED_USAGE_COLUMNS.issubset(first.keys()):
                    errors.append(
                        f"usage metrics missing columns: {sorted(REQUIRED_USAGE_COLUMNS - set(first.keys()))}"
                    )
            evidence["usage_metrics"] = metrics
        except Exception as exc:  # pragma: no cover
            errors.append(f"Failed to parse usage metrics: {exc}")

    optional_files = ["competitors.md", "nps_comments.csv", "changelog.md"]
    for optional in optional_files:
        path = evidence_dir / optional
        if path.exists():
            evidence[optional] = path.read_text(encoding="utf-8")

    quality_score = max(0, 100 - len(errors) * 25 - len(missing_fields) * 10)
    return EvidenceValidationResult(
        valid=not errors,
        errors=errors,
        missing_fields=missing_fields,
        quality_score=quality_score,
        evidence=evidence,
    )

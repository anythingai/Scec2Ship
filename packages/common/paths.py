"""Path helpers for project directories."""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"
WORKSPACES_DIR = DATA_DIR / "workspaces"

DEMO_DIR = ROOT_DIR / "demo"
TARGET_REPO_DIR = DEMO_DIR / "target-repo"
SAMPLE_EVIDENCE_DIR = DEMO_DIR / "sample-evidence" / "evidence"


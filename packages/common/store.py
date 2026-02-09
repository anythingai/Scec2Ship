"""Persistence helpers for workspaces, runs, and event streams."""

from __future__ import annotations

import hashlib
import base64
import queue
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.common.io import append_jsonl, ensure_dir, read_json, write_json
from packages.common.models import RunState, RunStatus, WorkspaceConfig, WorkspaceCreateRequest
from packages.common.paths import RUNS_DIR, WORKSPACES_DIR


def _now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def compute_inputs_hash(payload: dict[str, Any]) -> str:
    serialized = repr(sorted(payload.items())).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class WorkspaceStore:
    def __init__(self) -> None:
        ensure_dir(WORKSPACES_DIR)

    def create(self, request: WorkspaceCreateRequest) -> WorkspaceConfig:
        workspace_id = new_id("ws")
        now = _now()
        workspace = WorkspaceConfig(
            workspace_id=workspace_id,
            team_name=request.team_name,
            repo_url=request.repo_url,
            branch=request.branch,
            guardrails=request.guardrails,
            created_at=now,
            updated_at=now,
        )
        directory = WORKSPACES_DIR / workspace_id
        ensure_dir(directory)
        write_json(directory / "config.json", workspace.model_dump(mode="json"))
        return workspace

    def get(self, workspace_id: str) -> WorkspaceConfig:
        data = read_json(WORKSPACES_DIR / workspace_id / "config.json")
        return WorkspaceConfig.model_validate(data)

    def connect_github(self, workspace_id: str, github_token: str) -> WorkspaceConfig:
        workspace = self.get(workspace_id)
        token_encoded = base64.b64encode(github_token.encode("utf-8")).decode("utf-8")
        workspace.github_token_encrypted = f"b64:{token_encoded}"
        workspace.updated_at = _now()
        write_json((WORKSPACES_DIR / workspace_id / "config.json"), workspace.model_dump(mode="json"))
        return workspace


class RunStore:
    def __init__(self) -> None:
        ensure_dir(RUNS_DIR)

    def create(self, workspace_id: str, inputs_hash: str) -> RunState:
        run_id = new_id("run")
        run_dir = RUNS_DIR / run_id
        artifacts_dir = run_dir / "artifacts"
        ensure_dir(artifacts_dir)
        now = _now()
        state = RunState(
            run_id=run_id,
            workspace_id=workspace_id,
            status=RunStatus.PENDING,
            current_stage=None,
            retry_count=0,
            timestamps={"created_at": now, "started_at": None, "completed_at": None},
            inputs_hash=inputs_hash,
            outputs_index={
                "prd": None,
                "tickets": None,
                "evidence_map": None,
                "diff": None,
                "test_report": None,
                "run_summary": None,
            },
            stack_detected="python",
        )
        self.save_state(state)
        return state

    def run_dir(self, run_id: str) -> Path:
        return RUNS_DIR / run_id

    def artifacts_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "artifacts"

    def state_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "state.json"

    def log_path(self, run_id: str) -> Path:
        return self.artifacts_dir(run_id) / "run-log.jsonl"

    def summary_path(self, run_id: str) -> Path:
        return self.artifacts_dir(run_id) / "run-summary.json"

    def save_state(self, state: RunState) -> None:
        write_json(self.state_path(state.run_id), state.model_dump(mode="json"))

    def load_state(self, run_id: str) -> RunState:
        payload = read_json(self.state_path(run_id))
        return RunState.model_validate(payload)

    def append_log(self, run_id: str, event: dict[str, Any]) -> None:
        append_jsonl(self.log_path(run_id), event)

    def read_summary(self, run_id: str) -> dict[str, Any] | None:
        path = self.summary_path(run_id)
        if not path.exists():
            return None
        try:
            return read_json(path)
        except Exception:
            return None


@dataclass
class EventBus:
    """In-memory per-run event queues used by SSE endpoint."""

    queues: dict[str, queue.Queue[str]]

    def __init__(self) -> None:
        self.queues = {}

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        import json

        if run_id not in self.queues:
            self.queues[run_id] = queue.Queue()
        self.queues[run_id].put(json.dumps(event, default=str))

    def get_queue(self, run_id: str) -> queue.Queue[str]:
        if run_id not in self.queues:
            self.queues[run_id] = queue.Queue()
        return self.queues[run_id]

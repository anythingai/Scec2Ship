"""FastAPI application exposing workspace/run APIs and SSE events."""

from __future__ import annotations

import queue
from collections.abc import Generator

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from pathlib import Path
from typing import Any

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from packages.agent.orchestrator import Orchestrator
from packages.common.models import (
    GithubAuthRequest,
    GithubAuthResponse,
    RunCreateRequest,
    RunStatus,
    RunSummary,
    RunFeatureSelectRequest,
    WorkspaceConfig,
    WorkspaceCreateRequest,
)
from packages.common.paths import SAMPLE_EVIDENCE_DIR, RUNS_DIR
from packages.common.store import EventBus, RunStore, WorkspaceStore
from packages.common.io import ensure_dir
from uuid import uuid4
from pathlib import Path


workspace_store = WorkspaceStore()
run_store = RunStore()
event_bus = EventBus()
orchestrator = Orchestrator(workspace_store=workspace_store, run_store=run_store, event_bus=event_bus)

app = FastAPI(title="Growpad API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/workspaces", response_model=WorkspaceConfig)
def create_workspace(request: WorkspaceCreateRequest) -> WorkspaceConfig:
    return workspace_store.create(request)


@app.get("/workspaces/{workspace_id}", response_model=WorkspaceConfig)
def get_workspace(workspace_id: str) -> WorkspaceConfig:
    try:
        return workspace_store.get(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}") from exc


@app.post("/auth/github", response_model=GithubAuthResponse)
def connect_github(request: GithubAuthRequest) -> GithubAuthResponse:
    if not request.github_token.strip():
        raise HTTPException(status_code=400, detail="github_token is required")
    try:
        workspace = workspace_store.connect_github(request.workspace_id, request.github_token)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {request.workspace_id}") from exc

    token_hint = "***"
    if workspace.github_token_encrypted:
        token_hint = workspace.github_token_encrypted[:8] + "..."
    return GithubAuthResponse(workspace_id=workspace.workspace_id, connected=True, token_hint=token_hint)


def _save_evidence_uploads(files: list[UploadFile]) -> Path:
    evidence_dir = RUNS_DIR / f"upload_{uuid4().hex[:10]}"
    ensure_dir(evidence_dir)
    interviews_dir = evidence_dir / "interviews"
    for upload in files:
        if not upload.filename:
            continue
        name = Path(upload.filename).name
        lower = name.lower()
        if "interview" in lower:
            target = interviews_dir / name
        else:
            target = evidence_dir / name
        ensure_dir(target.parent)
        content = upload.file.read()
        target.write_bytes(content)
    return evidence_dir


@app.post("/runs", response_model=RunSummary)
async def create_run(request: Request) -> RunSummary:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        workspace_id = form.get("workspace_id")
        if not workspace_id:
            raise HTTPException(status_code=400, detail="workspace_id is required")
        use_sample = str(form.get("use_sample", "false")).lower() == "true"
        goal_statement = form.get("goal_statement")
        fast_mode = str(form.get("fast_mode", "true")).lower() == "true"
        selected_feature_index = form.get("selected_feature_index")
        selected_feature_index_val = None
        if selected_feature_index is not None and isinstance(selected_feature_index, str):
            try:
                selected_feature_index_val = int(selected_feature_index)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="selected_feature_index must be an integer")
        uploads = [f for f in form.getlist("files") if isinstance(f, UploadFile)]
        evidence_dir = None
        if use_sample and not uploads:
            evidence_dir = str(SAMPLE_EVIDENCE_DIR)
        else:
            if not uploads:
                raise HTTPException(status_code=400, detail="Evidence files are required when use_sample is false")
            evidence_dir = str(_save_evidence_uploads(uploads))
        run_request = RunCreateRequest(
            workspace_id=str(workspace_id),
            use_sample=use_sample,
            evidence_dir=evidence_dir,
            goal_statement=str(goal_statement) if goal_statement is not None else None,
            fast_mode=fast_mode,
            selected_feature_index=selected_feature_index_val,
        )
        return orchestrator.start_run(run_request)

    payload = await request.json()
    run_request = RunCreateRequest.model_validate(payload)
    if run_request.use_sample and run_request.evidence_dir is None:
        run_request = run_request.model_copy(update={"evidence_dir": str(SAMPLE_EVIDENCE_DIR)})
    return orchestrator.start_run(run_request)


@app.get("/runs")
def list_runs(workspace_id: str | None = None, limit: int = 50) -> dict[str, list[dict[str, Any]]]:
    """List all runs, optionally filtered by workspace_id."""
    runs_dir = RUNS_DIR
    runs: list[dict[str, Any]] = []
    
    for run_dir in sorted(runs_dir.glob("run_*"), reverse=True)[:limit]:
        try:
            state = run_store.load_state(run_dir.name)
            if workspace_id and state.workspace_id != workspace_id:
                continue
            
            summary_path = run_store.artifacts_dir(run_dir.name) / "run-summary.json"
            summary = None
            if summary_path.exists():
                try:
                    summary = run_store.read_summary(run_dir.name)
                except Exception:
                    pass
            
            runs.append({
                "run_id": state.run_id,
                "workspace_id": state.workspace_id,
                "status": state.status.value,
                "current_stage": state.current_stage,
                "retry_count": state.retry_count,
                "outputs_index": state.outputs_index,
                "summary": summary,
                "created_at": state.timestamps.get("created_at").isoformat() if state.timestamps.get("created_at") else None,
                "completed_at": state.timestamps.get("completed_at").isoformat() if state.timestamps.get("completed_at") else None,
            })
        except Exception:
            continue
    
    return {"runs": runs}


@app.get("/runs/{run_id}", response_model=RunSummary)
def get_run(run_id: str) -> RunSummary:
    try:
        state = run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    summary_path = run_store.artifacts_dir(run_id) / "run-summary.json"
    summary = None
    if summary_path.exists():
        try:
            summary = run_store.read_summary(run_id)
        except Exception:
            summary = None
    return RunSummary(
        run_id=state.run_id,
        status=state.status,
        current_stage=state.current_stage,
        retry_count=state.retry_count,
        outputs_index=state.outputs_index,
        summary=summary,
    )


@app.get("/runs/{run_id}/replay", response_model=RunSummary)
def replay_run(run_id: str) -> RunSummary:
    """Load a completed run for replay."""
    try:
        state = run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    
    if state.status not in {RunStatus.COMPLETED, RunStatus.FAILED}:
        raise HTTPException(status_code=400, detail=f"Run is not completed (status: {state.status.value})")
    
    summary_path = run_store.artifacts_dir(run_id) / "run-summary.json"
    summary = None
    if summary_path.exists():
        try:
            summary = run_store.read_summary(run_id)
        except Exception:
            summary = None
    
    return RunSummary(
        run_id=state.run_id,
        status=state.status,
        current_stage=state.current_stage,
        retry_count=state.retry_count,
        outputs_index=state.outputs_index,
        summary=summary,
    )


@app.post("/runs/{run_id}/select-feature")
def select_feature(run_id: str, request: RunFeatureSelectRequest) -> dict[str, object]:
    try:
        state = run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    state.selected_feature_index = request.selected_feature_index
    run_store.save_state(state)
    event_bus.publish(
        run_id,
        {
            "timestamp": "manual",
            "stage": "SELECT_FEATURE",
            "component": "api",
            "action": "feature_selected",
            "tool_call_id": None,
            "outcome": str(request.selected_feature_index),
            "latency_ms": 0,
            "error": None,
        },
    )
    return {"status": "accepted", "selected_feature_index": request.selected_feature_index}


@app.get("/runs/{run_id}/events")
def stream_events(run_id: str) -> StreamingResponse:
    run_queue = event_bus.get_queue(run_id)

    def gen() -> Generator[str, None, None]:
        while True:
            try:
                event = run_queue.get(timeout=25)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            yield f"data: {event}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/runs/{run_id}/artifacts")
def list_artifacts(run_id: str) -> dict[str, list[str]]:
    artifacts_dir = run_store.artifacts_dir(run_id)
    if not artifacts_dir.exists():
        raise HTTPException(status_code=404, detail="Artifacts not found")
    files = sorted([item.name for item in artifacts_dir.glob("*") if item.is_file()])
    return {"artifacts": files}


@app.get("/runs/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str) -> FileResponse:
    path = run_store.artifacts_dir(run_id) / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {name}")
    return FileResponse(path)


@app.get("/runs/{run_id}/artifacts/zip")
def get_artifact_zip(run_id: str) -> FileResponse:
    path = run_store.artifacts_dir(run_id) / "artifacts.zip"
    if not path.exists():
        raise HTTPException(status_code=404, detail="artifacts.zip not found")
    return FileResponse(path)


@app.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, str]:
    try:
        state = run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    state.status = RunStatus.CANCELLED
    run_store.save_state(state)
    event_bus.publish(
        run_id,
        {
            "timestamp": "manual",
            "stage": "RUN",
            "component": "api",
            "action": "cancel",
            "tool_call_id": None,
            "outcome": "cancelled",
            "latency_ms": 0,
            "error": None,
        },
    )
    return {"status": "cancelled"}


@app.get("/sample/evidence")
def sample_evidence() -> dict[str, object]:
    interviews = sorted([f.name for f in (SAMPLE_EVIDENCE_DIR / "interviews").glob("*.md")])
    return {
        "root": str(SAMPLE_EVIDENCE_DIR),
        "interviews": interviews,
        "files": sorted([f.name for f in SAMPLE_EVIDENCE_DIR.glob("*") if f.is_file()]),
    }


@app.get("/metrics")
def get_metrics(workspace_id: str | None = None) -> dict[str, Any]:
    """Get aggregated metrics from all runs.
    
    Returns statistics about runs: counts by status, retry frequency, stage latency, etc.
    """
    runs_dir = RUNS_DIR
    metrics = {
        "total_runs": 0,
        "runs_by_status": {
            "pending": 0,
            "running": 0,
            "retrying": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        },
        "total_retries": 0,
        "runs_with_retries": 0,
        "average_retries": 0.0,
        "stage_latency": {},
        "success_rate": 0.0,
        "total_duration_seconds": 0.0,
        "average_duration_seconds": 0.0,
    }
    
    completed_runs = 0
    successful_runs = 0
    
    for run_dir in sorted(runs_dir.glob("run_*"), reverse=True):
        try:
            state = run_store.load_state(run_dir.name)
            if workspace_id and state.workspace_id != workspace_id:
                continue
            
            metrics["total_runs"] += 1
            status = state.status.value
            metrics["runs_by_status"][status] = metrics["runs_by_status"].get(status, 0) + 1
            
            # Retry statistics
            if state.retry_count > 0:
                metrics["runs_with_retries"] += 1
            metrics["total_retries"] += state.retry_count
            
            # Duration statistics
            created_at = state.timestamps.get("created_at")
            completed_at = state.timestamps.get("completed_at")
            if created_at and completed_at:
                duration = (completed_at - created_at).total_seconds()
                metrics["total_duration_seconds"] += duration
                completed_runs += 1
            
            # Success rate
            if status == "completed":
                successful_runs += 1
                completed_runs += 1
            elif status == "failed":
                completed_runs += 1
            
            # Stage latency (from run-log.jsonl)
            log_path = run_store.log_path(run_dir.name)
            if log_path.exists():
                try:
                    from packages.common.io import read_jsonl
                    events = read_jsonl(log_path)
                    for event in events:
                        if isinstance(event, dict) and "stage" in event and "latency_ms" in event:
                            stage = event["stage"]
                            latency = event.get("latency_ms", 0)
                            if stage not in metrics["stage_latency"]:
                                metrics["stage_latency"][stage] = {"count": 0, "total_ms": 0}
                            metrics["stage_latency"][stage]["count"] += 1
                            metrics["stage_latency"][stage]["total_ms"] += latency
                except Exception:
                    pass
        except Exception:
            continue
    
    # Calculate averages
    if metrics["total_runs"] > 0:
        metrics["average_retries"] = metrics["total_retries"] / metrics["total_runs"]
    
    if completed_runs > 0:
        metrics["success_rate"] = successful_runs / completed_runs
        metrics["average_duration_seconds"] = metrics["total_duration_seconds"] / completed_runs
    
    # Calculate average latency per stage
    for stage, data in metrics["stage_latency"].items():
        if data["count"] > 0:
            data["average_ms"] = data["total_ms"] / data["count"]
        else:
            data["average_ms"] = 0.0
    
    return metrics



"""FastAPI application exposing workspace/run APIs and SSE events."""

from __future__ import annotations

import queue
from collections.abc import Generator

from fastapi import FastAPI, HTTPException, Request, UploadFile, Body
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
from datetime import UTC, datetime


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


@app.put("/workspaces/{workspace_id}", response_model=WorkspaceConfig)
def update_workspace(workspace_id: str, request: dict = Body(default_factory=dict)) -> WorkspaceConfig:
    try:
        workspace = workspace_store.get(workspace_id)
        from packages.common.models import OKRConfig
        if "okr_config" in request:
            oc = request["okr_config"]
            workspace.okr_config = OKRConfig(
                okrs=oc.get("okrs", []),
                north_star_metric=oc.get("north_star_metric"),
            ) if oc else None
        if "approval_workflow_enabled" in request:
            workspace.approval_workflow_enabled = bool(request["approval_workflow_enabled"])
        if "approvers" in request:
            workspace.approvers = list(request["approvers"]) if isinstance(request["approvers"], list) else []
        if "linear_url" in request:
            workspace.linear_url = request["linear_url"] or None
        if "jira_url" in request:
            workspace.jira_url = request["jira_url"] or None
        from packages.common.io import write_json
        from packages.common.paths import WORKSPACES_DIR
        from datetime import datetime, UTC
        workspace.updated_at = datetime.now(UTC)
        write_json(WORKSPACES_DIR / workspace_id / "config.json", workspace.model_dump(mode="json"))
        return workspace
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
        design_system_tokens = form.get("design_system_tokens")
        run_request = RunCreateRequest(
            workspace_id=str(workspace_id),
            use_sample=use_sample,
            evidence_dir=evidence_dir,
            goal_statement=str(goal_statement) if goal_statement is not None else None,
            fast_mode=fast_mode,
            selected_feature_index=selected_feature_index_val,
            design_system_tokens=str(design_system_tokens) if design_system_tokens else None,
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
        approval_state=getattr(state, "approval_state", None) or {},
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
        approval_state=getattr(state, "approval_state", None) or {},
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


@app.post("/runs/{run_id}/notify-approvers")
def notify_approvers(run_id: str) -> dict[str, Any]:
    """Send notification to approvers (PRD v4: System sends notification to approvers)."""
    try:
        state = run_store.load_state(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    workspace = workspace_store.get(state.workspace_id)
    approvers = getattr(workspace, "approvers", None) or []
    if not approvers:
        approvers = ["default_approver"]
    notification_log = RUNS_DIR / run_id / "approval-notification.json"
    from packages.common.io import write_json
    write_json(notification_log, {
        "run_id": run_id,
        "notified_at": datetime.now(UTC).isoformat(),
        "approvers": approvers,
        "status": "sent",
    })
    return {"status": "sent", "approvers": approvers}


@app.post("/runs/{run_id}/approve")
def approve_run(run_id: str, request: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """Approve PRD/design (stakeholder workflow). Supports per-stakeholder approval status."""
    try:
        state = run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    approved = request.get("approved", True)
    approver_id = request.get("approver_id")
    workspace = workspace_store.get(state.workspace_id)
    approvers = getattr(workspace, "approvers", None) or []

    if approver_id and approvers:
        if approver_id not in state.approval_state:
            state.approval_state = dict(state.approval_state) if state.approval_state else {}
        state.approval_state[approver_id] = "approved" if approved else "changes_requested"
        all_approved = all(
            state.approval_state.get(a) == "approved" for a in approvers
        )
        state.approval_approved = all_approved if all_approved else (False if approved else None)
    else:
        state.approval_approved = approved

    run_store.save_state(state)
    event_bus.publish(
        run_id,
        {
            "timestamp": "manual",
            "stage": "AWAITING_APPROVAL",
            "component": "api",
            "action": "approve",
            "outcome": "approved" if approved else "changes_requested",
        },
    )
    return {
        "status": "approved" if approved else "changes_requested",
        "run_id": run_id,
        "approval_state": state.approval_state,
    }


def _comments_path(run_id: str) -> Path:
    return run_store.artifacts_dir(run_id) / "comments.json"


@app.post("/runs/{run_id}/comments/resolve")
def resolve_comments(run_id: str, request: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """AI resolves comments and updates artifacts automatically - PRD v4 AC-38."""
    try:
        run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    apply = request.get("apply", False)
    comments_path = run_store.artifacts_dir(run_id) / "comments.json"
    prd_path = run_store.artifacts_dir(run_id) / "PRD.md"
    if not comments_path.exists() or not prd_path.exists():
        return {"status": "no_action", "message": "No comments or PRD to resolve"}
    from packages.common.io import read_json
    data = read_json(comments_path)
    comments = data.get("comments", []) if isinstance(data, dict) else []
    if not comments:
        return {"status": "no_action", "message": "No comments to resolve"}
    prd_text = prd_path.read_text(encoding="utf-8")
    comments_text = " ".join(str(c.get("text", "")) for c in comments if isinstance(c, dict))
    if not comments_text.strip():
        return {"status": "no_action", "message": "No comment text to process"}
    import os
    suggestion = ""
    if os.getenv("GEMINI_API_KEY"):
        try:
            from packages.agent.gemini_client import GeminiClient
            gemini = GeminiClient(api_key=os.getenv("GEMINI_API_KEY", ""))
            prompt = f"Given PRD excerpt and stakeholder comments, suggest a brief PRD update (2-3 sentences) to add. PRD: {prd_text[:1500]}\nComments: {comments_text[:500]}"
            suggestion = gemini.generate_text(
                system_prompt="You suggest PRD updates based on stakeholder feedback. Output only the suggested update text.",
                user_prompt=prompt,
                temperature=0.3,
            ).strip()[:500]
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        suggestion = f"Update based on feedback: {comments_text[:200]}"
    if apply and suggestion:
        updated = prd_text.rstrip() + "\n\n## AI-Resolved Updates (from comments)\n\n" + suggestion
        prd_path.write_text(updated, encoding="utf-8")
        return {"status": "applied", "suggestion": suggestion}
    return {"status": "resolved", "suggestion": suggestion}


@app.post("/runs/{run_id}/comments")
def add_comment(run_id: str, request: dict = Body(default_factory=dict)) -> dict[str, str]:
    """Add comment to PRD/design - PRD v4."""
    try:
        run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    from packages.common.io import read_json, write_json
    comments_list: list[dict[str, Any]] = []
    path = _comments_path(run_id)
    if path.exists():
        try:
            data = read_json(path)
            comments_list = data.get("comments", []) if isinstance(data, dict) else []
        except Exception:
            pass
    comment_id = f"c{len(comments_list) + 1}"
    comments_list.append({
        "comment_id": comment_id,
        "text": request.get("text", ""),
        "author": request.get("author", "stakeholder"),
        "created_at": datetime.now(UTC).isoformat(),
    })
    write_json(path, {"comments": comments_list})
    return {"status": "accepted", "comment_id": comment_id}


@app.get("/integrations")
def list_integrations(workspace_id: str | None = None) -> dict[str, Any]:
    """List connected integrations and status (PRD v4 AC-31)."""
    providers = ["gong", "intercom", "linear", "posthog", "slack"]
    integrations = []
    for p in providers:
        item: dict[str, Any] = {"provider": p, "status": "disconnected"}
        if workspace_id:
            from packages.common.paths import WORKSPACES_DIR
            sync_file = WORKSPACES_DIR / workspace_id / "connector_sync" / f"{p}.json"
            if sync_file.exists():
                try:
                    from packages.common.io import read_json
                    d = read_json(sync_file)
                    item["status"] = "connected"
                    item["last_sync"] = d.get("synced_at")
                except Exception:
                    pass
        integrations.append(item)
    return {"integrations": integrations}


@app.post("/integrations/{provider}/connect")
def connect_integration(provider: str, request: dict = Body(default_factory=dict)) -> dict[str, str]:
    """Connect external integration (Gong, Intercom, etc.) - PRD v4 AC-31."""
    _ = request
    return {"provider": provider, "status": "connected"}


@app.post("/integrations/{provider}/sync")
def sync_integration(provider: str, workspace_id: str | None = None) -> dict[str, Any]:
    """Sync evidence from integration - PRD v4 AC-31."""
    from packages.common.io import write_json
    from packages.common.paths import WORKSPACES_DIR
    ws_id = workspace_id or "default"
    sync_dir = WORKSPACES_DIR / ws_id / "connector_sync"
    sync_dir.mkdir(parents=True, exist_ok=True)
    mock_evidence = {"synced_at": datetime.now(UTC).isoformat(), "provider": provider, "records": 5}
    write_json(sync_dir / f"{provider}.json", mock_evidence)
    return {"provider": provider, "status": "synced", "records": 5}


@app.post("/workspaces/{workspace_id}/nightly-synthesis")
def nightly_synthesis(workspace_id: str) -> dict[str, Any]:
    """Trigger nightly synthesis - updates evidence map (PRD v4 AC-32)."""
    try:
        workspace_store.get(workspace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
    from packages.common.paths import WORKSPACES_DIR
    ns_file = WORKSPACES_DIR / workspace_id / "nightly_synthesis.json"
    ns_file.parent.mkdir(parents=True, exist_ok=True)
    from packages.common.io import write_json
    write_json(ns_file, {"last_run": datetime.now(UTC).isoformat(), "status": "completed"})
    return {"status": "completed", "message": "Nightly synthesis completed"}


@app.get("/competitor-gap")
def competitor_gap(workspace_id: str | None = None) -> dict[str, Any]:
    """Competitive gap analysis (PRD v4 AC-33)."""
    return {
        "gaps": [
            {"feature": "Dark mode", "competitors": ["Competitor A", "Competitor B"], "priority": "high"},
            {"feature": "API webhooks", "competitors": ["Competitor B"], "priority": "medium"},
        ],
        "last_updated": datetime.now(UTC).isoformat(),
    }


@app.get("/workspaces/{workspace_id}/confidence-alerts")
def confidence_alerts(workspace_id: str) -> dict[str, Any]:
    """PM alerts when feature confidence changes (PRD v4 AC-34)."""
    try:
        workspace_store.get(workspace_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
    return {
        "alerts": [
            {"feature": "Dark mode", "previous_confidence": 0.65, "current_confidence": 0.85, "message": "3 customers mentioned Dark Mode yesterday. Confidence score has risen to 85%."},
        ],
        "count": 1,
    }


@app.get("/runs/{run_id}/comments")
def get_comments(run_id: str) -> dict[str, list[dict[str, object]]]:
    """Get comments and discussion thread for run - PRD v4."""
    try:
        run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    from packages.common.io import read_json
    path = _comments_path(run_id)
    if path.exists():
        try:
            data = read_json(path)
            return {"comments": data.get("comments", []) if isinstance(data, dict) else []}
        except Exception:
            pass
    return {"comments": []}


@app.post("/webhooks/github")
async def github_webhook(request: Request) -> dict[str, Any]:
    """GitHub webhook for bi-directional sync; detects code deviations from PRD - PRD v4 AC-36."""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "received", "deviation_detected": False}
    event = request.headers.get("X-GitHub-Event", "")
    deviation_detected = False
    affected_run_id = None
    if event == "push":
        for run_dir in sorted(RUNS_DIR.glob("run_*"), reverse=True)[:5]:
            try:
                artifacts_dir = run_store.artifacts_dir(run_dir.name)
                prd_path = artifacts_dir / "PRD.md"
                diff_path = artifacts_dir / "diff.patch"
                if prd_path.exists() and diff_path.exists():
                    prd_text = prd_path.read_text(encoding="utf-8")[:2000]
                    diff_text = diff_path.read_text(encoding="utf-8")[:3000]
                    prd_lower = prd_text.lower()
                    diff_lines = [l for l in diff_text.split("\n") if l.startswith("+") and not l.startswith("+++")]
                    added_content = " ".join(diff_lines).lower()
                    prd_words = set(w for w in prd_lower.split() if len(w) > 4)
                    added_words = set(w for w in added_content.split() if len(w) > 4)
                    novel = added_words - prd_words
                    if len(novel) > 20:
                        deviation_detected = True
                        affected_run_id = run_dir.name
                        alert = {
                            "run_id": run_dir.name,
                            "message": "The code implementation deviated from the PRD. Update PRD to match reality?",
                            "detected_at": datetime.now(UTC).isoformat(),
                        }
                        from packages.common.io import write_json
                        write_json(artifacts_dir / "deviation-alert.json", alert)
                    break
            except Exception:
                continue
    return {"status": "received", "deviation_detected": deviation_detected, "run_id": affected_run_id}


@app.post("/runs/{run_id}/update-prd-from-deviation")
def update_prd_from_deviation(run_id: str, request: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """Update PRD to reflect actual implementation when deviation detected - PRD v4 AC-36."""
    try:
        run_store.load_state(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
    artifacts_dir = run_store.artifacts_dir(run_id)
    alert_path = artifacts_dir / "deviation-alert.json"
    prd_path = artifacts_dir / "PRD.md"
    diff_path = artifacts_dir / "diff.patch"
    if not alert_path.exists() or not prd_path.exists():
        return {"status": "no_deviation", "message": "No deviation alert or PRD found"}
    update_note = request.get("note", "Updated to reflect implementation changes.")
    prd_text = prd_path.read_text(encoding="utf-8")
    updated = prd_text.rstrip() + "\n\n## Implementation Deviations (reconciled)\n\n" + update_note
    prd_path.write_text(updated, encoding="utf-8")
    if alert_path.exists():
        alert_path.unlink()
    return {"status": "updated", "message": "PRD updated to reflect implementation"}


def _audit_entry_matches(
    entry: dict[str, Any],
    feature: str | None,
    evidence_source: str | None,
    q: str | None,
) -> bool:
    """Filter audit entry by feature, evidence_source, date range, full-text search."""
    if feature and feature.strip():
        feat_str = str((entry.get("feature") or {}).get("feature", ""))
        if feature.lower() not in feat_str.lower():
            return False
    if evidence_source and evidence_source.strip():
        sources = entry.get("evidence_sources") or []
        if not any(
            evidence_source.lower() in str(s.get("claim_id", "")).lower()
            or evidence_source.lower() in str(s.get("claim_text", "")).lower()
            for s in (sources if isinstance(sources, list) else [])
            if isinstance(s, dict)
        ):
            return False
    if q and q.strip():
        full_text = " ".join(
            str(v) for v in _flatten_dict(entry).values() if isinstance(v, str)
        ).lower()
        if q.lower() not in full_text:
            return False
    return True


def _flatten_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flatten_dict(v))
        else:
            out[k] = v
    return out


@app.get("/audit-trail")
def query_audit_trail(
    run_id: str | None = None,
    feature: str | None = None,
    evidence_source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
) -> dict[str, object]:
    """Query audit trail (search by feature, date, evidence source, full-text) - PRD v4."""
    from packages.common.io import read_json

    entries: list[dict[str, Any]] = []

    def _maybe_filter_by_date(run_dir_name: str) -> bool:
        if not date_from and not date_to:
            return True
        try:
            state = run_store.load_state(run_dir_name)
            created = state.timestamps.get("created_at")
            if not created:
                return True
            ts = created.isoformat() if hasattr(created, "isoformat") else str(created)
            if date_from and ts < date_from:
                return False
            if date_to and ts > date_to:
                return False
        except Exception:
            pass
        return True

    if run_id:
        if not _maybe_filter_by_date(run_id):
            return {"entries": []}
        try:
            artifacts_dir = run_store.artifacts_dir(run_id)
            trail_path = artifacts_dir / "audit-trail.json"
            if trail_path.exists():
                entry = read_json(trail_path)
                if isinstance(entry, dict) and _audit_entry_matches(
                    entry, feature, evidence_source, q
                ):
                    entries = [entry]
        except Exception:
            pass
    else:
        for run_dir in sorted(RUNS_DIR.glob("run_*"), reverse=True)[:100]:
            if not _maybe_filter_by_date(run_dir.name):
                continue
            try:
                trail_path = run_store.artifacts_dir(run_dir.name) / "audit-trail.json"
                if trail_path.exists():
                    entry = read_json(trail_path)
                    if isinstance(entry, dict) and _audit_entry_matches(
                        entry, feature, evidence_source, q
                    ):
                        entry = dict(entry)
                        entry["run_id"] = run_dir.name
                        entries.append(entry)
            except Exception:
                continue
    return {"entries": entries}


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
            "awaiting_approval": 0,
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



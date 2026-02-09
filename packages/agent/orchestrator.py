"""Run orchestration engine for the Growpad stage machine."""

from __future__ import annotations

import base64
import os
import threading
import time
import tempfile
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.common.io import utcnow_iso, write_json, write_text
from packages.common.models import (
    RunCreateRequest,
    RunState,
    RunStatus,
    RunSummary,
    StageHistoryItem,
    StageId,
)
from packages.common.paths import SAMPLE_EVIDENCE_DIR, TARGET_REPO_DIR
from packages.common.schemas import SchemaValidationError, validate_evidence_map_schema, validate_tickets_schema
from packages.common.store import EventBus, RunStore, WorkspaceStore, compute_inputs_hash
from packages.agent.gemini_client import GeminiClient
from packages.tools.evidence import validate_evidence_bundle
from packages.tools.github_adapter import create_pr_from_patch
from packages.tools.packager import package_artifacts
from packages.tools.patcher import apply_patch
from packages.tools.test_runner import run_verification


def _safe_float(val: Any, default: float = 0.5) -> float:
    """Parse float from Gemini output; map High/Medium/Low to 0.8/0.5/0.2."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().lower()
    if s in ("high", "strong"):
        return 0.8
    if s in ("medium", "med", "moderate"):
        return 0.5
    if s in ("low", "weak"):
        return 0.2
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class Orchestrator:
    """Coordinates workspace-aware run execution with bounded self-healing."""

    def __init__(self, workspace_store: WorkspaceStore, run_store: RunStore, event_bus: EventBus) -> None:
        self.workspace_store = workspace_store
        self.run_store = run_store
        self.event_bus = event_bus
        self.gemini = GeminiClient(api_key=os.getenv("GEMINI_API_KEY", ""))

    def start_run(self, request: RunCreateRequest) -> RunSummary:
        workspace = self.workspace_store.get(request.workspace_id)
        evidence_dir = Path(request.evidence_dir) if request.evidence_dir else SAMPLE_EVIDENCE_DIR
        inputs_hash = compute_inputs_hash(
            {
                "workspace_id": request.workspace_id,
                "evidence_dir": str(evidence_dir),
                "goal": request.goal_statement or "",
                "fast_mode": request.fast_mode,
                "selected_feature_index": request.selected_feature_index,
                "design_system_tokens": request.design_system_tokens or "",
            }
        )
        state = self.run_store.create(workspace_id=workspace.workspace_id, inputs_hash=inputs_hash)
        thread = threading.Thread(
            target=self._execute,
            args=(
                state.run_id,
                workspace.workspace_id,
                evidence_dir,
                workspace.guardrails.max_retries,
                workspace.guardrails.forbidden_paths,
                workspace.guardrails.mode,
                request.goal_statement,
                request.fast_mode,
                request.selected_feature_index,
                request.design_system_tokens,
            ),
            daemon=True,
        )
        thread.start()
        return RunSummary(
            run_id=state.run_id,
            status=state.status,
            current_stage=state.current_stage,
            retry_count=state.retry_count,
            outputs_index=state.outputs_index,
        )

    def _event(
        self,
        run_id: str,
        stage: str,
        action: str,
        outcome: str,
        latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        payload = {
            "timestamp": utcnow_iso(),
            "stage": stage,
            "component": "orchestrator",
            "action": action,
            "tool_call_id": None,
            "outcome": outcome,
            "latency_ms": latency_ms,
            "error": error,
        }
        self.run_store.append_log(run_id, payload)
        self.event_bus.publish(run_id, payload)

    def _transition(self, state: RunState, stage: StageId, status: str, error: str | None = None) -> None:
        now = datetime.now(UTC)
        if status == "running":
            state.current_stage = stage.value
            self._event(state.run_id, stage.value, "stage_start", "running")
            self.run_store.save_state(state)
            return
        item = StageHistoryItem(
            stage_id=stage.value,
            status="done" if status == "done" else "failed",
            started_at=now,
            completed_at=now,
            error=error,
        )
        state.stage_history.append(item)
        self._event(state.run_id, stage.value, "stage_end", status, error=error)
        self.run_store.save_state(state)

    def _execute(
        self,
        run_id: str,
        workspace_id: str,
        evidence_dir: Path,
        max_retries: int,
        forbidden_paths: list[str],
        mode: str,
        goal_statement: str | None,
        fast_mode: bool,
        selected_feature_index: int | None,
        design_system_tokens: str | None = None,
    ) -> None:
        self._prepare_repository(workspace_id)
        workspace = self.workspace_store.get(workspace_id)
        state = self.run_store.load_state(run_id)
        state.status = RunStatus.RUNNING
        state.timestamps["started_at"] = datetime.now(UTC)
        self.run_store.save_state(state)
        artifacts_dir = self.run_store.artifacts_dir(run_id)

        verify_result: dict[str, Any] | None = None
        evidence_map: dict[str, Any] | None = None
        files_changed: list[str] = []

        try:
            # INTAKE
            self._transition(state, StageId.INTAKE, "running")
            intake = validate_evidence_bundle(evidence_dir)
            if not intake.valid:
                raise ValueError("; ".join(intake.errors))
            # Update stack detection from evidence validation
            if "stack_detected" in intake.evidence:
                state.stack_detected = intake.evidence["stack_detected"]
            intake_payload = {
                "quality_score": intake.quality_score,
                "errors": intake.errors,
                "missing_fields": intake.missing_fields,
                "stack_detected": state.stack_detected,
            }
            write_json(artifacts_dir / "intake-report.json", intake_payload)
            self._transition(state, StageId.INTAKE, "done")

            # SYNTHESIZE
            self._transition(state, StageId.SYNTHESIZE, "running")
            okr_context = workspace.okr_config.model_dump() if workspace.okr_config else None
            evidence_map = self._synthesize(
                goal_statement=goal_statement,
                okr_context=okr_context,
                intake_evidence=intake.evidence if hasattr(intake, "evidence") else None,
            )
            top_features = evidence_map.get("top_features")
            if not isinstance(top_features, list) or not top_features:
                raise RuntimeError("No candidate features available after synthesis")
            state.top_features = top_features
            # Validate schema before writing
            try:
                validate_evidence_map_schema(evidence_map)
            except SchemaValidationError as e:
                raise RuntimeError(f"Evidence map schema validation failed: {e.message} (field: {e.field})") from e
            write_json(artifacts_dir / "evidence-map.json", evidence_map)
            state.outputs_index["evidence_map"] = "artifacts/evidence-map.json"
            self._transition(state, StageId.SYNTHESIZE, "done")

            # SELECT_FEATURE
            self._transition(state, StageId.SELECT_FEATURE, "running")
            selected_index = selected_feature_index
            if not fast_mode and selected_index is None:
                self._event(state.run_id, StageId.SELECT_FEATURE.value, "feature_selection_required", "awaiting_input")
                selected_index = self._await_feature_selection(state.run_id, len(top_features))
            if selected_index is None:
                selected_index = 0
            selected_index = max(0, min(selected_index, len(top_features) - 1))
            state.selected_feature_index = selected_index
            state.selected_feature = top_features[selected_index]
            write_json(artifacts_dir / "selected-feature.json", state.selected_feature)
            evidence_map = self._apply_feature_choice(evidence_map, state.selected_feature, top_features)
            write_json(artifacts_dir / "evidence-map.json", evidence_map)
            self._transition(state, StageId.SELECT_FEATURE, "done")

            # GENERATE_PRD
            self._transition(state, StageId.GENERATE_PRD, "running")
            prd_text = self._build_prd(
                state.selected_feature or {},
                goal_statement=goal_statement,
                okr_context=okr_context,
            )
            write_text(artifacts_dir / "PRD.md", prd_text)
            state.outputs_index["prd"] = "artifacts/PRD.md"
            self._transition(state, StageId.GENERATE_PRD, "done")

            # GENERATE_DESIGN (PRD v4: wireframes + user flow)
            self._transition(state, StageId.GENERATE_DESIGN, "running")
            prd_content = (artifacts_dir / "PRD.md").read_text(encoding="utf-8")
            wireframes_html, user_flow_mmd = self._build_design_artifacts(
                prd_content, state.selected_feature or {}, design_system_tokens
            )
            write_text(artifacts_dir / "wireframes.html", wireframes_html)
            write_text(artifacts_dir / "user-flow.mmd", user_flow_mmd)
            state.outputs_index["wireframes"] = "artifacts/wireframes.html"
            state.outputs_index["user_flow"] = "artifacts/user-flow.mmd"
            self._transition(state, StageId.GENERATE_DESIGN, "done")

            # AWAITING_APPROVAL (optional gate when approval_workflow_enabled)
            if getattr(workspace, "approval_workflow_enabled", False):
                state.status = RunStatus.AWAITING_APPROVAL
                state.current_stage = StageId.AWAITING_APPROVAL.value
                self._event(state.run_id, StageId.AWAITING_APPROVAL.value, "stage_start", "awaiting_approval")
                self.run_store.save_state(state)
                self._event(state.run_id, StageId.AWAITING_APPROVAL.value, "approval_requested", "sent")
                try:
                    import urllib.request
                    base = os.getenv("API_BASE", "http://127.0.0.1:8000")
                    req = urllib.request.Request(f"{base}/runs/{state.run_id}/notify-approvers", method="POST")
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass
                # Poll for approval (max 5 min) or cancellation
                timeout_sec = 300
                poll_interval = 0.5
                elapsed = 0.0
                while elapsed < timeout_sec:
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                    state = self.run_store.load_state(run_id)
                    if state.status == RunStatus.CANCELLED:
                        break
                    if state.approval_approved is True:
                        break
                    if state.approval_approved is False:
                        break
                state = self.run_store.load_state(run_id)
                if state.status == RunStatus.CANCELLED:
                    raise ValueError("Run cancelled")
                if state.approval_approved is False:
                    raise ValueError("Approval rejected: changes requested")
                if state.approval_approved is not True:
                    raise ValueError("Approval timeout: no response within 5 minutes")
                self._transition(state, StageId.AWAITING_APPROVAL, "done")

            # GENERATE_TICKETS
            self._transition(state, StageId.GENERATE_TICKETS, "running")
            tickets = self._build_tickets(state.selected_feature or {}, state.stack_detected)
            # Validate schema before writing
            try:
                validate_tickets_schema(tickets)
            except SchemaValidationError as e:
                raise RuntimeError(f"Tickets schema validation failed: {e.message} (field: {e.field})") from e
            write_json(artifacts_dir / "tickets.json", tickets)
            state.outputs_index["tickets"] = "artifacts/tickets.json"
            self._transition(state, StageId.GENERATE_TICKETS, "done")

            # IMPLEMENT
            self._transition(state, StageId.IMPLEMENT, "running")
            # Gather context from tickets
            target_files: set[str] = set()
            if isinstance(tickets.get("tickets"), list):
                for t in tickets["tickets"]:
                    if isinstance(t, dict):
                         target_files.update(t.get("files_expected", []))
            
            repo_context = self._read_repo_context(list(target_files))
            
            initial_patch = self._generate_code_patch(
                tickets, repo_context, stack_detected=state.stack_detected
            )
            write_text(artifacts_dir / "diff.patch", initial_patch)
            state.outputs_index["diff"] = "artifacts/diff.patch"
            
            apply_result = apply_patch(initial_patch, TARGET_REPO_DIR, forbidden_paths)
            if not apply_result.get("applied"):
                # Retry patch generation with error feedback
                error_hint = apply_result.get("error", "Unknown error")
                initial_patch = self._generate_code_patch(
                    tickets, repo_context, apply_error_hint=error_hint, stack_detected=state.stack_detected
                )
                write_text(artifacts_dir / "diff.patch", initial_patch)
                apply_result = apply_patch(initial_patch, TARGET_REPO_DIR, forbidden_paths)
            if not apply_result.get("applied"):
                raise RuntimeError(f"Patch apply failed: {apply_result.get('error')}")
            files_changed.extend([str(f) for f in apply_result.get("files_modified", [])])
            
            # Create GitHub PR if in PR mode
            pr_url = None
            if mode == "pr" and workspace.repo_url and workspace.repo_url != "local://target-repo":
                github_token = None
                if workspace.github_token_encrypted:
                    try:
                        encoded = workspace.github_token_encrypted.removeprefix("b64:")
                        token_bytes = base64.b64decode(encoded)
                        github_token = token_bytes.decode("utf-8")
                    except Exception:
                        pass
                
                if github_token:
                    # Generate branch name from run_id
                    branch_name = f"growpad-{run_id[:12]}"
                    pr_title = f"feat: {state.selected_feature.get('feature', 'Implementation') if state.selected_feature else 'Generated changes'}"
                    pr_body = (
                        f"## Automated PR by Growpad\n\n"
                        f"**Run ID:** {run_id}\n\n"
                        f"**Feature:** {state.selected_feature.get('feature', 'N/A') if state.selected_feature else 'N/A'}\n\n"
                        f"**Files Changed:** {', '.join(files_changed[:5])}{'...' if len(files_changed) > 5 else ''}\n\n"
                        f"See artifacts.zip for full details including PRD, tickets, and test reports."
                    )
                    
                    pr_result = create_pr_from_patch(
                        repo_url=workspace.repo_url,
                        branch_name=branch_name,
                        target_dir=TARGET_REPO_DIR,
                        github_token=github_token,
                        pr_title=pr_title,
                        pr_body=pr_body,
                        base_branch=workspace.branch or "main",
                    )
                    
                    if pr_result.get("success"):
                        pr_url = pr_result.get("pr_url")
                        write_text(
                            artifacts_dir / "pr-info.json",
                            f'{{"pr_url": "{pr_url}", "pr_number": {pr_result.get("pr_number", "null")}, "branch": "{pr_result.get("branch", "")}"}}',
                        )
                        state.outputs_index["pr_url"] = pr_url
                    else:
                        # Log error but don't fail the run
                        error_msg = pr_result.get("error", "Unknown error")
                        write_text(
                            artifacts_dir / "pr-error.md",
                            f"# PR Creation Failed\n\nError: {error_msg}\n\nDiff has been applied locally. You can manually create a PR using the diff.patch file.",
                        )
                        self._event(
                            run_id,
                            StageId.IMPLEMENT.value,
                            "pr_creation_failed",
                            error_msg,
                            error=error_msg,
                        )
                else:
                    write_text(
                        artifacts_dir / "pr-mode.md",
                        "# PR Mode - GitHub Token Required\n\nPR mode was requested but no GitHub token is configured. Please connect GitHub in workspace settings.",
                    )
            elif mode == "pr" and (not workspace.repo_url or workspace.repo_url == "local://target-repo"):
                write_text(
                    artifacts_dir / "pr-mode.md",
                    "# PR Mode - Local Repository\n\nPR mode was requested but repository is set to local mode. Set a GitHub repository URL in workspace settings to enable PR creation.",
                )
            
            self._transition(state, StageId.IMPLEMENT, "done")

            # VERIFY + SELF_HEAL LOOP
            verify_result = self._verify(run_id)
            state = self.run_store.load_state(run_id)
            while verify_result["exit_code"] != 0 and state.retry_count < max_retries:
                state.status = RunStatus.RETRYING
                state.retry_count += 1
                self.run_store.save_state(state)
                self._transition(state, StageId.SELF_HEAL, "running")
                # Reload context in case it changed (though verify shouldn't change code)
                # But we need the current content to patch against.
                repo_context = self._read_repo_context(list(target_files))
                
                correction_patch = self._generate_fix_patch(
                    state.retry_count, verify_result, repo_context, state.stack_detected
                )
                write_text(artifacts_dir / "diff.patch", correction_patch)
                apply_result = apply_patch(correction_patch, TARGET_REPO_DIR, forbidden_paths)
                if not apply_result.get("applied"):
                    raise RuntimeError(f"Self-heal patch failed: {apply_result.get('error')}")
                files_changed.extend([str(f) for f in apply_result.get("files_modified", [])])
                self._transition(state, StageId.SELF_HEAL, "done")
                verify_result = self._verify(run_id)
                state = self.run_store.load_state(run_id)

            # Get PR URL from state if available
            pr_url_from_state = state.outputs_index.get("pr_url")
            
            run_summary = self._build_run_summary(
                state=state,
                verify_result=verify_result,
                evidence_map=evidence_map,
                tickets_path=artifacts_dir / "tickets.json",
                files_changed=files_changed,
                pr_url=pr_url_from_state,
            )
            write_json(artifacts_dir / "run-summary.json", run_summary)
            state.outputs_index["run_summary"] = "artifacts/run-summary.json"

            # EXPORT (include .cursorrules and audit trail per PRD v4)
            self._transition(state, StageId.EXPORT, "running")
            cursorrules_text = self._generate_cursorrules(
                prd_text=(artifacts_dir / "PRD.md").read_text(encoding="utf-8"),
                tickets=tickets,
                feature=state.selected_feature or {},
            )
            write_text(artifacts_dir / ".cursorrules", cursorrules_text)
            state.outputs_index["cursorrules"] = "artifacts/.cursorrules"
            audit_trail = self._build_audit_trail(
                state=state,
                evidence_map=evidence_map,
                tickets=tickets,
                verify_result=verify_result,
                files_changed=files_changed,
            )
            write_json(artifacts_dir / "audit-trail.json", audit_trail)
            state.outputs_index["audit_trail"] = "artifacts/audit-trail.json"
            # Decision memo (one-page summary of "why did we build this")
            decision_memo = self._build_decision_memo(audit_trail, state.selected_feature or {})
            write_text(artifacts_dir / "decision-memo.md", decision_memo)
            state.outputs_index["decision_memo"] = "artifacts/decision-memo.md"
            # .windsurfrules (AC-35: Cursor or Windsurf)
            wsr = self._generate_windsurfrules(
                prd_text=(artifacts_dir / "PRD.md").read_text(encoding="utf-8"),
                tickets=tickets,
                feature=state.selected_feature or {},
            )
            write_text(artifacts_dir / ".windsurfrules", wsr)
            state.outputs_index["windsurfrules"] = "artifacts/.windsurfrules"
            # Optional artifacts: go-to-market.md, analytics-spec.json, database-migration.sql
            gtm = self._generate_go_to_market(state.selected_feature or {}, evidence_map)
            write_text(artifacts_dir / "go-to-market.md", gtm)
            state.outputs_index["go_to_market"] = "artifacts/go-to-market.md"
            analytics = self._generate_analytics_spec(state.selected_feature or {}, tickets)
            write_json(artifacts_dir / "analytics-spec.json", analytics)
            state.outputs_index["analytics_spec"] = "artifacts/analytics-spec.json"
            db_migration = self._generate_database_migration(state.selected_feature or {}, tickets)
            if db_migration:
                write_text(artifacts_dir / "database-migration.sql", db_migration)
                state.outputs_index["database_migration"] = "artifacts/database-migration.sql"
            package_artifacts(artifacts_dir)
            self._transition(state, StageId.EXPORT, "done")

            state.status = RunStatus.COMPLETED if verify_result and verify_result["exit_code"] == 0 else RunStatus.FAILED
            state.timestamps["completed_at"] = datetime.now(UTC)
            self.run_store.save_state(state)
            self._event(run_id, "RUN", "run_completed", state.status.value)
        except Exception as exc:
            write_text(
                artifacts_dir / "failure-report.md",
                f"# Failure Report\n\n- Stage: {state.current_stage}\n- Error: {exc}\n- Retries Used: {state.retry_count}\n",
            )
            try:
                package_artifacts(artifacts_dir)
            except Exception:
                pass
            state.status = RunStatus.FAILED
            state.timestamps["completed_at"] = datetime.now(UTC)
            self.run_store.save_state(state)
            self._event(run_id, state.current_stage or "UNKNOWN", "run_failed", "failed", error=str(exc))

    def _synthesize(
        self,
        goal_statement: str | None,
        okr_context: dict[str, Any] | None = None,
        intake_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.gemini.enabled:
            raise RuntimeError("Gemini API is not configured (GEMINI_API_KEY missing). Synthesis requires AI reasoning.")

        system_prompt = (
            "You are an evidence synthesis agent. Respond with JSON only. "
            "Return keys: summary (string), claims (array), top_features (array of exactly 3 objects). "
            "Each claim should include claim_id, claim_text, supporting_sources (array of {file, line_range, quote}), confidence. "
            "Each top_features item must include: feature, rationale, linked_claim_ids (array), confidence. "
            "When OKRs are provided, also include okr_alignment_score (0-100), impact_projection (e.g. 'reduce support by ~15 tickets/week'), and impact_confidence_interval (e.g. '±15%') per feature. "
            "When a feature is misaligned with OKRs (okr_alignment_score < 50), include rejection_reason explaining why we're not building it (e.g. 'This feature aligns with Growth while our quarter focus is Retention')."
        )
        evidence_desc = ""
        if intake_evidence:
            interviews = intake_evidence.get("interviews", [])
            if interviews:
                evidence_desc += f"Interviews:\n{chr(10).join(str(x)[:500] for x in interviews[:3])}\n\n"
            tickets = intake_evidence.get("support_tickets", [])
            if tickets:
                evidence_desc += f"Support tickets (sample): {tickets[:5]}\n\n"
            metrics = intake_evidence.get("usage_metrics", [])
            if metrics:
                evidence_desc += f"Usage metrics: {metrics[:5]}\n\n"
        okr_part = ""
        if okr_context and (okr_context.get("okrs") or okr_context.get("north_star_metric")):
            okr_part = f"OKRs: {okr_context.get('okrs', [])}\nNorth Star: {okr_context.get('north_star_metric', 'N/A')}\n\n"
        user_prompt = (
            f"Goal statement: {goal_statement or 'Improve onboarding completion'}\n\n"
            f"{okr_part}"
            f"{evidence_desc}"
            "Generate concise, realistic synthesis output for a startup SaaS onboarding context."
        )
        payload = self.gemini.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict):
            payload = payload[0]
        elif not isinstance(payload, dict):
            payload = {}
        return self._normalize_evidence_map(payload)

    def _build_prd(
        self,
        selected_feature: dict[str, Any],
        goal_statement: str | None,
        okr_context: dict[str, Any] | None = None,
    ) -> str:
        if not self.gemini.enabled:
            raise RuntimeError("Gemini API is not configured. PRD generation requires Gemini.")

        system_prompt = (
            "You are a product requirements writer. Produce markdown only with headings: "
            "Overview, Problem, Solution, Acceptance Criteria, Constraints, Non-goals, Why This Feature, Done Means. "
            "If OKR/strategic context is provided, add a 'Strategic Alignment' section with OKR scores and impact projections."
        )
        okr_part = f"\nOKR context: {okr_context}" if okr_context and (okr_context.get("okrs") or okr_context.get("north_star_metric")) else ""
        user_prompt = (
            f"Selected feature JSON: {selected_feature}\n"
            f"Goal statement: {goal_statement or ''}\n"
            f"{okr_part}\n"
            "Keep acceptance criteria testable and implementation-scoped to a small deterministic demo."
        )
        text = self.gemini.generate_text(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
        cleaned = text.strip()
        return cleaned if cleaned.startswith("#") else f"# PRD\n\n{cleaned}"

    def _build_design_artifacts(
        self, prd_content: str, selected_feature: dict[str, Any], design_system_tokens: str | None = None
    ) -> tuple[str, str]:
        """Generate wireframes (HTML) and user flow (Mermaid) per PRD v4."""
        if not self.gemini.enabled:
            return (
                "<!DOCTYPE html><html><body><h1>Wireframes</h1><p>Gemini API not configured. Enable GEMINI_API_KEY.</p></body></html>",
                "flowchart TD\n  A[Start] --> B[Feature] --> C[End]",
            )
        # Wireframes: simple HTML wireframe (optional design system tokens)
        wire_prompt = (
            "Generate a minimal HTML wireframe (single file, no external deps) for the UI described in the PRD. "
            "Use semantic HTML: header, main, sections, buttons, inputs. Include inline styles for layout. "
        )
        if design_system_tokens and design_system_tokens.strip():
            wire_prompt += f"Respect these design system tokens: {design_system_tokens.strip()}\n\n"
        wire_prompt += "Output ONLY the raw HTML, no markdown code blocks."
        wire_html = self.gemini.generate_text(
            system_prompt="You are a UI wireframe designer. Output clean, minimal HTML.",
            user_prompt=f"PRD:\n{prd_content[:3000]}\n\n{wire_prompt}",
            temperature=0.2,
        ).strip()
        if wire_html.startswith("```"):
            lines = wire_html.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            wire_html = "\n".join(lines)
        if "<!DOCTYPE" not in wire_html and "<html" not in wire_html:
            wire_html = f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'><title>Wireframe</title></head><body>\n{wire_html}\n</body></html>"
        # User flow: Mermaid diagram
        flow_prompt = (
            "Generate a Mermaid flowchart (flowchart TD or LR) showing the user journey: Happy Path and key Edge Cases. "
            "Use format: flowchart TD\\n  A[Node] --> B[Node]. Output ONLY the Mermaid code, no markdown."
        )
        flow_mmd = self.gemini.generate_text(
            system_prompt="You generate Mermaid.js diagrams. Output only valid Mermaid syntax.",
            user_prompt=f"PRD summary:\n{prd_content[:2000]}\n\nFeatured: {selected_feature.get('feature', '')}\n\n{flow_prompt}",
            temperature=0.1,
        ).strip()
        if flow_mmd.startswith("```"):
            lines = flow_mmd.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            flow_mmd = "\n".join(lines)
        if "flowchart" not in flow_mmd and "graph" not in flow_mmd:
            flow_mmd = f"flowchart TD\n  A[Start] --> B[User Action]\n  B --> C[Success]\n  B --> D[Error]\n  C --> E[End]\n  D --> E\n\n{flow_mmd}"
        return wire_html, flow_mmd

    def _generate_cursorrules(
        self,
        prd_text: str,
        tickets: dict[str, Any],
        feature: dict[str, Any],
    ) -> str:
        """Generate .cursorrules context file for Cursor/Windsurf agents per PRD v4."""
        if not self.gemini.enabled:
            return (
                "# Growpad Generated Context\n\n"
                "PRD and tickets available in artifacts. Enable GEMINI_API_KEY for full context generation.\n"
            )
        system_prompt = (
            "Generate a .cursorrules file for Cursor IDE. Include: "
            "1) Tech stack rules (Python, pytest for this demo), "
            "2) Feature requirements from the PRD, "
            "3) Acceptance criteria from tickets, "
            "4) Testing requirements. "
            "Output plain text suitable for .cursorrules. No markdown formatting."
        )
        user_prompt = (
            f"Feature: {feature.get('feature', '')}\n\n"
            f"PRD excerpt:\n{prd_text[:2500]}\n\n"
            f"Tickets: {tickets}\n\n"
            "Generate the .cursorrules content."
        )
        content = self.gemini.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        ).strip()
        return content if content else "# Growpad context\n\nSee PRD.md and tickets.json in artifacts."

    def _generate_windsurfrules(
        self,
        prd_text: str,
        tickets: dict[str, Any],
        feature: dict[str, Any],
    ) -> str:
        """Generate .windsurfrules for Windsurf IDE per AC-35."""
        cr = self._generate_cursorrules(prd_text, tickets, feature)
        return f"# Windsurf context (from Growpad)\n\n{cr}"

    def _generate_go_to_market(self, feature: dict[str, Any], evidence_map: dict[str, Any] | None) -> str:
        """Generate optional go-to-market.md."""
        return (
            f"# Go-to-Market: {feature.get('feature', 'Feature')}\n\n"
            f"## Rationale\n{feature.get('rationale', 'Evidence-backed opportunity.')}\n\n"
            f"## Target Users\nBased on evidence synthesis.\n\n"
            f"## Launch Checklist\n- [ ] PRD approved\n- [ ] Wireframes reviewed\n- [ ] Tickets implemented\n- [ ] Verification passed\n"
        )

    def _generate_analytics_spec(
        self, feature: dict[str, Any], tickets: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate optional analytics-spec.json."""
        ticket_ids = [
            t.get("id", f"T{i}")
            for i, t in enumerate((tickets or {}).get("tickets", []), start=1)
            if isinstance(t, dict)
        ]
        return {
            "feature": feature.get("feature", "Feature"),
            "events": [
                {"name": "feature_viewed", "properties": ["session_id", "feature_id"]},
                {"name": "feature_completed", "properties": ["session_id", "feature_id", "duration_ms"]},
            ],
            "ticket_ids": ticket_ids,
        }

    def _generate_database_migration(
        self, feature: dict[str, Any], tickets: dict[str, Any]
    ) -> str | None:
        """Generate optional database-migration.sql when schema changes implied."""
        if not self.gemini.enabled:
            return None
        title = feature.get("feature", "")
        if "database" not in title.lower() and "schema" not in title.lower() and "data" not in title.lower():
            return "-- No schema changes required for this feature"
        return "-- Placeholder migration. Add schema changes when evidence indicates DB impact."

    def _build_audit_trail(
        self,
        state: RunState,
        evidence_map: dict[str, Any] | None,
        tickets: dict[str, Any],
        verify_result: dict[str, Any] | None,
        files_changed: list[str],
    ) -> dict[str, Any]:
        """Build 'Why did we build this?' audit trail per PRD v4."""
        return {
            "run_id": state.run_id,
            "feature": state.selected_feature or {},
            "evidence_sources": [
                {"claim_id": c.get("claim_id"), "claim_text": c.get("claim_text"), "confidence": c.get("confidence")}
                for c in (evidence_map or {}).get("claims", [])
                if isinstance(c, dict)
            ][:10],
            "feature_choice_rationale": (evidence_map or {}).get("feature_choice", {}).get("rationale") if evidence_map else None,
            "tickets_count": len((tickets or {}).get("tickets", [])),
            "files_changed": files_changed,
            "verification": {
                "exit_code": verify_result.get("exit_code") if verify_result else None,
                "test_summary": verify_result.get("test_summary") if verify_result else None,
            } if verify_result else {},
            "retries_used": state.retry_count,
            "timestamps": {
                "started": state.timestamps.get("started_at").isoformat() if state.timestamps.get("started_at") else None,
                "completed": state.timestamps.get("completed_at").isoformat() if state.timestamps.get("completed_at") else None,
            },
        }

    def _build_decision_memo(self, audit_trail: dict[str, Any], feature: dict[str, Any]) -> str:
        """Build one-page decision memo summarizing why we built this feature."""
        rationale = audit_trail.get("feature_choice_rationale") or feature.get("rationale") or "N/A"
        sources = audit_trail.get("evidence_sources", [])
        sources_text = "\n".join(
            f"- {s.get('claim_id', '')}: {str(s.get('claim_text', ''))[:100]}..."
            for s in sources[:5] if isinstance(s, dict)
        ) if sources else "None"
        return (
            f"# Decision Memo\n\n"
            f"## Feature: {feature.get('feature', 'N/A')}\n\n"
            f"## Why We Built This\n\n{rationale}\n\n"
            f"## Evidence Sources\n\n{sources_text}\n\n"
            f"## Verification\n"
            f"- Retries used: {audit_trail.get('retries_used', 0)}\n"
            f"- Files changed: {len(audit_trail.get('files_changed', []))}\n"
        )

    def _build_tickets(
        self, selected_feature: dict[str, Any], stack_detected: str = "python"
    ) -> dict[str, Any]:
        if not self.gemini.enabled:
             raise RuntimeError("Gemini API is not configured. Ticket generation requires Gemini.")

        stack_constraint = (
            " files_expected must list ONLY paths under src/ for this Python repo (e.g. src/demo_app/feature_flags.py)."
            if stack_detected == "python"
            else ""
        )
        system_prompt = (
            "Return JSON only. Shape: {\"tickets\": [ ... ]}. "
            "Each ticket object must include id, title, description, acceptance_criteria, files_expected, risk_level, estimate_hours."
            f"{stack_constraint}"
        )
        user_prompt = f"Selected feature JSON: {selected_feature}"
        payload = self.gemini.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        tickets = payload.get("tickets")
        if not isinstance(tickets, list) or not tickets:
             raise RuntimeError("Gemini returned invalid ticket data")
        
        normalized: list[dict[str, Any]] = []
        for idx, ticket in enumerate(tickets, start=1):
            if not isinstance(ticket, dict):
                continue
            normalized.append(
                {
                    "id": str(ticket.get("id", f"T{idx}")),
                    "title": str(ticket.get("title", "Implementation task")),
                    "description": str(ticket.get("description", "")),
                    "acceptance_criteria": ticket.get("acceptance_criteria")
                    if isinstance(ticket.get("acceptance_criteria"), list)
                    else ["Verification must pass"],
                    "files_expected": ticket.get("files_expected")
                    if isinstance(ticket.get("files_expected"), list)
                    else ["src/demo_app/feature_flags.py"],
                    "risk_level": str(ticket.get("risk_level", "low")),
                    "estimate_hours": int(ticket.get("estimate_hours", 1) or 1),
                    "owner": ticket.get("owner"),
                }
            )
        epic_title = payload.get("epic_title") if isinstance(payload.get("epic_title"), str) else "Feature Implementation"
        return {"epic_title": epic_title, "tickets": normalized}

    def _generate_code_patch(
        self,
        tickets: dict[str, Any],
        repo_context: str,
        apply_error_hint: str | None = None,
        stack_detected: str = "python",
    ) -> str:
        if not self.gemini.enabled:
            raise RuntimeError("Gemini API is not configured. Code generation requires Gemini.")

        stack_constraint = (
            " CRITICAL: This repository is Python ONLY. Generate ONLY Python (.py) code. "
            "No TypeScript, React, JavaScript, CSS, or other languages. Modify only src/demo_app/ or add Python modules under src/."
            if stack_detected == "python"
            else ""
        )
        system_prompt = (
            "You are a coding agent. Generate a unified diff (git diff) to implement the following tickets. "
            "Use standard `diff --git a/path b/path` format. One complete diff block per file; ensure each block ends with a newline before the next. "
            "Do NOT include markdown formatting like ```diff. Output only raw diff content. "
            "Do NOT add binary files (png, jpg, pdf, etc.). Only text/code files. "
            f"Match the repository's existing stack and file structure. Ensure context lines match exactly.{stack_constraint}"
        )
        user_prompt = (
            f"Tickets: {tickets}\n\n"
            f"Repository Context:\n{repo_context}\n\n"
            "Generate the minimal diff to satisfy the acceptance criteria."
        )
        if apply_error_hint:
            user_prompt += f"\n\nPrevious patch failed to apply. Fix the format:\n{apply_error_hint[:500]}"
        patch = self.gemini.generate_text(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.0).strip()
        # Cleanup markdown formatting if Gemini included it despite instructions
        if patch.startswith("```"):
            lines = patch.splitlines()
            if lines and lines[0].startswith("```"):
                 lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                 lines = lines[:-1]
            patch = "\n".join(lines).strip()
        return patch

    def _generate_fix_patch(
        self,
        retry_count: int,
        verify_result: dict[str, Any],
        repo_context: str,
        stack_detected: str = "python",
    ) -> str:
        if not self.gemini.enabled:
             raise RuntimeError("Gemini API is not configured. Self-healing requires Gemini.")

        stack_constraint = (
            " Python only. No TypeScript/React/CSS." if stack_detected == "python" else ""
        )
        system_prompt = (
            "You are a defect correction agent. Use the test failure log and repository content to generate a fix patch. "
            f"Return ONLY the unified diff. No explanations.{stack_constraint}"
        )
        user_prompt = (
            f"Retry count: {retry_count}\n"
            f"Verification summary: {verify_result.get('test_summary')}\n"
            f"stdout:\n{verify_result.get('stdout', '')}\n\n"
            f"stderr:\n{verify_result.get('stderr', '')}\n\n"
            f"Current File Content:\n{repo_context}\n\n"
            "Generate a patch to fix the failure."
        )
        patch = self.gemini.generate_text(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.0).strip()
        if patch.startswith("```"):
            lines = patch.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            patch = "\n".join(lines).strip()
        return patch

    def _read_repo_context(self, file_paths: list[str]) -> str:
        context = []
        seen: set[str] = set()
        for rel_path in file_paths:
            path = TARGET_REPO_DIR / rel_path
            if path.exists() and path.is_file() and rel_path not in seen:
                seen.add(rel_path)
                try:
                    content = path.read_text(encoding="utf-8")
                    context.append(f"File: {rel_path}\n```\n{content}\n```\n")
                except Exception:
                    context.append(f"File: {rel_path} (error reading)")
            elif rel_path not in seen:
                seen.add(rel_path)
                context.append(f"File: {rel_path} (not found)")
        if not context and (TARGET_REPO_DIR / "src" / "demo_app" / "feature_flags.py").exists():
            fallback = TARGET_REPO_DIR / "src" / "demo_app" / "feature_flags.py"
            context.append(f"File: src/demo_app/feature_flags.py\n```\n{fallback.read_text(encoding='utf-8')}\n```\n")
        return "\n".join(context)



    def _normalize_evidence_map(self, payload: dict[str, Any] | list[Any]) -> dict[str, Any]:
        if isinstance(payload, list):
            payload = payload[0] if len(payload) > 0 and isinstance(payload[0], dict) else {}
        if not isinstance(payload, dict):
            payload = {}
        summary = payload.get("summary") if isinstance(payload.get("summary"), str) else "Evidence synthesis summary"

        payload_claims_raw = payload.get("claims")
        claims_raw: list[Any] = payload_claims_raw if isinstance(payload_claims_raw, list) else []
        claims: list[dict[str, Any]] = []
        for idx, claim in enumerate(claims_raw, start=1):
            if not isinstance(claim, dict):
                continue
            claim_id = str(claim.get("claim_id") or claim.get("id") or f"C{idx}")
            claim_text = str(claim.get("claim_text") or claim.get("claim") or "")
            sources_raw = claim.get("supporting_sources") if isinstance(claim.get("supporting_sources"), list) else []
            if not sources_raw and isinstance(claim.get("evidence_ref"), str):
                sources_raw = [{"file": claim.get("evidence_ref"), "line_range": [1, 1], "quote": ""}]
            supporting_sources: list[dict[str, Any]] = []
            for src in sources_raw:
                if not isinstance(src, dict):
                    continue
                line_range = src.get("line_range") if isinstance(src.get("line_range"), list) else [1, 1]
                if len(line_range) < 2:
                    line_range = [1, 1]
                supporting_sources.append(
                    {
                        "file": str(src.get("file", "")),
                        "line_range": [int(line_range[0]), int(line_range[1])],
                        "quote": str(src.get("quote", "")),
                    }
                )
            claims.append(
                {
                    "claim_id": claim_id,
                    "claim_text": claim_text,
                    "supporting_sources": supporting_sources,
                    "confidence": _safe_float(claim.get("confidence"), 0.5),
                }
            )

        features_payload_raw = payload.get("top_features")
        features_raw: list[Any] = features_payload_raw if isinstance(features_payload_raw, list) else []
        features: list[dict[str, Any]] = []
        claim_ids = [c.get("claim_id") for c in claims if isinstance(c, dict)]
        for idx, feat in enumerate(features_raw[:3], start=1):
            if not isinstance(feat, dict):
                continue
            linked_raw = feat.get("linked_claim_ids") if isinstance(feat.get("linked_claim_ids"), list) else []
            linked_claim_ids = [str(item) for item in linked_raw] if linked_raw else claim_ids[:2]
            feat_obj: dict[str, Any] = {
                "feature": str(feat.get("feature", f"Candidate feature {idx}")),
                "rationale": str(feat.get("rationale", "Evidence-backed opportunity")),
                "confidence": _safe_float(feat.get("confidence"), 0.5),
                "linked_claim_ids": linked_claim_ids,
            }
            if "okr_alignment_score" in feat:
                feat_obj["okr_alignment_score"] = int(feat.get("okr_alignment_score", 0))
            if "impact_projection" in feat:
                feat_obj["impact_projection"] = str(feat.get("impact_projection", ""))
            if "impact_confidence_interval" in feat:
                feat_obj["impact_confidence_interval"] = str(feat.get("impact_confidence_interval", ""))
            if "rejection_reason" in feat:
                feat_obj["rejection_reason"] = str(feat.get("rejection_reason", ""))
            features.append(feat_obj)

        return {
            "summary": summary,
            "claims": claims,
            "top_features": features[:3],
            "feature_choice": None,
        }

    def _apply_feature_choice(
        self,
        evidence_map: dict[str, Any] | None,
        selected_feature: dict[str, Any],
        top_features: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if evidence_map is None:
            return {}
        linked_claim_ids = selected_feature.get("linked_claim_ids")
        if not isinstance(linked_claim_ids, list) or not linked_claim_ids:
            linked_claim_ids = []
        feature_choice = {
            "feature": selected_feature.get("feature", "Selected feature"),
            "rationale": selected_feature.get("rationale", ""),
            "linked_claim_ids": linked_claim_ids,
        }
        evidence_map["feature_choice"] = feature_choice
        evidence_map["top_features"] = top_features
        return evidence_map

    def _await_feature_selection(self, run_id: str, top_feature_count: int, timeout_s: int = 300) -> int:
        start = time.time()
        while time.time() - start < timeout_s:
            state = self.run_store.load_state(run_id)
            if state.selected_feature_index is not None:
                return max(0, min(state.selected_feature_index, top_feature_count - 1))
            time.sleep(0.5)
        raise TimeoutError("Timed out waiting for feature selection")

    def _build_run_summary(
        self,
        state: RunState,
        verify_result: dict[str, Any] | None,
        evidence_map: dict[str, Any] | None,
        tickets_path: Path,
        files_changed: list[str],
        pr_url: str | None = None,
    ) -> dict[str, Any]:
        duration = "--"
        created_at = state.timestamps.get("created_at")
        completed_at = state.timestamps.get("completed_at")
        if created_at and completed_at:
            delta = completed_at - created_at
            duration = f"{int(delta.total_seconds())}s"

        tickets_payload: dict[str, Any] = {}
        if tickets_path.exists():
            try:
                from packages.common.io import read_json

                tickets_payload = read_json(tickets_path) or {}
            except Exception:
                tickets_payload = {}
        tickets = tickets_payload.get("tickets") if isinstance(tickets_payload.get("tickets"), list) else []
        total_estimate = sum(int(t.get("estimate_hours", 0) or 0) for t in tickets if isinstance(t, dict))

        confidence_score = 0.7
        if evidence_map and isinstance(evidence_map.get("claims"), list):
            confidences = [c.get("confidence", 0.0) for c in evidence_map["claims"] if isinstance(c, dict)]
            if confidences:
                confidence_score = float(sum(confidences)) / len(confidences)

        pass_fail = "pass" if verify_result and verify_result.get("exit_code") == 0 else "fail"
        tests_passed = 1 if pass_fail == "pass" else 0
        tests_failed = 0 if pass_fail == "pass" else 1

        okr_alignment = None
        impact_projection = None
        impact_confidence = None
        if evidence_map and state.selected_feature:
            sm = state.selected_feature
            if "okr_alignment_score" in sm:
                okr_alignment = int(sm.get("okr_alignment_score", 0))
            if "impact_projection" in sm:
                impact_projection = str(sm.get("impact_projection", ""))
            if "impact_confidence_interval" in sm:
                impact_confidence = str(sm.get("impact_confidence_interval", ""))

        return {
            "passFail": pass_fail,
            "retriesUsed": state.retry_count,
            "filesChanged": sorted(set(files_changed)),
            "confidenceScore": confidence_score,
            "totalTickets": len(tickets),
            "totalEstimateHours": total_estimate,
            "testsPassed": tests_passed,
            "testsFailed": tests_failed,
            "testsSkipped": 0,
            "duration": duration,
            "prUrl": pr_url,
            "okrAlignmentScore": okr_alignment,
            "impactProjection": impact_projection,
            "impactConfidenceInterval": impact_confidence or "±15%",
        }


    def _verify(self, run_id: str) -> dict[str, Any]:
        state = self.run_store.load_state(run_id)
        self._transition(state, StageId.VERIFY, "running")
        started = time.perf_counter()
        result = run_verification(TARGET_REPO_DIR)
        latency_ms = int((time.perf_counter() - started) * 1000)

        report = (
            f"# Test Report\n\n"
            f"- Summary: {result['test_summary']}\n"
            f"- Exit Code: {result['exit_code']}\n"
            f"- Duration (ms): {result['duration_ms']}\n\n"
            "## stdout\n"
            f"```\n{result['stdout']}\n```\n\n"
            "## stderr\n"
            f"```\n{result['stderr']}\n```\n"
        )
        write_text(self.run_store.artifacts_dir(run_id) / "test-report.md", report)
        state.outputs_index["test_report"] = "artifacts/test-report.md"
        status = "done" if result["exit_code"] == 0 else "failed"
        self._transition(state, StageId.VERIFY, status, error=None if status == "done" else "verification failed")
        self._event(run_id, StageId.VERIFY.value, "verification", str(result["test_summary"]), latency_ms=latency_ms)
        self.run_store.save_state(state)
        return result

    def _prepare_repository(self, workspace_id: str) -> None:
        workspace = self.workspace_store.get(workspace_id)
        repo_url = (workspace.repo_url or "").strip()
        use_local_scaffold = not repo_url or repo_url == "local://target-repo"
        if repo_url and not use_local_scaffold:
            # If repo_url is provided, we try to clone/pull it
            if (TARGET_REPO_DIR / ".git").exists():
                 # For safety in this demo agent, we don't want to nuke the user's existing work 
                 # if they ran it repeatedly. But to be safe and deterministic we might.
                 # Let's perform a 'git pull' if it matches, otherwise warn or re-clone.
                 # Simplest valid approach: nuke and clone.
                 shutil.rmtree(TARGET_REPO_DIR, ignore_errors=True)
            
            TARGET_REPO_DIR.mkdir(parents=True, exist_ok=True)
            cmd = ["git", "clone", workspace.repo_url, "."]
            if workspace.branch:
                cmd.extend(["-b", workspace.branch])
            
            # Use token if available
            final_repo_url = workspace.repo_url
            if workspace.github_token_encrypted:
                # Simple b64 decode
                try:
                    token = base64.b64decode(workspace.github_token_encrypted.removeprefix("b64:")).decode("utf-8")
                    if "https://" in final_repo_url:
                        final_repo_url = final_repo_url.replace("https://", f"https://oauth2:{token}@")
                except Exception:
                    pass # Fallback to public clone

            cmd = ["git", "clone", final_repo_url, "."]
            if workspace.branch:
                cmd.extend(["-b", workspace.branch])

            subprocess.run(cmd, cwd=TARGET_REPO_DIR, check=True, capture_output=True)
            
        else:
            # Default demo usage: Write deterministic scaffold
            # Reset to clean state so patches apply reliably across runs
            if (TARGET_REPO_DIR / ".git").exists():
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=TARGET_REPO_DIR, capture_output=True, check=False
                )
                subprocess.run(
                    ["git", "clean", "-fd"],
                    cwd=TARGET_REPO_DIR, capture_output=True, check=False
                )
            
            # Ensure dir exists
            TARGET_REPO_DIR.mkdir(parents=True, exist_ok=True)
            (TARGET_REPO_DIR / "src" / "demo_app").mkdir(parents=True, exist_ok=True)
            
            baseline = (
                '"""Feature flags for deterministic verification demo."""\n\n'
                "BOOST_POINTS = 0\n\n\n"
                "def onboarding_score(base_score: int) -> int:\n"
                "    return base_score + BOOST_POINTS\n"
            )
            write_text(TARGET_REPO_DIR / "src" / "demo_app" / "feature_flags.py", baseline)


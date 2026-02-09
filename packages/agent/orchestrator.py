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
            evidence_map = self._synthesize(goal_statement=goal_statement)
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
            prd_text = self._build_prd(state.selected_feature or {}, goal_statement=goal_statement)
            write_text(artifacts_dir / "PRD.md", prd_text)
            state.outputs_index["prd"] = "artifacts/PRD.md"
            self._transition(state, StageId.GENERATE_PRD, "done")

            # GENERATE_TICKETS
            self._transition(state, StageId.GENERATE_TICKETS, "running")
            tickets = self._build_tickets(state.selected_feature or {})
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
            
            initial_patch = self._generate_code_patch(tickets, repo_context)
            write_text(artifacts_dir / "diff.patch", initial_patch)
            state.outputs_index["diff"] = "artifacts/diff.patch"
            
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
                
                correction_patch = self._generate_fix_patch(state.retry_count, verify_result, repo_context)
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

            # EXPORT
            self._transition(state, StageId.EXPORT, "running")
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

    def _synthesize(self, goal_statement: str | None) -> dict[str, Any]:
        if not self.gemini.enabled:
            raise RuntimeError("Gemini API is not configured (GEMINI_API_KEY missing). Synthesis requires AI reasoning.")

        system_prompt = (
            "You are an evidence synthesis agent. Respond with JSON only. "
            "Return keys: summary (string), claims (array), top_features (array of exactly 3 objects). "
            "Each claim should include claim_id, claim_text, supporting_sources (array of {file, line_range, quote}), confidence. "
            "Each top_features item must include: feature, rationale, linked_claim_ids (array), confidence."
        )
        user_prompt = (
            f"Goal statement: {goal_statement or 'Improve onboarding completion'}\n"
            "Generate concise, realistic synthesis output for a startup SaaS onboarding context."
        )
        payload = self.gemini.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        return self._normalize_evidence_map(payload)

    def _build_prd(self, selected_feature: dict[str, Any], goal_statement: str | None) -> str:
        if not self.gemini.enabled:
            raise RuntimeError("Gemini API is not configured. PRD generation requires Gemini.")

        system_prompt = (
            "You are a product requirements writer. Produce markdown only with headings: "
            "Overview, Problem, Solution, Acceptance Criteria, Constraints, Non-goals, Why This Feature, Done Means."
        )
        user_prompt = (
            f"Selected feature JSON: {selected_feature}\n"
            f"Goal statement: {goal_statement or ''}\n"
            "Keep acceptance criteria testable and implementation-scoped to a small deterministic demo."
        )
        text = self.gemini.generate_text(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
        cleaned = text.strip()
        return cleaned if cleaned.startswith("#") else f"# PRD\n\n{cleaned}"

    def _build_tickets(self, selected_feature: dict[str, Any]) -> dict[str, Any]:
        if not self.gemini.enabled:
             raise RuntimeError("Gemini API is not configured. Ticket generation requires Gemini.")

        system_prompt = (
            "Return JSON only. Shape: {\"tickets\": [ ... ]}. "
            "Each ticket object must include id, title, description, acceptance_criteria, files_expected, risk_level, estimate_hours."
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

    def _generate_code_patch(self, tickets: dict[str, Any], repo_context: str) -> str:
        if not self.gemini.enabled:
            raise RuntimeError("Gemini API is not configured. Code generation requires Gemini.")

        system_prompt = (
            "You are a coding agent. Generate a unified diff (git diff) to implement the following tickets. "
            "Use standard `diff --git a/path b/path` format. "
            "Do NOT include markdown formatting like ```diff. Just the raw diff content. "
            "Ensure context lines match exactly."
        )
        user_prompt = (
            f"Tickets: {tickets}\n\n"
            f"Repository Context:\n{repo_context}\n\n"
            "Generate the minimal diff to satisfy the acceptance criteria."
        )
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

    def _generate_fix_patch(self, retry_count: int, verify_result: dict[str, Any], repo_context: str) -> str:
        if not self.gemini.enabled:
             raise RuntimeError("Gemini API is not configured. Self-healing requires Gemini.")

        system_prompt = (
            "You are a defect correction agent. Use the test failure log and repository content to generate a fix patch. "
            "Return ONLY the unified diff. No explanations."
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
        for rel_path in file_paths:
            path = TARGET_REPO_DIR / rel_path
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    context.append(f"File: {rel_path}\n```\n{content}\n```\n")
                except Exception:
                    context.append(f"File: {rel_path} (error reading)")
            else:
                context.append(f"File: {rel_path} (not found)")
        return "\n".join(context)



    def _normalize_evidence_map(self, payload: dict[str, Any]) -> dict[str, Any]:
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
                    "confidence": float(claim.get("confidence", 0.5)),
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
            features.append(
                {
                    "feature": str(feat.get("feature", f"Candidate feature {idx}")),
                    "rationale": str(feat.get("rationale", "Evidence-backed opportunity")),
                    "confidence": float(feat.get("confidence", 0.5)),
                    "linked_claim_ids": linked_claim_ids,
                }
            )

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
        if workspace.repo_url:
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
            # Ensure safe clean state
            if (TARGET_REPO_DIR / ".git").exists():
                 # Dont nuke a git repo for default demo unless explicitly asked?
                 # PRD says "Local or bundled deterministic repository".
                 # We'll just overwrite the files we care about to be safe.
                 pass
            
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


# Product Requirements Document — Growpad

**Version:** 3.1  
**Status:** Production Specification  
**Hackathon:** [Gemini 3 Hackathon](https://gemini3.devpost.com/) (Deadline: Feb 9, 2026 @ 5:00pm PST)

---

## Executive Summary

**Growpad** is a verification-first product execution agent that converts scattered product evidence (interviews, support tickets, usage metrics) into a validated implementation outcome: PRD, tickets, code patch, and passing tests—with bounded self-correction when verification fails.

**One-liner:** Upload product evidence → synthesize feature → generate PRD + tickets → implement patch → verify tests → if fail, self-heal (≤2 retries) → export auditable artifact pack.

**Core differentiator:** Proof over promises. Every run produces evidence map, PRD, tickets, code diff, test report, and execution logs. The system verifies its own output instead of relying on trust.

---

## 1. Hackathon Compliance

### 1.1 Gemini 3 Hackathon Requirements

| Requirement | Growpad Implementation |
|-------------|---------------------------|
| **New application** | Built from scratch during contest period |
| **Gemini 3 API** | All generation, synthesis, and patch logic uses Gemini 3 |
| **Text description (~200 words)** | Documents Gemini 3 features used and their centrality |
| **Public project link** | Deployed app, publicly accessible, no login/paywall |
| **Public code repository** | Required (no AI Studio link) |
| **~3-minute demo video** | Includes success path + intentional failure + self-correction |
| **Original work only** | No reuse as a modified pre-existing project; all core functionality built during hackathon window |
| **Functional fidelity** | Demo behavior must match what video + description claim |
| **English submission materials** | UI supports English; write-up, instructions, and video/subtitles in English |
| **Submission access for judging** | Judges can access app and test without payment barriers through judging period |
| **Stage-1 viability compliance** | Submission includes all required fields, links, and runnable proof assets |

### 1.2 Judging Criteria Alignment

| Criterion | Weight | Growpad Strategy |
|-----------|--------|---------------------|
| **Technical Execution** | 40% | Full stack, real tools, deterministic verification, quality code |
| **Potential Impact** | 20% | Addresses real PM/engineering pain, broad market applicability |
| **Innovation / Wow Factor** | 30% | Evidence→PR with self-healing verification loop |
| **Presentation / Demo** | 10% | Clear problem, effective demo, Gemini integration docs, architecture diagram |

### 1.3 Submission Operations Checklist (Devpost)

- [ ] Final build is publicly accessible and usable without paywall/login blockers.
- [ ] Devpost text explicitly explains Gemini 3 usage and why app fails without Gemini.
- [ ] Public repo link is valid and README includes one-command local run path.
- [ ] Demo video is concise and shows real product behavior (not slides-only).
- [ ] Video sequence covers: problem → product flow → fail→self-heal proof → impact.
- [ ] Submission package is verified only after production readiness checks are complete.

---

## 2. Problem Statement

### 2.1 Target Users

- **Primary:** Founders, Product Managers, and 1–10 engineer teams shipping weekly
- **Secondary:** Engineers reviewing generated implementations
- **Tertiary:** Stakeholders auditing evidence-to-decision traceability

### 2.2 Pain Points

1. **Evidence overload** — Customer interviews, support tickets, and analytics live in disparate tools and formats.
2. **Decision thrash** — "What should we build next?" takes days and meetings; prioritization is manual.
3. **Trust gap** — AI outputs feel un-auditable; engineers don't trust hallucinated specs/code.
4. **Execution friction** — Turning insights into shippable code requires coordination + verification.

### 2.3 Value Proposition

Growpad solves these problems by making proof part of the product:

- **Why?** → Evidence map with citations linking decisions to source snippets
- **What?** → PRD + structured tickets with acceptance criteria
- **Did it work?** → Test results + logs + diff
- **Can we audit it?** → Full run timeline + artifacts

Result: Converts weeks of synthesis + coordination into a verified execution pipeline. Gives founders a repeatable weekly rhythm: Evidence Monday → PR Friday.

---

## 3. Goals and Non-Goals

### 3.1 Goals

1. **End-to-end evidence → verified output** in under 5 minutes for typical runs.
2. **Deterministic verification loop** — run tests, capture outcome, self-heal on failure with ≤2 retries.
3. **Complete artifact export** — every run (success or failure) produces a downloadable artifact pack.
4. **Transparent execution** — live timeline, structured logs, and audit trail for every stage.
5. **Production-ready architecture** — no mocks; real tools, real Gemini 3 API, real test execution.

### 3.3 Production Runtime Policy (Hard Requirement)

The production pipeline must not rely on demo-only logic.

- **No mocks/stubs in runtime path** for agent stages, patching, verification, or artifact generation.
- **No fake success states** (all stage outcomes must come from actual tool/model execution).
- **No placeholder artifacts** presented as completed outputs.
- **Allowed only in tests:** mocks/stubs for unit-test isolation are acceptable in test code only.
- **Sample evidence is allowed** for onboarding/evaluation, but it must execute the same real runtime pipeline.

### 3.2 Non-Goals (Current Release)

- General-purpose coding agent for arbitrary, unlimited repositories.
- Heavy third-party integrations (Jira, Linear, Slack) beyond core workflow.
- Multi-tenant SaaS with org-level isolation and billing (future phase).
- Real-time collaboration on runs (single-user execution model).

---

## 4. Customer Onboarding

### 4.1 Onboarding Flow (First 5 Minutes)

1. **Create workspace** — Team name, repo select
2. **Connect GitHub** — OAuth or token-based authentication
3. **Upload evidence** — Drag/drop or use sample bundle
4. **Set guardrails:**
   - Max retries (default 2)
   - Read-only vs PR mode
   - Forbidden paths (e.g., `/infra`, `/payments`)
5. **Run first workflow** — Guided wizard with sample evidence

### 4.2 Common Onboarding Issues & Solutions

| Issue | Solution |
|--------|----------|
| No tests exist | Generate minimal test scaffold (explicitly marked as generated) + use lint + typecheck as verification substitutes |
| Messy evidence | Show "evidence quality meter" + prompt for 2 missing fields |
| Repo permissions | Fallback: generate `diff.patch` + manual apply instructions |
| Ambiguous scope | Require user pick from Top 3 candidate features (reduces iteration) |

---

## 5. Core Workflow (State Machine)

### 5.1 Stage Sequence

| Stage | ID | Description | Input | Output |
|-------|-----|-------------|-------|--------|
| 0 | `INTAKE` | Validate evidence, detect stack, create run_id | Evidence bundle | State file + validation result |
| 1 | `SYNTHESIZE` | Cluster evidence, rank themes, generate top 3 candidate features | Evidence | Top 3 features + rationale |
| 2 | `SELECT_FEATURE` | User selects feature (or auto-pick in fast mode) | Top 3 features | Selected feature |
| 3 | `GENERATE_PRD` | Produce PRD with acceptance criteria | Selected feature + evidence | `PRD.md` |
| 4 | `GENERATE_TICKETS` | Produce structured tickets with owners and estimates | PRD | `tickets.json` |
| 5 | `IMPLEMENT` | Generate implementation plan, apply diff, create PR | Tickets + repo context | `diff.patch` or PR |
| 6 | `VERIFY` | Run tests/lint/typecheck in CI-like runner | Patch + repo | Test stdout/stderr, exit code |
| 7 | `SELF_HEAL` | On verify fail: generate correction patch | Failure log + diff | New patch |
| 8 | `EXPORT` | Package artifacts for download | All artifacts | `artifacts.zip` |

### 5.2 State Transitions

```
START → INTAKE → SYNTHESIZE → SELECT_FEATURE → GENERATE_PRD → GENERATE_TICKETS → IMPLEMENT → VERIFY
                                                                           │
                                           ┌────────────────────────────────┘
                                           │ (if fail)
                                           ▼
                                     SELF_HEAL (retry ≤2)
                                           │
                                           ├──► VERIFY (re-run)
                                           │         │
                                           │         └──► (pass) → EXPORT
                                           │
                                           └──► (retries exhausted) → EXPORT (with failure report)
```

### 5.3 Retry Policy (Hard Rule)

- **Max retries:** 2
- **Trigger:** Verify stage returns non-zero exit code
- **Action:** Auditor step (Gemini 3) analyzes failure log + current diff → produces minimal correction patch
- **Visibility:** Each retry logged with cause, patch, and verification result
- **Enforcement:** Retry cap enforced in code and config; not prompt-dependent

---

## 6. Functional Requirements

### 6.1 Input Handling

#### FR-1.1 Evidence Bundle Structure

**Required paths:**

| Path | Format | Required | Description |
|------|--------|----------|-------------|
| `evidence/interviews/*.md` | Markdown | Yes (≥1) | User/customer interview notes |
| `evidence/support_tickets.csv` | CSV | Yes | Support ticket log |
| `evidence/usage_metrics.csv` | CSV or JSON | Yes | Key metrics (current vs target) |
| `evidence/competitors.md` | Markdown | No | Competitive context |

**Optional paths:**

| Path | Format | Description |
|------|--------|-------------|
| `evidence/nps_comments.csv` | CSV | NPS/customer feedback comments |
| `evidence/changelog.md` | Markdown | Recent product changelog |

**Support tickets CSV schema:**

- `ticket_id` (string)
- `created_at` (ISO date or string)
- `summary` (string)
- `severity` (string)
- `freq_estimate` (optional, number or string)

**Usage metrics schema:**

- `metric` (string)
- `current_value` (number or string)
- `target_value` (number or string)
- `notes` (optional string)

#### FR-1.2 Evidence Validation

- **On upload:** Validate presence of required files and basic schema conformance.
- **On parse error:** Return specific error (file, line, field) with actionable message.
- **Reject:** Invalid encoding, missing required columns, or empty required files.
- **Evidence quality meter:** Visual indicator showing completeness and quality of uploaded bundle.

#### FR-1.3 Target Repository & Workspace

- **Option A (default):** Local or bundled deterministic repository (e.g. `target-repo`).
- **Option B:** GitHub repo URL + branch; requires OAuth or `GITHUB_TOKEN` with repo scope.
- **Workspace configuration:** Team name, repo selection
- **Guardrails:**
  - Max retries (default 2)
  - Read-only vs PR mode
  - Forbidden paths (e.g., `/infra`, `/payments`)
- **Goal statement:** Optional user-provided objective (e.g., "Improve onboarding completion")

### 6.2 Stage Logic

#### FR-2.1 Intake & Sanity Checks

1. Parse and validate each evidence file per schema.
2. Validate repository is reachable and accessible.
3. Detect tech stack (Node/Python/etc.) from repository.
4. Create `run_id` and initialize `state.json`.
5. On failure: halt run, emit validation error, export partial artifacts if any.

#### FR-2.2 Synthesize & Cluster Evidence

1. **Gemini 3 call:** Send evidence (interviews, tickets, metrics, competitors, NPS, changelog) with structured prompt.
2. **Output:** Top 3 candidate features + rationale, evidence map with claims linked to source snippets.
3. **Logic:** Cluster evidence into themes (pain points, requests); rank by frequency, severity, revenue/retention adjacency, effort estimate.
4. **Evidence map:** For each claim, produce `{ claim_id, claim_text, supporting_sources[], confidence }`.

#### FR-2.3 Select Feature

1. **Default behavior:** Auto-pick highest-ranked feature in "fast mode."
2. **Interactive mode:** Present Top 3 features with rationales; user selects one.
3. **Output:** Selected feature object with `feature`, `rationale`, `linked_claim_ids[]`.

#### FR-2.4 Generate PRD

1. **Gemini 3 call:** Selected feature + evidence + evidence-map.
2. **Output:** `PRD.md` with sections: Overview, Problem, Solution, Acceptance Criteria, Constraints, Non-goals.
3. **Acceptance criteria:** Must be testable (map to unit test or deterministic check).
4. **Explicit "done means" checklist:** Testable definitions of completion.

#### FR-2.5 Generate Tickets

1. **Gemini 3 call:** PRD + feature.
2. **Output:** `tickets.json` conforming to schema (see §6.4).
3. **Logic:** Each ticket maps to `files_expected`; `acceptance_criteria` derived from PRD.
4. **Include:** Owners (placeholder), estimated time, risk level.

#### FR-2.6 Implement Patch

1. **Gemini 3 call:** Tickets + target repo file contents (relevant files only).
2. **Implementation plan:** Identify files likely to change; generate implementation steps; create branch name + commit plan.
3. **Output:** Unified diff format.
4. **Logic:**
   - Apply patch to working copy; if Git PR mode, create branch and open PR.
   - Ensure formatting/lint steps if configured.
5. **Tool:** Patch applier writes changes; no arbitrary shell from user input.

#### FR-2.7 Verify

1. **Tool:** Execute test command (e.g. `pytest`, `npm test`, lint, typecheck) in isolated environment.
2. **Capture:** stdout, stderr, exit code, test summary (passing/failing tests).
3. **Output:** `test-report.md` with raw output + summary (PASS/FAIL).
4. **Logic:** Exit code 0 → PASS; non-zero → FAIL → trigger self-heal if retries remain.
5. **Fallback for no tests:** Use lint + typecheck + generated minimal test scaffold as verification substitutes.

#### FR-2.8 Self-Heal

1. **Trigger:** Verify fails and `retry_count < 2`.
2. **Gemini 3 call (Auditor):** Failure log + current diff + test output + constraints.
3. **Output:** Correction patch (minimal change to fix failure).
4. **Action:** Apply correction patch; increment retry_count; re-run Verify.
5. **Log:** Record retry index, root cause, patch summary.
6. **Stop condition:** After 2 retries, if still failing, produce "handoff pack" for engineer.

#### FR-2.9 Export Artifact Pack

1. **Collect:** All artifacts from run.
2. **Validate:** Schema conformance for JSON artifacts.
3. **Package:** Zip into `artifacts.zip`.
4. **Storage:** Persist in `runs/<run_id>/artifacts/`.
5. **Output:** Shareable folder or signed download link.

### 6.3 Output Artifacts

**Required per run** (`runs/<run_id>/artifacts/`):

| Artifact | Format | Producer |
|----------|--------|----------|
| `PRD.md` | Markdown | Generate PRD stage |
| `tickets.json` | JSON | Generate Tickets stage |
| `evidence-map.json` | JSON | Synthesize stage |
| `diff.patch` | Text | Implement stage (or PR URL marker) |
| `test-report.md` | Markdown | Verify stage |
| `run-log.jsonl` | JSONL | Orchestrator (all stages) |

**Guarantee:** Artifacts exported on both success and failure (terminal states).

**Additional run summary metadata:**

- Pass/fail status
- Retries used
- Files changed
- Confidence scores

### 6.4 Data Schemas

#### Tickets Schema (`tickets.json`)

```json
{
  "epic_title": "string",
  "tickets": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "acceptance_criteria": ["string"],
      "files_expected": ["string"],
      "risk_level": "low" | "med" | "high",
      "estimate_hours": number,
      "owner": "string|null"
    }
  ]
}
```

#### Evidence Map Schema (`evidence-map.json`)

```json
{
  "claims": [
    {
      "claim_id": "string",
      "claim_text": "string",
      "supporting_sources": [
        { "file": "string", "line_range": [number, number], "quote": "string (≤18 words)" }
      ],
      "confidence": number
    }
  ],
  "feature_choice": {
    "feature": "string",
    "rationale": "string",
    "linked_claim_ids": ["string"]
  },
  "top_features": [
    {
      "feature": "string",
      "rationale": "string",
      "linked_claim_ids": ["string"]
    }
  ]
}
```

#### Run Log Schema (`run-log.jsonl`)

Each line is a JSON object:

```json
{
  "timestamp": "ISO8601",
  "stage": "string",
  "component": "string",
  "action": "string",
  "tool_call_id": "string|null",
  "outcome": "string",
  "latency_ms": number,
  "error": "string|null"
}
```

#### Run State Schema (`state.json`)

```json
{
  "run_id": "string",
  "status": "pending" | "running" | "retrying" | "completed" | "failed" | "cancelled",
  "current_stage": "string|null",
  "retry_count": number,
  "stage_history": [
    {
      "stage_id": "string",
      "status": "done" | "failed" | "skipped",
      "started_at": "ISO8601",
      "completed_at": "ISO8601|null",
      "error": "string|null"
    }
  ],
  "timestamps": {
    "created_at": "ISO8601",
    "started_at": "ISO8601|null",
    "completed_at": "ISO8601|null"
  },
  "inputs_hash": "string",
  "outputs_index": {
    "prd": "string|null",
    "tickets": "string|null",
    "evidence_map": "string|null",
    "diff": "string|null",
    "test_report": "string|null"
  },
  "workspace": {
    "team_name": "string",
    "repo_url": "string",
    "branch": "string",
    "guardrails": {
      "max_retries": number,
      "mode": "read_only" | "pr",
      "forbidden_paths": ["string"]
    }
  }
}
```

### 6.5 Optional: Sample Evidence & Quick Start

- **Purpose:** Enable judges and new users to run the pipeline without preparing evidence.
- **Implementation:** "Load sample" button preloads a reference evidence bundle (interviews, tickets, metrics) and optional target repo fixture.
- **Behavior:** Same pipeline as real upload; no mocked stages. Sample data is synthetic but realistic.
- **Deterministic path:** When using bundled sample + deterministic target repo, run produces a predictable fail→fix→pass sequence for consistent demo evaluation.

### 6.6 Tool Specifications

#### Test Runner Tool

- **Input:** Working directory path, test command (e.g. `pytest tests/`), timeout (default 60s).
- **Output:** `{ stdout, stderr, exit_code, duration_ms, test_summary }`.
- **Security:** Allowlisted commands; no arbitrary user input in shell.
- **Environment:** Isolated (venv/container or locked env).
- **Fallback:** If no tests exist, run lint + typecheck.

#### Patch Applier Tool

- **Input:** Diff string, target directory.
- **Output:** `{ applied: boolean, files_modified: string[], error?: string, branch?: string, pr_url?: string }`.
- **Logic:** Parse unified diff; apply hunks; validate no path traversal.
- **Git integration:** Optional branch creation and PR opening via GitHub API.

#### Packager Tool

- **Input:** Artifact directory path.
- **Output:** Path to `artifacts.zip`.
- **Logic:** Zip all files; include checksum in manifest if configured.
- **Share:** Generate shareable link or signed URL for download.

---

## 7. User Interface Requirements

### 7.1 Layout

**Single-page app, three panels:**

1. **Input panel**
   - Evidence upload (drag/drop)
   - Repo connect (OAuth)
   - Guardrails configuration
   - "Load sample" button for quick start
2. **Timeline panel**
   - Stage list with status (pending/running/done/failed/retry)
   - Streaming log lines
   - Retry counter (0/2, 1/2, 2/2)
3. **Artifacts panel**
   - Tabs: PRD | Tickets | Evidence Map | Diff | Test Report | Download Zip
   - "Open PR" button (if GitHub mode)
   - "Copy link to artifacts" button

### 7.2 Stage Status Display

- Each stage shows: icon, label, status badge.
- Statuses: `pending`, `running`, `done`, `failed`, `retry`.
- Retry: explicit label "Retry 1/2" or "Retry 2/2".

### 7.3 Artifact Tabs

- **PRD:** Rendered markdown with syntax highlighting.
- **Tickets:** Structured table (id, title, risk, estimate, owner).
- **Evidence Map:** Claims + feature choice with source links and citations.
- **Diff:** Unified diff viewer with syntax highlighting.
- **Test Report:** Raw output + pass/fail summary + failing test names.
- **Download Zip:** Button to download `artifacts.zip`.

### 7.4 Real-Time Updates

- **Mechanism:** SSE or WebSocket (or short-polling fallback).
- **Events:** Stage transition, log line, artifact ready.
- **Latency target:** <2 seconds from backend event to UI update.

### 7.5 Error Handling UX

- Validation errors: inline, actionable, no page reload.
- Run failure: clear message, link to failure report, next-steps hint.
- Retry cap exceeded: "Retry limit reached. Exported failure report and logs."
- Evidence quality: Visual meter showing completeness and required missing fields.

### 7.6 Small UI Features for Trust

- **"Show evidence citations" toggle:** Links decisions to source snippets
- **"Files changed" list:** Shows affected files + diff preview
- **"Why this feature" one-page summary:** Quick rationale view with confidence scores

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Target |
|--------|--------|
| P95 run completion | <5 minutes |
| P95 test execution | <30 seconds |
| UI event delay | <2 seconds |
| Artifact zip generation | <10 seconds |

### 8.2 Reliability

- Deterministic verification path when using deterministic target repo and tests.
- Idempotent stage handlers where feasible.
- Artifact export guaranteed on terminal state (success/failure).
- No silent failures; all errors logged and reflected in run status.

### 8.3 Security

- **Secrets:** No API keys or tokens in code, logs, or artifacts.
- **GitHub token:** Least-privilege (repo scope only) when used.
- **Tool execution:** Path and command allowlists; no arbitrary shell from user input.
- **Input validation:** File type, size limits, schema validation on upload.
- **Forbidden paths:** Guardrail to prevent modifying sensitive directories (`/infra`, `/payments`).

### 8.4 Observability

- Structured JSON logs with `run_id` correlation.
- `run-log.jsonl` captures every stage transition and tool call.
- Metrics: runs started/completed/failed, retry frequency, stage latency.

---

## 9. API Specification

### 9.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/runs` | Create run; body: multipart evidence bundle + options |
| `POST` | `/workspaces` | Create workspace (team name, repo, guardrails) |
| `GET` | `/workspaces/{id}` | Get workspace configuration |
| `GET` | `/runs/{id}` | Get run status and metadata |
| `GET` | `/runs/{id}/events` | SSE stream of run events |
| `GET` | `/runs/{id}/artifacts` | List artifact paths |
| `GET` | `/runs/{id}/artifacts/{name}` | Download specific artifact |
| `GET` | `/runs/{id}/artifacts/zip` | Download full artifact pack |
| `POST` | `/runs/{id}/cancel` | Cancel in-progress run |
| `POST` | `/auth/github` | OAuth flow for GitHub connection |

### 9.2 Run Status Model

- `pending` — Created, not started.
- `running` — Pipeline in progress.
- `retrying` — In self-heal loop.
- `completed` — All stages done, verify passed.
- `failed` — Terminal failure (including retry cap exceeded).
- `cancelled` — User or system cancelled.

### 9.3 Error Response

```json
{
  "code": "string",
  "message": "string",
  "stage": "string|null",
  "retryable": boolean,
  "details": {}
}
```

---

## 10. Acceptance Criteria

### 10.1 Core Flow

- [ ] **AC-1** User uploads valid evidence bundle and clicks "Run pipeline".
- [ ] **AC-2** UI shows all stages in sequence with correct status transitions.
- [ ] **AC-3** Run completes with all required artifacts in `runs/<id>/artifacts/`.
- [ ] **AC-4** Artifact zip downloads successfully and contains PRD, tickets, evidence-map, diff, test-report, run-log.

### 10.2 Verification Loop

- [ ] **AC-5** When verify fails, self-heal triggers and applies correction patch.
- [ ] **AC-6** Retry count visible in UI; max 2 retries enforced.
- [ ] **AC-7** On verify pass (after retry or first attempt), run status is `completed`.
- [ ] **AC-8** On retry cap exceeded, run status is `failed`; artifact pack still exported with failure report.

### 10.3 Quality

- [ ] **AC-9** PRD acceptance criteria map to testable outcomes (unit test or deterministic check).
- [ ] **AC-10** Evidence map links decisions to source snippets with confidence.
- [ ] **AC-11** No mocks or stubs in production code paths; all tools are real implementations.
- [ ] **AC-12** Evidence quality meter shows completeness and guides users to fix missing fields.
- [ ] **AC-24** All stage status values are derived from real execution outcomes (no simulated stage completion).
- [ ] **AC-25** Artifact files are generated from actual run outputs, not static templates.

### 10.4 Onboarding & Workspace

- [ ] **AC-13** Workspace creation flow completes within 5 minutes.
- [ ] **AC-14** GitHub OAuth connection succeeds with correct permissions.
- [ ] **AC-15** Guardrails (max retries, forbidden paths, mode) are configurable and enforced.
- [ ] **AC-16** Sample evidence bundle loads and runs the full pipeline successfully.

### 10.5 Hackathon Submission

- [ ] **AC-17** Public demo link, no login/paywall.
- [ ] **AC-18** Public code repository with clear README and run instructions.
- [ ] **AC-19** ~3-minute demo video: success path + intentional failure + self-correction.
- [ ] **AC-20** ~200-word Gemini integration description in Devpost submission.
- [ ] **AC-21** Submission is in English (or includes English subtitles/translations).
- [ ] **AC-22** App behavior demonstrated in video matches real executable app behavior.
- [ ] **AC-23** Stage-1 viability: all required submission fields and links are complete and valid.

---

## 11. Production Delivery Plan

### 11.1 Product Completion Priorities

1. **End-to-end correctness first**
   - Ship deterministic evidence → PRD → tickets → patch → verify → export workflow.
   - Enforce retry cap and failure handling in code, not in prompts.
2. **Production reliability and safety**
   - No mocks in primary workflow.
   - Strong validation, guardrails, and structured observability for all stages.
3. **Auditability as a core feature**
   - Every run must emit complete artifact pack and full execution trail.
4. **Submission readiness after product readiness**
   - Hackathon/demo packaging happens only after the system is stable and reproducible.

### 11.2 Milestone-Based Implementation Plan

**Milestone 1 — Foundations**

- Finalize architecture, schemas, and deterministic target repo fixture.
- Implement intake, synthesis, feature selection, PRD, and tickets stages.

**Milestone 2 — Execution Loop**

- Implement patch generation/application, verify stage, and retry manager (max=2 hard cap).
- Add run timeline events and `run-log.jsonl` end-to-end logging.

**Milestone 3 — Artifact Integrity**

- Ensure artifact contracts are always produced (success and failure states).
- Validate artifact schemas and zip packaging.

**Milestone 4 — UX and Operational Readiness**

- Complete run timeline + artifact review UX.
- Add operational controls, deployment validation, rollback confidence.

**Milestone 5 — External Submission Packaging**

- After production readiness, prepare demo video and Devpost materials.
- Validate public links and submission metadata as final packaging step.

---

## 12. Gemini 3 Integration Details

### 12.1 Usage Points

| Stage | Gemini 3 Role | Input | Output |
|-------|---------------|-------|--------|
| Synthesize | Feature selection + evidence clustering | Evidence bundle (interviews, tickets, metrics, NPS, changelog) | Top 3 features + evidence-map |
| Select Feature (optional) | Feature ranking validation (if user override) | Top 3 features | Selected feature |
| Generate PRD | PRD authoring | Feature + evidence | `PRD.md` |
| Generate Tickets | Ticket breakdown | PRD | `tickets.json` |
| Implement | Code generation | Tickets + repo context | Unified diff |
| Verify (Auditor) | Failure analysis and fix | Failure log + diff | Correction patch |

### 12.2 Capabilities Leveraged

- **Multimodal / reasoning:** Evidence synthesis across interviews, CSV, and structured data.
- **Structured output:** JSON parsing for tickets, evidence-map, and feature rankings.
- **Tool use:** Orchestrator can use Gemini 3 function calling for tool dispatch (if applicable).
- **Low latency:** Optimize for sub-5-minute runs via model selection and prompt efficiency.

### 12.3 Devpost Write-Up (Draft)

> Growpad uses the Gemini 3 API as its core intelligence layer across six stages: (1) Synthesize—Gemini analyzes interviews, support tickets, metrics, NPS, and changelog to cluster themes and select the highest-impact feature; (2) Generate PRD—Gemini drafts the product requirements document with testable acceptance criteria; (3) Generate Tickets—Gemini breaks down the PRD into structured engineering tickets with owners and estimates; (4) Implement—Gemini generates code patches from tickets and repository context; (5) Verify—Gemini runs tests/lint/typecheck and analyzes outputs; (6) Auditor (Self-Heal)—on test failure, Gemini analyzes the failure log and diff to produce a minimal correction patch. Gemini 3 is central to the product: without it, the system cannot perform evidence synthesis, PRD authoring, or self-correction. All generation is driven by Gemini 3; no other LLM is used. The verification loop (run tests, fail, correct, re-run) is what makes Growpad trustworthy—and Gemini 3 powers the entire chain from evidence to final patch.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|------|-------------|
| Flaky tests | Deterministic tests only; isolated env; no network/time in tests |
| Gemini API instability | Retries with backoff; graceful degradation message |
| Tool misuse / security | Allowlists, path validation, no arbitrary shell, forbidden paths guardrail |
| Long-run timeouts | Per-stage timeout; graceful fail with artifact export |
| State drift | Checkpoint state after each stage; replayable from logs |
| No tests in repo | Generate minimal test scaffold + fallback to lint/typecheck |
| Messy evidence | Evidence quality meter + inline validation errors + prompts for missing fields |

---

## 14. References

- [Gemini 3 Hackathon](https://gemini3.devpost.com/)
- [Hackathon Rules](https://gemini3.devpost.com/rules)
- [Architecture](docs/architecture.md)
- [User Flow](docs/user-flow.md)
- [Deployment Runbook](docs/deployment-runbook.md)
- [Governance & Quality](docs/governance-quality.md)

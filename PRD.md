# Product Requirements Document — Growpad

**Version:** 4.0  
**Status:** Full Vision Specification  
**Evolution:** Expanded from hackathon prototype to "Cursor for Product Management" platform

---

## Executive Summary

**Growpad** is a verification-first product operating system that transforms product management from manual synthesis and coordination into an automated, evidence-driven pipeline. It converts scattered product evidence (interviews, support tickets, usage metrics, live data connectors) into validated implementation outcomes: PRD, wireframes, tickets, code patches, and passing tests—with strategic alignment, continuous context discovery, and bounded self-correction.

**One-liner:** Continuous evidence discovery → synthesize features with OKR alignment → generate PRD + wireframes + tickets → stakeholder approval → implement patch → verify tests → if fail, self-heal (≤2 retries) → export complete artifact pack with audit trail.

**Core differentiator:** Proof over promises. Every run produces evidence map, PRD, visual designs, tickets, code diff, test report, execution logs, and permanent audit trail. The system verifies its own output, aligns with strategic goals, and maintains complete traceability from evidence to implementation.

---

## 1. Hackathon Compliance

### 1.1 Gemini 3 Hackathon Requirements

| Requirement                       | Growpad Implementation                                                                            |
| --------------------------------- | ------------------------------------------------------------------------------------------------- |
| **New application**               | Built from scratch during contest period                                                          |
| **Gemini 3 API**                  | All generation, synthesis, and patch logic uses Gemini 3                                          |
| **Text description (~200 words)** | Documents Gemini 3 features used and their centrality                                             |
| **Public project link**           | Deployed app, publicly accessible, no login/paywall                                               |
| **Public code repository**        | Required (no AI Studio link)                                                                      |
| **~3-minute demo video**          | Includes success path + intentional failure + self-correction                                     |
| **Original work only**            | No reuse as a modified pre-existing project; all core functionality built during hackathon window |
| **Functional fidelity**           | Demo behavior must match what video + description claim                                           |
| **English submission materials**  | UI supports English; write-up, instructions, and video/subtitles in English                       |
| **Submission access for judging** | Judges can access app and test without payment barriers through judging period                    |
| **Stage-1 viability compliance**  | Submission includes all required fields, links, and runnable proof assets                         |

### 1.2 Judging Criteria Alignment

| Criterion                   | Weight | Growpad Strategy                                                             |
| --------------------------- | ------ | ---------------------------------------------------------------------------- |
| **Technical Execution**     | 40%    | Full stack, real tools, deterministic verification, quality code             |
| **Potential Impact**        | 20%    | Addresses real PM/engineering pain, broad market applicability               |
| **Innovation / Wow Factor** | 30%    | Evidence→PR with self-healing verification loop                              |
| **Presentation / Demo**     | 10%    | Clear problem, effective demo, Gemini integration docs, architecture diagram |

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
- Multi-tenant SaaS with org-level isolation and billing (future phase).

### 3.4 Strategic Context & Alignment

To realize the full vision of "Cursor for Product Management," Growpad must understand not just what users want, but what the company should build to achieve its strategic objectives.

#### 3.4.1 OKR Guardrails

**Input:** Company OKRs (e.g., "Increase Retention by 10%", "Reduce Support Volume by 20%").

**Logic:** When synthesizing features, score them against active OKRs and strategic priorities.

**Output:**

- Feature alignment score (0-100) per OKR
- Rejection reason when misaligned: "This feature is popular but aligns with 'Growth' while our current quarter focus is 'Retention'."
- Prioritization boost for features that advance multiple OKRs

#### 3.4.2 North Star Metrics

**Input:** Company North Star metric definition (e.g., "Weekly Active Users", "Time to Value").

**Logic:** All feature recommendations include projected impact on North Star metric.

**Output:** "Implementing this feature is projected to increase Weekly Active Users by ~5% based on similar historical features."

#### 3.4.3 Impact Simulation

**Action:** Based on usage data, support ticket patterns, and historical feature launches, predict quantitative impact.

**Output:**

- "Implementing this is projected to reduce support volume by ~15 tickets/week."
- "This feature addresses 23% of current churn reasons based on exit survey analysis."
- Confidence intervals for impact predictions

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

| Issue            | Solution                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| No tests exist   | Generate minimal test scaffold (explicitly marked as generated) + use lint + typecheck as verification substitutes |
| Messy evidence   | Show "evidence quality meter" + prompt for 2 missing fields                                                        |
| Repo permissions | Fallback: generate `diff.patch` + manual apply instructions                                                        |
| Ambiguous scope  | Require user pick from Top 3 candidate features (reduces iteration)                                                |

---

## 5. Core Workflow (State Machine)

### 5.1 Stage Sequence

| Stage | ID                  | Description                                                      | Input                                  | Output                                      |
| ----- | ------------------- | ---------------------------------------------------------------- | -------------------------------------- | ------------------------------------------- |
| 0     | `INTAKE`            | Validate evidence, detect stack, create run_id                   | Evidence bundle                        | State file + validation result              |
| 1     | `SYNTHESIZE`        | Cluster evidence, rank themes, generate top 3 candidate features | Evidence                               | Top 3 features + rationale                  |
| 2     | `SELECT_FEATURE`    | User selects feature (or auto-pick in fast mode)                 | Top 3 features                         | Selected feature                            |
| 3     | `GENERATE_PRD`      | Produce PRD with acceptance criteria                             | Selected feature + evidence            | `PRD.md`                                    |
| 3.5   | `GENERATE_DESIGN`   | Generate UI wireframes and user flow diagrams                    | PRD + Design System tokens (optional)  | Wireframes (HTML/PNG) + User Flow (Mermaid) |
| 3.6   | `AWAITING_APPROVAL` | (Optional) Stakeholder review of PRD + design                    | PRD + Wireframes                       | Approval/rejection + comments               |
| 4     | `GENERATE_TICKETS`  | Produce structured tickets with owners and estimates             | PRD + Design artifacts (post-approval) | `tickets.json`                              |
| 5     | `IMPLEMENT`         | Generate implementation plan, apply diff, create PR              | Tickets + repo context                 | `diff.patch` or PR                          |
| 6     | `VERIFY`            | Run tests/lint/typecheck in CI-like runner                       | Patch + repo                           | Test stdout/stderr, exit code               |
| 7     | `SELF_HEAL`         | On verify fail: generate correction patch                        | Failure log + diff                     | New patch                                   |
| 8     | `EXPORT`            | Package artifacts for download                                   | All artifacts                          | `artifacts.zip`                             |

### 5.2 State Transitions

```
START → INTAKE → SYNTHESIZE → SELECT_FEATURE → GENERATE_PRD → GENERATE_DESIGN
                                                                     │
                                        ┌─────────────────────────────┴─────────────────────────────┐
                                        │ (optional: approval workflow enabled)                    │
                                        ▼                                                           │
                               AWAITING_APPROVAL ◄──► (changes_requested) → AI resolves → re-submit │
                                        │                                                           │
                                        │ (approved)                                                │
                                        └─────────────────────────────┬─────────────────────────────┘
                                                                     │
                                                                     ▼
                                          GENERATE_TICKETS → IMPLEMENT → VERIFY
                                                                           │
                                           ┌───────────────────────────────┘
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

| Path                           | Format      | Required | Description                     |
| ------------------------------ | ----------- | -------- | ------------------------------- |
| `evidence/interviews/*.md`     | Markdown    | Yes (≥1) | User/customer interview notes   |
| `evidence/support_tickets.csv` | CSV         | Yes      | Support ticket log              |
| `evidence/usage_metrics.csv`   | CSV or JSON | Yes      | Key metrics (current vs target) |
| `evidence/competitors.md`      | Markdown    | No       | Competitive context             |

**Optional paths:**

| Path                        | Format   | Description                    |
| --------------------------- | -------- | ------------------------------ |
| `evidence/nps_comments.csv` | CSV      | NPS/customer feedback comments |
| `evidence/changelog.md`     | Markdown | Recent product changelog       |

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

1. **Gemini 3 call:** Selected feature + evidence + evidence-map + OKR context (if configured).
2. **Output:** `PRD.md` with sections: Overview, Problem, Solution, Acceptance Criteria, Constraints, Non-goals, Strategic Alignment (OKR scores, North Star impact projection).
3. **Acceptance criteria:** Must be testable (map to unit test or deterministic check).
4. **Explicit "done means" checklist:** Testable definitions of completion.
5. **Strategic scoring:** Include OKR alignment scores and impact simulation results in PRD.

#### FR-2.5 Generate Design Artifacts

1. **UI Wireframe Generation:**
   - **Input:** PRD + Design System tokens (optional, e.g., color palette, typography, component library).
   - **Action:** Agent generates low-fidelity wireframes or interactive HTML prototypes (via Vercel v0 API or similar).
   - **Output:** Embedded UI mocks in the PRD or separate `wireframes.html` / `wireframes.png` files.
   - **Rationale:** Engineers need visual context, not just text requirements.

2. **User Flow Diagrams:**
   - **Action:** Generate Mermaid.js or React Flow charts visualizing the user journey.
   - **Include:** Happy Path + Edge Cases + Error States.
   - **Output:** `user-flow.mmd` (Mermaid) or `user-flow.json` (React Flow).
   - **Rationale:** Visual flow diagrams clarify interaction patterns and edge case handling.

3. **Design System Integration:**
   - **Logic:** If design tokens provided, wireframes respect brand guidelines.
   - **Fallback:** Generic but professional wireframes if no design system provided.

#### FR-2.6 Generate Tickets

1. **Gemini 3 call:** PRD + feature.
2. **Output:** `tickets.json` conforming to schema (see §6.4).
3. **Logic:** Each ticket maps to `files_expected`; `acceptance_criteria` derived from PRD.
4. **Include:** Owners (placeholder), estimated time, risk level.

#### FR-2.7 Implement Patch

1. **Gemini 3 call:** Tickets + target repo file contents (relevant files only).
2. **Implementation plan:** Identify files likely to change; generate implementation steps; create branch name + commit plan.
3. **Output:** Unified diff format.
4. **Logic:**
   - Apply patch to working copy; if Git PR mode, create branch and open PR.
   - Ensure formatting/lint steps if configured.
5. **Tool:** Patch applier writes changes; no arbitrary shell from user input.

#### FR-2.8 Verify

1. **Tool:** Execute test command (e.g. `pytest`, `npm test`, lint, typecheck) in isolated environment.
2. **Capture:** stdout, stderr, exit code, test summary (passing/failing tests).
3. **Output:** `test-report.md` with raw output + summary (PASS/FAIL).
4. **Logic:** Exit code 0 → PASS; non-zero → FAIL → trigger self-heal if retries remain.
5. **Fallback for no tests:** Use lint + typecheck + generated minimal test scaffold as verification substitutes.

#### FR-2.9 Self-Heal

1. **Trigger:** Verify fails and `retry_count < 2`.
2. **Gemini 3 call (Auditor):** Failure log + current diff + test output + constraints.
3. **Output:** Correction patch (minimal change to fix failure).
4. **Action:** Apply correction patch; increment retry_count; re-run Verify.
5. **Log:** Record retry index, root cause, patch summary.
6. **Stop condition:** After 2 retries, if still failing, produce "handoff pack" for engineer.

#### FR-2.10 Export Artifact Pack

1. **Collect:** All artifacts from run.
2. **Validate:** Schema conformance for JSON artifacts.
3. **Package:** Zip into `artifacts.zip`.
4. **Storage:** Persist in `runs/<run_id>/artifacts/`.
5. **Output:** Shareable folder or signed download link.

### 6.3 Output Artifacts

**Required per run** (`runs/<run_id>/artifacts/`):

| Artifact                             | Format   | Producer                           | Purpose                                              |
| ------------------------------------ | -------- | ---------------------------------- | ---------------------------------------------------- |
| `PRD.md`                             | Markdown | Generate PRD stage                 | Product requirements with acceptance criteria        |
| `wireframes.html` / `wireframes.png` | HTML/PNG | Generate Design stage              | Visual UI mocks for engineering reference            |
| `user-flow.mmd`                      | Mermaid  | Generate Design stage              | User journey visualization (Happy Path + Edge Cases) |
| `tickets.json`                       | JSON     | Generate Tickets stage             | Structured engineering tickets                       |
| `evidence-map.json`                  | JSON     | Synthesize stage                   | Claims linked to source evidence                     |
| `diff.patch`                         | Text     | Implement stage (or PR URL marker) | Code changes in unified diff format                  |
| `test-report.md`                     | Markdown | Verify stage                       | Test execution results and summary                   |
| `run-log.jsonl`                      | JSONL    | Orchestrator (all stages)          | Complete execution timeline                          |

**Optional artifacts** (generated when applicable):

| Artifact                 | Format     | Producer                            | Purpose                                    |
| ------------------------ | ---------- | ----------------------------------- | ------------------------------------------ |
| `database-migration.sql` | SQL/Prisma | Implement stage (if schema changes) | Database schema changes                    |
| `go-to-market.md`        | Markdown   | Generate PRD stage (optional)       | Marketing announcement draft               |
| `analytics-spec.json`    | JSON       | Generate PRD stage (optional)       | Event tracking plan for feature            |
| `.cursorrules`           | Text       | Export stage (optional)             | Context file for Cursor agent              |
| `.windsurfrules`         | Text       | Export stage (optional)             | Context file for Windsurf agent            |
| `audit-trail.json`       | JSON       | Orchestrator                        | Permanent "Why did we build this?" history |

**Guarantee:** Artifacts exported on both success and failure (terminal states).

**Additional run summary metadata:**

- Pass/fail status
- Retries used
- Files changed
- Confidence scores
- OKR alignment scores
- Impact projections

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
  "status": "pending" | "running" | "awaiting_approval" | "retrying" | "completed" | "failed" | "cancelled",
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
    "wireframes": "string|null",
    "user_flow": "string|null",
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

### 6.6 Continuous Context Engine

The system should be "always on," not just when evidence is uploaded. Continuous discovery enables proactive feature identification.

#### FR-6.6.1 Live Data Connectors

**Integrations:** Native APIs for:

- **Gong** (sales calls) — Extract feature requests and pain points from call transcripts
- **Intercom** (support) — Monitor support tickets and customer conversations
- **Linear/Jira** (backlog) — Track existing backlog items and their context
- **PostHog/Mixpanel** (usage data) — Analyze feature adoption and drop-off patterns
- **Slack** (internal discussions) — Capture product discussions and decisions

**Action:** "Nightly Synthesis" — The AI scans yesterday's data and updates the "Evidence Map" automatically.

**Trigger:** Alert the PM: "3 customers mentioned 'Dark Mode' yesterday. Confidence score for this feature has risen to 85%."

**Output:** Updated evidence map with new sources, revised confidence scores, and feature priority adjustments.

#### FR-6.6.2 Competitor Monitor

**Action:** Agent periodically crawls competitor changelogs, documentation, and public announcements.

**Frequency:** Weekly or configurable (e.g., daily for critical competitors).

**Output:** "Competitive Gap Analysis" section in the Feature Selection stage.

**Logic:** Identify features competitors have launched that are missing from current product; flag as potential opportunities or risks.

#### FR-6.6.3 Evidence Map Auto-Update

**Logic:** When new evidence arrives via connectors, automatically:

1. Cluster new evidence with existing claims
2. Update confidence scores based on frequency and recency
3. Re-rank feature candidates if significant new evidence emerges
4. Notify PM of high-confidence feature opportunities

### 6.7 Advanced Agent Handoff Protocol

Growpad should serve as the "brain" for other coding agents, not just generate patches internally.

#### FR-6.7.1 Context File Generation

**Action:** Generate `.cursorrules` or `.windsurfrules` files specifically formatted for Cursor or Windsurf agents.

**Content includes:**

- Tech stack rules and conventions
- Specific feature requirements from PRD
- Relevant code snippets from repo analysis
- Design constraints and acceptance criteria
- Testing requirements

**Output:** Agent-ready context files that enable external agents to implement features with full context.

**Rationale:** Enables "your favorite coding agent" workflow mentioned in the vision.

#### FR-6.7.2 Bi-Directional Sync

**Logic:** If the engineer changes implementation details in code/PR, detect this via GitHub Webhook.

**Action:** Compare implemented code against PRD requirements.

**Output:** Alert: "The code implementation deviated from the PRD. Update PRD to match reality?"

**Workflow:**

1. Detect PR merge or code changes via webhook
2. Analyze diff against original PRD
3. Flag significant deviations (not just stylistic differences)
4. Offer to update PRD to reflect actual implementation
5. Maintain audit trail of PRD → Code → PRD updates

**Rationale:** Keeps PRD as source of truth, even when implementation evolves.

### 6.8 Tool Specifications

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

**Multi-view application with main workspace:**

1. **Input panel**
   - Evidence upload (drag/drop)
   - Repo connect (OAuth)
   - Guardrails configuration
   - OKR configuration (strategic context)
   - Integration management (Gong, Intercom, Linear, etc.)
   - "Load sample" button for quick start
2. **Timeline panel**
   - Stage list with status (pending/running/done/failed/retry/awaiting_approval)
   - Streaming log lines
   - Retry counter (0/2, 1/2, 2/2)
   - Approval status indicators
3. **Artifacts panel**
   - Tabs: PRD | Wireframes | User Flow | Tickets | Evidence Map | Diff | Test Report | Audit Trail | Download Zip
   - "Open PR" button (if GitHub mode)
   - "Copy link to artifacts" button
   - "Generate .cursorrules" button (agent handoff)
4. **Collaboration panel** (when approval workflow active)
   - Comments thread
   - Approval status per stakeholder
   - "Request Changes" / "Approve" buttons

### 7.2 Stage Status Display

- Each stage shows: icon, label, status badge.
- Statuses: `pending`, `running`, `done`, `failed`, `retry`.
- Retry: explicit label "Retry 1/2" or "Retry 2/2".

### 7.3 Artifact Tabs

- **PRD:** Rendered markdown with syntax highlighting, OKR alignment scores, impact projections.
- **Wireframes:** Interactive HTML wireframes or PNG images with design system tokens applied.
- **User Flow:** Interactive Mermaid diagram showing happy path and edge cases.
- **Tickets:** Structured table (id, title, risk, estimate, owner) with links to Linear/Jira.
- **Evidence Map:** Claims + feature choice with source links and citations, live connector data highlighted.
- **Diff:** Unified diff viewer with syntax highlighting.
- **Test Report:** Raw output + pass/fail summary + failing test names.
- **Audit Trail:** Queryable history with search by feature, date, evidence source, decision rationale.
- **Download Zip:** Button to download `artifacts.zip` including all artifacts.

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
- **"Why this feature" one-page summary:** Quick rationale view with confidence scores, OKR alignment, impact projections
- **"Live connector status" indicator:** Shows last sync time and new evidence count
- **"Competitive gap" badge:** Highlights features competitors have launched
- **"Impact simulation" expandable:** Shows quantitative predictions with confidence intervals
- **"Audit trail search" bar:** Quick search for historical decisions and rationale

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric                  | Target      |
| ----------------------- | ----------- |
| P95 run completion      | <5 minutes  |
| P95 test execution      | <30 seconds |
| UI event delay          | <2 seconds  |
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

## 9. External Integrations & Data Connectors

### 9.1 Integration Architecture

Growpad connects to external tools to enable continuous context discovery and seamless workflow integration.

### 9.2 Supported Integrations

#### 9.2.1 Gong Integration

**Purpose:** Extract feature requests and pain points from sales call transcripts.

**Authentication:** OAuth 2.0 or API key.

**Data Flow:**

- Fetch call transcripts from last N days (configurable)
- Extract feature requests, pain points, and customer needs
- Add to evidence map with source attribution
- Update feature confidence scores based on frequency

**Configuration:**

- Sync frequency (daily, weekly)
- Date range for call analysis
- Filter criteria (e.g., only calls with specific tags)

#### 9.2.2 Intercom Integration

**Purpose:** Monitor support tickets and customer conversations for product insights.

**Authentication:** OAuth 2.0 or API key.

**Data Flow:**

- Fetch support conversations and tickets
- Extract common issues and feature requests
- Cluster similar requests for pattern detection
- Update evidence map with support-driven insights

**Configuration:**

- Sync frequency
- Ticket status filters (open, closed, resolved)
- Tag-based filtering

#### 9.2.3 Linear/Jira Integration

**Purpose:** Track existing backlog items and their context; sync generated tickets.

**Authentication:** OAuth 2.0 or API token.

**Data Flow (Read):**

- Fetch backlog items and their descriptions
- Extract feature context and requirements
- Identify gaps between backlog and evidence-driven features

**Data Flow (Write):**

- Create tickets in Linear/Jira from `tickets.json`
- Link tickets to PRD and evidence sources
- Update ticket status based on implementation progress

**Configuration:**

- Workspace/project selection
- Sync direction (read-only, write-only, bidirectional)
- Ticket mapping rules

#### 9.2.4 PostHog/Mixpanel Integration

**Purpose:** Analyze feature adoption and usage patterns to validate feature impact.

**Authentication:** API key.

**Data Flow:**

- Fetch usage metrics and event data
- Identify feature adoption rates
- Detect drop-off points in user flows
- Correlate usage patterns with feature requests

**Configuration:**

- Event names to track
- Date range for analysis
- User segment filters

#### 9.2.5 Slack Integration

**Purpose:** Capture product discussions and decisions from internal channels.

**Authentication:** OAuth 2.0 (Slack App).

**Data Flow:**

- Monitor specified channels for product discussions
- Extract feature ideas, decisions, and context
- Add to evidence map with attribution
- Enable notifications for high-confidence features

**Configuration:**

- Channels to monitor
- Keyword filters
- Notification preferences

### 9.3 Integration Management

**UI:** Integration settings page showing:

- Connected integrations with status
- Last sync time and status
- Sync frequency configuration
- Error logs and retry status

**Security:**

- Encrypted storage of API keys/tokens
- Least-privilege OAuth scopes
- Token rotation support

---

## 10. Multi-User Collaboration & Workflows

### 10.1 Stakeholder Approval Workflow

Product management is a team sport. The system must support collaborative decision-making.

#### FR-10.1.1 Approval Gates

**Action:** Before generating code, send PRD + Wireframes to specific users for approval.

**Recipients:** Configurable (e.g., Design Lead, Eng Lead, Product Lead).

**Workflow:**

1. PRD + Design artifacts generated
2. System sends notification to approvers
3. Approvers review and comment
4. AI resolves comments (e.g., Engineer comments "This API is deprecated," AI rewrites Implementation Plan)
5. Once approved, proceed to ticket generation and implementation

**Approval States:**

- `pending` — Awaiting review
- `approved` — Approved by all required approvers
- `changes_requested` — Comments require PRD/design updates
- `rejected` — Feature rejected, workflow stops

#### FR-10.1.2 Comment Resolution

**Action:** AI analyzes comments and automatically updates PRD/design/tickets.

**Logic:**

- Identify actionable feedback (technical constraints, design issues, scope changes)
- Generate updated artifacts incorporating feedback
- Present diff of changes for review
- Re-submit for approval if required

**Example:** Engineer comments "This API is deprecated, use v2 instead." AI updates Implementation Plan section of PRD.

### 10.2 "Why Did We Build This?" Audit Trail

**Purpose:** Maintain permanent, queryable history of decision rationale.

**Action:** Every run produces an audit trail entry including:

- Evidence sources that led to feature selection
- Confidence scores and rationale
- OKR alignment reasoning
- Stakeholder comments and approvals
- Implementation decisions and deviations

**Storage:** Queryable database with full-text search.

**Use Case:** Six months later, a user asks: "Why is this button blue?" Answer: "Because 40% of users in interview set B couldn't find it in gray. See evidence-map.json, claim_id: C-2024-03-15-001."

**Output:** `audit-trail.json` included in artifact pack with complete decision history.

### 10.3 Multi-User Workspace

**Features:**

- Team workspaces with role-based access (Admin, PM, Engineer, Viewer)
- Shared evidence libraries
- Run history visible to team
- Comment threads on PRDs and features

**Roles:**

- **Admin:** Full access, integration management, workspace settings
- **PM:** Create runs, approve features, manage evidence
- **Engineer:** View runs, comment on PRDs, access code artifacts
- **Viewer:** Read-only access to runs and artifacts

---

## 11. API Specification

### 11.1 Endpoints

| Method | Path                               | Description                                                  |
| ------ | ---------------------------------- | ------------------------------------------------------------ |
| `POST` | `/runs`                            | Create run; body: multipart evidence bundle + options        |
| `POST` | `/workspaces`                      | Create workspace (team name, repo, guardrails)               |
| `GET`  | `/workspaces/{id}`                 | Get workspace configuration                                  |
| `PUT`  | `/workspaces/{id}`                 | Update workspace (OKRs, integrations, team members)          |
| `GET`  | `/runs/{id}`                       | Get run status and metadata                                  |
| `GET`  | `/runs/{id}/events`                | SSE stream of run events                                     |
| `GET`  | `/runs/{id}/artifacts`             | List artifact paths                                          |
| `GET`  | `/runs/{id}/artifacts/{name}`      | Download specific artifact                                   |
| `GET`  | `/runs/{id}/artifacts/zip`         | Download full artifact pack                                  |
| `POST` | `/runs/{id}/cancel`                | Cancel in-progress run                                       |
| `POST` | `/runs/{id}/approve`               | Approve PRD/design (stakeholder workflow)                    |
| `POST` | `/runs/{id}/comments`              | Add comment to PRD/design                                    |
| `GET`  | `/runs/{id}/comments`              | Get comments and discussion thread                           |
| `POST` | `/auth/github`                     | OAuth flow for GitHub connection                             |
| `POST` | `/integrations/{provider}/connect` | Connect external integration (Gong, Intercom, etc.)          |
| `GET`  | `/integrations`                    | List connected integrations and status                       |
| `POST` | `/integrations/{provider}/sync`    | Trigger manual sync for integration                          |
| `GET`  | `/audit-trail`                     | Query audit trail (search by feature, date, evidence source) |
| `POST` | `/webhooks/github`                 | GitHub webhook endpoint for bi-directional sync              |

### 11.2 Run Status Model

- `pending` — Created, not started.
- `running` — Pipeline in progress.
- `awaiting_approval` — PRD + design sent to stakeholders; awaiting approval (when approval workflow enabled).
- `retrying` — In self-heal loop.
- `completed` — All stages done, verify passed.
- `failed` — Terminal failure (including retry cap exceeded).
- `cancelled` — User or system cancelled.

### 11.3 Error Response

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

## 12. Acceptance Criteria

### 12.1 Core Flow

- [ ] **AC-1** User uploads valid evidence bundle and clicks "Run pipeline".
- [ ] **AC-2** UI shows all stages in sequence with correct status transitions.
- [ ] **AC-3** Run completes with all required artifacts in `runs/<id>/artifacts/`.
- [ ] **AC-4** Artifact zip downloads successfully and contains PRD, wireframes, user-flow, tickets, evidence-map, diff, test-report, run-log.

### 12.2 Verification Loop

- [ ] **AC-5** When verify fails, self-heal triggers and applies correction patch.
- [ ] **AC-6** Retry count visible in UI; max 2 retries enforced.
- [ ] **AC-7** On verify pass (after retry or first attempt), run status is `completed`.
- [ ] **AC-8** On retry cap exceeded, run status is `failed`; artifact pack still exported with failure report.

### 12.3 Quality

- [ ] **AC-9** PRD acceptance criteria map to testable outcomes (unit test or deterministic check).
- [ ] **AC-10** Evidence map links decisions to source snippets with confidence.
- [ ] **AC-11** No mocks or stubs in production code paths; all tools are real implementations.
- [ ] **AC-12** Evidence quality meter shows completeness and guides users to fix missing fields.
- [ ] **AC-24** All stage status values are derived from real execution outcomes (no simulated stage completion).
- [ ] **AC-25** Artifact files are generated from actual run outputs, not static templates.

### 12.4 Onboarding & Workspace

- [ ] **AC-13** Workspace creation flow completes within 5 minutes.
- [ ] **AC-14** GitHub OAuth connection succeeds with correct permissions.
- [ ] **AC-15** Guardrails (max retries, forbidden paths, mode) are configurable and enforced.
- [ ] **AC-16** Sample evidence bundle loads and runs the full pipeline successfully.

- [ ] **AC-26** OKR guardrails filter and score features during synthesis.
- [ ] **AC-27** PRD includes strategic alignment section with OKR scores and North Star impact projections.
- [ ] **AC-28** Impact simulation provides quantitative predictions (e.g., "reduce support volume by X tickets/week").
- [ ] **AC-29** Design stage generates wireframes (HTML/PNG) and user flow diagrams (Mermaid).
- [ ] **AC-30** Wireframes respect design system tokens when provided.

### 12.6 Continuous Context & Integrations

- [ ] **AC-31** Live data connectors sync evidence from Gong, Intercom, Linear, PostHog, and Slack.
- [ ] **AC-32** Nightly synthesis updates evidence map automatically with new data.
- [ ] **AC-33** Competitor monitor crawls and analyzes competitor changelogs.
- [ ] **AC-34** PM receives alerts when feature confidence scores change significantly.

### 12.7 Agent Handoff & Collaboration

- [ ] **AC-35** System generates `.cursorrules` or `.windsurfrules` files for external agents.
- [ ] **AC-36** Bi-directional sync detects code deviations from PRD via GitHub webhook.
- [ ] **AC-37** Stakeholder approval workflow sends PRD/design to approvers before implementation.
- [ ] **AC-38** AI resolves comments and updates artifacts automatically.
- [ ] **AC-39** Audit trail provides queryable history of "why did we build this?" decisions.

---

## 13. Production Delivery Plan

### 13.1 Product Completion Priorities

1. **End-to-end correctness first**
   - Ship deterministic evidence → PRD → design → tickets → patch → verify → export workflow.
   - Enforce retry cap and failure handling in code, not in prompts.
2. **Strategic alignment integration**
   - OKR guardrails and impact simulation must be accurate and trustworthy.
   - North Star metrics integration enables data-driven prioritization.
3. **Visual design as first-class artifact**
   - Wireframes and user flows are essential for engineering handoff.
   - Design system integration ensures brand consistency.
4. **Continuous context as competitive advantage**
   - Live connectors transform Growpad from "on-demand" to "always-on" system.
   - Competitor monitoring provides proactive feature identification.
5. **Production reliability and safety**
   - No mocks in primary workflow.
   - Strong validation, guardrails, and structured observability for all stages.
6. **Auditability as a core feature**
   - Every run must emit complete artifact pack and full execution trail.
   - Audit trail enables "why did we build this?" queries months later.
7. **Collaboration workflows**
   - Stakeholder approval ensures quality and alignment before implementation.
   - Comment resolution reduces iteration cycles.

### 13.2 Milestone-Based Implementation Plan

**Milestone 1 — Foundations**

- Finalize architecture, schemas, and deterministic target repo fixture.
- Implement intake, synthesis, feature selection, PRD, and tickets stages.

**Milestone 2 — Execution Loop**

- Implement patch generation/application, verify stage, and retry manager (max=2 hard cap).
- Add run timeline events and `run-log.jsonl` end-to-end logging.

**Milestone 3 — Artifact Integrity**

- Ensure artifact contracts are always produced (success and failure states).
- Validate artifact schemas and zip packaging.

**Milestone 4 — Strategic Alignment**

- Implement OKR guardrails and scoring system.
- Add impact simulation based on historical data.
- Integrate North Star metrics tracking.

**Milestone 5 — Visual Design Module**

- Implement wireframe generation (Vercel v0 API or similar).
- Generate user flow diagrams (Mermaid/React Flow).
- Add design system token support.

**Milestone 6 — Continuous Context Engine**

- Build live data connectors (Gong, Intercom, Linear, PostHog, Slack).
- Implement nightly synthesis and auto-update of evidence map.
- Add competitor monitoring and gap analysis.

**Milestone 7 — Agent Handoff & Bi-Directional Sync**

- Generate `.cursorrules` / `.windsurfrules` context files.
- Implement GitHub webhook for code deviation detection.
- Build PRD update workflow from implementation changes.

**Milestone 8 — Collaboration & Workflows**

- Implement stakeholder approval workflow.
- Add comment resolution with AI updates.
- Build audit trail system with queryable history.

**Milestone 9 — UX and Operational Readiness**

- Complete run timeline + artifact review UX with new artifacts.
- Add integration management UI.
- Add operational controls, deployment validation, rollback confidence.

**Milestone 10 — External Submission Packaging** (if applicable)

- After production readiness, prepare demo video and Devpost materials.
- Validate public links and submission metadata as final packaging step.

---

## 14. Gemini 3 Integration Details

### 14.1 Usage Points

| Stage                     | Gemini 3 Role                                 | Input                                                                                | Output                                      |
| ------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------- |
| Synthesize                | Feature selection + evidence clustering       | Evidence bundle (interviews, tickets, metrics, NPS, changelog) + live connector data | Top 3 features + evidence-map               |
| Select Feature (optional) | Feature ranking validation (if user override) | Top 3 features + OKR context                                                         | Selected feature                            |
| Generate PRD              | PRD authoring                                 | Feature + evidence + OKR context                                                     | `PRD.md` with strategic alignment           |
| Generate Design           | UI wireframe + user flow generation           | PRD + Design System tokens                                                           | Wireframes (HTML/PNG) + User Flow (Mermaid) |
| Generate Tickets          | Ticket breakdown                              | PRD + Design artifacts                                                               | `tickets.json`                              |
| Implement                 | Code generation                               | Tickets + repo context                                                               | Unified diff                                |
| Verify (Auditor)          | Failure analysis and fix                      | Failure log + diff                                                                   | Correction patch                            |
| Agent Handoff             | Context file generation                       | PRD + tickets + repo context                                                         | `.cursorrules` / `.windsurfrules`           |

### 14.2 Capabilities Leveraged

- **Multimodal / reasoning:** Evidence synthesis across interviews, CSV, and structured data.
- **Structured output:** JSON parsing for tickets, evidence-map, and feature rankings.
- **Tool use:** Orchestrator can use Gemini 3 function calling for tool dispatch (if applicable).
- **Low latency:** Optimize for sub-5-minute runs via model selection and prompt efficiency.

### 14.3 Devpost Write-Up (Draft)

> Growpad uses the Gemini 3 API as its core intelligence layer across multiple stages: (1) Synthesize—Gemini analyzes interviews, support tickets, metrics, NPS, changelog, and live connector data to cluster themes and select the highest-impact feature; (2) Generate PRD—Gemini drafts the product requirements document with testable acceptance criteria and strategic alignment; (3) Generate Design—Gemini produces UI wireframes and user flow diagrams; (4) Generate Tickets—Gemini breaks down the PRD into structured engineering tickets; (5) Implement—Gemini generates code patches from tickets and repository context; (6) Verify—Gemini runs tests/lint/typecheck and analyzes outputs; (7) Auditor (Self-Heal)—on test failure, Gemini analyzes the failure log and diff to produce a minimal correction patch; (8) Agent Handoff—Gemini generates .cursorrules context files for external coding agents. Gemini 3 is central: without it, the system cannot perform evidence synthesis, PRD authoring, design generation, or self-correction. The verification loop (run tests, fail, correct, re-run) is what makes Growpad trustworthy—and Gemini 3 powers the entire chain from evidence to final patch.

---

## 15. Risks and Mitigations

| Risk                   | Mitigation                                                                     |
| ---------------------- | ------------------------------------------------------------------------------ |
| Flaky tests            | Deterministic tests only; isolated env; no network/time in tests               |
| Gemini API instability | Retries with backoff; graceful degradation message                             |
| Tool misuse / security | Allowlists, path validation, no arbitrary shell, forbidden paths guardrail     |
| Long-run timeouts      | Per-stage timeout; graceful fail with artifact export                          |
| State drift            | Checkpoint state after each stage; replayable from logs                        |
| No tests in repo       | Generate minimal test scaffold + fallback to lint/typecheck                    |
| Messy evidence         | Evidence quality meter + inline validation errors + prompts for missing fields |

---

## 16. Platform Evolution Summary

### 16.1 From Prototype to Product Operating System

This PRD represents the evolution of Growpad from a hackathon prototype into a category-defining "Cursor for Product Management" platform. The key transformations include:

**Expanded Capabilities:**

- **Visual Design:** UI wireframes and user flow diagrams bridge the gap between text PRDs and visual design
- **Strategic Alignment:** OKR guardrails and impact simulation ensure features align with company goals
- **Continuous Context:** Live data connectors and competitor monitoring enable proactive feature discovery
- **Agent Handoff:** Context file generation and bi-directional sync integrate with external coding agents
- **Collaboration:** Stakeholder approval workflows and audit trails support team-based product management

**New Artifacts:**

- Wireframes (HTML/PNG)
- User Flow Diagrams (Mermaid)
- Database Migration Plans (SQL/Prisma)
- Go-To-Market Drafts (Markdown)
- Analytics Specifications (JSON)
- Agent Context Files (.cursorrules / .windsurfrules)
- Audit Trail (JSON)

**New Integrations:**

- Gong (sales calls)
- Intercom (support)
- Linear/Jira (backlog)
- PostHog/Mixpanel (usage data)
- Slack (internal discussions)

**New Workflows:**

- Stakeholder approval gates
- Comment resolution with AI updates
- Bi-directional PRD ↔ Code sync
- Continuous evidence discovery

### 16.2 Implementation Phases

The expanded platform can be built incrementally:

**Phase 1 (Core):** Evidence → PRD → Tickets → Code → Verify (hackathon scope)
**Phase 2 (Strategic):** OKR alignment, impact simulation, North Star metrics
**Phase 3 (Visual):** Wireframes, user flows, design system integration
**Phase 4 (Continuous):** Live connectors, competitor monitoring, auto-updates
**Phase 5 (Collaboration):** Approval workflows, comments, audit trail
**Phase 6 (Handoff):** Agent context files, bi-directional sync

Each phase delivers standalone value while building toward the complete vision.

---

## 17. References

- [Gemini 3 Hackathon](https://gemini3.devpost.com/)
- [Hackathon Rules](https://gemini3.devpost.com/rules)

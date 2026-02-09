# Growpad

A verification-first product execution agent that converts scattered product evidence into a validated implementation outcome: PRD, tickets, code patch, and passing tests—with bounded self-correction when verification fails.

---

## Quick Start (One Command)

```bash
# Prerequisites: Python 3.11+, Node.js 18+, Git
git clone <repo-url> && cd Scec2Ship
python3 -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements.txt
cd apps/web && npm install && cd ../..
make run
```

Then open **http://localhost:3000**. Load sample evidence, create a workspace, and run the pipeline.

---

## What It Is

Growpad is "Cursor for shipping decisions"—except it outputs a PR that passes tests and explains why.

**Core Flow:**

Evidence bundle → synthesize feature → generate PRD + tickets → implement patch → verify tests → if fail, self-heal (≤2 retries) → export auditable artifact pack.

**Who It's For:**

- **Primary:** Founders, Product Managers, and 1–10 engineer teams shipping weekly
- **Secondary:** Engineers reviewing generated implementations
- **Tertiary:** Stakeholders auditing evidence-to-decision traceability

---

## Core Problems Solved

1. **Evidence overload** — Customer interviews, support tickets, and analytics live in disparate tools and formats.
2. **Decision thrash** — "What should we build next?" takes days and meetings; prioritization is manual.
3. **Trust gap** — AI outputs feel un-auditable; engineers don't trust hallucinated specs/code.
4. **Execution friction** — Turning insights into shippable code requires coordination + verification.

**Growpad Solution:**

- **Why?** → Evidence map with citations linking decisions to source snippets
- **What?** → PRD + structured tickets with acceptance criteria
- **Did it work?** → Test results + logs + diff
- **Can we audit it?** → Full run timeline + artifacts

Result: Converts weeks of synthesis + coordination into a verified execution pipeline. Gives founders a repeatable weekly rhythm: Evidence Monday → PR Friday.

---

## What Users Upload

**Evidence Bundle** (zip or uploaded files):

| File Path                      | Format      | Required | Description                                                                                        |
| ------------------------------ | ----------- | -------- | -------------------------------------------------------------------------------------------------- |
| `evidence/interviews/*.md`     | Markdown    | Yes (≥1) | User/customer interview notes                                                                      |
| `evidence/support_tickets.csv` | CSV         | Yes      | Support ticket log with columns: `ticket_id`, `created_at`, `summary`, `severity`, `freq_estimate` |
| `evidence/usage_metrics.csv`   | CSV or JSON | Yes      | Key metrics (current vs target): `metric`, `current_value`, `target_value`, `notes`                |
| `evidence/competitors.md`      | Markdown    | No       | Competitive context                                                                                |

**Optional Evidence Paths:**

| Path                        | Format   | Description                    |
| --------------------------- | -------- | ------------------------------ |
| `evidence/nps_comments.csv` | CSV      | NPS/customer feedback comments |
| `evidence/changelog.md`     | Markdown | Recent product changelog       |

**Target Repository:**

- Local bundled repository (default)
- GitHub repo URL + branch (requires OAuth or `GITHUB_TOKEN` with repo scope)

**Workspace Configuration:**

- Team name, repo selection
- Guardrails: max retries (default 2), read-only vs PR mode, forbidden paths (e.g., `/infra`, `/payments`)
- Goal statement (optional user-provided objective)

---

## What Users Get

**Every run produces a downloadable artifact pack** (`artifacts.zip`) containing:

| Artifact            | Format       | Description                                                                                                     |
| ------------------- | ------------ | --------------------------------------------------------------------------------------------------------------- |
| `PRD.md`            | Markdown     | Product requirements with Overview, Problem, Solution, Acceptance Criteria, Constraints                         |
| `wireframes.html`   | HTML         | UI wireframes for engineering reference                                                                         |
| `user-flow.mmd`     | Mermaid      | User journey visualization                                                                                      |
| `tickets.json`      | JSON         | Structured tickets with id, title, description, acceptance_criteria, files_expected, risk_level, estimate_hours |
| `evidence-map.json` | JSON         | Claims linked to source snippets with confidence and rationale; Top 3 candidate features                        |
| `diff.patch`        | Unified diff | Code changes applied (or PR URL if GitHub mode)                                                                 |
| `test-report.md`    | Markdown     | Test execution output with raw logs + PASS/FAIL summary                                                         |
| `run-log.jsonl`     | JSONL        | Complete execution log with timestamps, stage transitions, tool calls, latency                                  |
| `audit-trail.json`  | JSON         | "Why did we build this?" decision history                                                                       |

**Plus:**

- **Live timeline** in UI showing all 9 stages with status
- **Real-time logs** streaming as stages execute
- **Retry visibility** with cause, patch, and outcome when self-healing occurs
- **Evidence quality meter** showing bundle completeness
- **Feature selection UI** with Top 3 candidates and rationales

---

## Core Workflow (9 Stages)

| Stage | ID                 | Description                                                      | Input                       | Output                                    |
| ----- | ------------------ | ---------------------------------------------------------------- | --------------------------- | ----------------------------------------- |
| 0     | `INTAKE`           | Validate evidence, detect stack, create run_id                   | Evidence bundle             | State file + validation result            |
| 1     | `SYNTHESIZE`       | Cluster evidence, rank themes, generate top 3 candidate features | Evidence                    | Top 3 features + rationale + evidence map |
| 2     | `SELECT_FEATURE`   | User selects feature (or auto-pick in fast mode)                 | Top 3 features              | Selected feature                          |
| 3     | `GENERATE_PRD`     | Produce PRD with acceptance criteria                             | Selected feature + evidence | `PRD.md`                                  |
| 3.5   | `GENERATE_DESIGN`  | Generate wireframes and user flow diagrams                       | PRD + design tokens         | `wireframes.html`, `user-flow.mmd`       |
| 3.6   | `AWAITING_APPROVAL`| (Optional) Stakeholder review of PRD + design                     | PRD + wireframes            | Approval/rejection + comments             |
| 4     | `GENERATE_TICKETS` | Produce structured tickets with owners and estimates             | PRD + design                | `tickets.json`                            |
| 5     | `IMPLEMENT`        | Generate implementation plan, apply diff, create PR              | Tickets + repo context      | `diff.patch` or PR                        |
| 6     | `VERIFY`           | Run tests/lint/typecheck in CI-like runner                       | Patch + repo                | Test stdout/stderr, exit code             |
| 7     | `SELF_HEAL`        | On verify fail: generate correction patch                        | Failure log + diff          | New patch                                 |
| 8     | `EXPORT`           | Package artifacts for download                                   | All artifacts               | `artifacts.zip`                           |

**State Transitions:**

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

---

## Key Features

### Verification-First Architecture

- **Deterministic tests** for predictable fail→fix→pass behavior
- **Real tools** — test runner, patch applier, packager (no mocks)
- **Full audit trail** via `run-log.jsonl` for every stage and tool call
- **Artifact guarantee** — artifacts exported on both success and failure

### Bounded Self-Correction (≤2 Retries)

- **Trigger:** Verify stage returns non-zero exit code
- **Action:** Gemini 3 Auditor analyzes failure log + current diff → produces minimal correction patch
- **Visibility:** Each retry shows cause, patch, and verification result
- **Hard cap:** Max 2 retries enforced in code and config; not prompt-dependent

### Customer Onboarding (First 5 Minutes)

1. Create workspace (team name, repo select)
2. Connect GitHub (OAuth)
3. Upload evidence (drag/drop) or use sample bundle
4. Set guardrails (max retries, scope, forbidden paths)
5. Run first workflow (guided wizard)

**Common Onboarding Solutions:**

- No tests exist → Generate minimal test scaffold (explicitly marked) + use lint + typecheck as verification substitutes
- Messy evidence → Show "evidence quality meter" + prompt for missing fields
- Repo permissions → Fallback: generate `diff.patch` + manual apply instructions
- Ambiguous scope → Require user pick from Top 3 features

### User Experience (3-Panel UI)

| Panel         | Description                                                                                |
| ------------- | ------------------------------------------------------------------------------------------ |
| **Input**     | Evidence upload, GitHub connect, guardrails configuration, OKR config, "Load sample" button |
| **Timeline**  | Stage list with status badges, streaming log lines, retry counter (0/2, 1/2, 2/2)            |
| **Artifacts** | Tabs: PRD, Wireframes, User Flow, Tickets, Evidence Map, Diff, Tests, Audit Trail, Download Zip |

**Trust-Building Features:**

- "Show evidence citations" toggle
- "Files changed" list + diff preview
- "Why this feature" one-page summary

---

## Technology Stack

| Layer   | Technology                                                         |
| ------- | ------------------------------------------------------------------ |
| Web app | Next.js (React + TypeScript) app in `apps/web/`                    |
| API     | FastAPI (Python, `apps/api`)                                       |
| Agent   | Gemini 3 API                                                       |
| Tools   | Python/Node (test runner, patch applier, packager, GitHub adapter) |
| Storage | Local filesystem (initial) → S3/GCS (production)                   |

---

## Repository Layout

```
apps/
  api/               # FastAPI backend application
  web/               # Next.js frontend UI
packages/            # Shared packages (monorepo pattern)
  agent/             # Stage logic and Gemini 3 integration
  common/            # Models, store, paths
  tools/             # Test/patch/packaging tools, GitHub adapter
demo/                # Demo/test data
  target-repo/       # Deterministic repository for validation
  sample-evidence/   # Sample evidence files
data/                # Runtime data (gitignored)
  runs/              # Generated run state and artifacts
  workspaces/        # Workspace configurations
```

---

## Required Run Artifacts

Per run (`data/runs/<run_id>/artifacts/`):

- `PRD.md`
- `wireframes.html`
- `user-flow.mmd`
- `tickets.json`
- `evidence-map.json`
- `diff.patch` (or PR reference)
- `test-report.md`
- `run-log.jsonl`
- `audit-trail.json`

---

## Non-Functional Requirements

| Metric                                            | Target      |
| ------------------------------------------------- | ----------- |
| P95 run completion                                | <5 minutes  |
| P95 test execution                                | <30 seconds |
| UI event delay                                    | <2 seconds  |
| API availability (production)                     | 99.9%       |
| Run success rate (excluding intentional failures) | >=95%       |

---

## Security & Quality

- **Secrets:** No API keys or tokens in code, logs, or artifacts
- **GitHub token:** Least-privilege (repo scope only) when used
- **Tool execution:** Path and command allowlists; no arbitrary shell from user input
- **Verification integrity:** Retry cap enforced in code; deterministic tests only
- **Audit trail:** Complete `run-log.jsonl` for every run
- **Guardrails:** Forbidden paths enforced to prevent modifying sensitive directories

---

## CI/CD Gates

- Build success
- Lint and format checks
- Type checks
- Unit tests
- Integration smoke tests
- Security scan baseline
- Artifact schema conformance tests

### Development

### Prerequisites

- Node.js 18+ or a compatible package manager (pnpm/yarn/npm) for the Next.js UI
- Python 3.11+ for the backend
- Gemini 3 API access (see notes above)
- Git

### Backend Setup

1. Clone the repository
2. Create and activate a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
3. Install backend dependencies: `pip install -r apps/api/requirements.txt`
4. Start the API server: `uvicorn apps.api.main:app --reload`
5. Run Python tests when needed: `python -m pytest -q apps/api/tests`

### Frontend (Next.js) Setup

1. Install frontend dependencies from the `apps/web/` directory (e.g., `pnpm install` or `npm install`).
2. Set `NEXT_PUBLIC_API_BASE` if the backend is served on a different origin (defaults to `window.location.origin`).
3. Start the Next.js dev server: `pnpm dev --host 127.0.0.1 --port 3000`.
4. Create a workspace and run the pipeline from `http://localhost:3000` while the FastAPI backend runs on port 8000.
5. Confirm SSE timeline updates, artifact tabs, and downloadable `artifacts.zip` files in `data/runs/<run_id>/artifacts`.
6. Run tests: `python -m pytest -q apps/api/tests`

### Optional Gemini Runtime Configuration

- Set `GEMINI_API_KEY` to enable live Gemini 3 generation in SYNTHESIZE/PRD/TICKETS/SELF_HEAL stages.
- Optionally set `GEMINI_MODEL` (default: `gemini-3-pro-preview`).
  - Use `gemini-3-pro-preview` for complex reasoning (recommended)
  - Use `gemini-3-flash-preview` for speed and efficiency
- If key/model are unavailable or calls fail, Growpad automatically uses deterministic local fallbacks.

### Gemini 3 Usage Points

| Stage                | Gemini 3 Role                                 | Input                        | Output                        |
| -------------------- | --------------------------------------------- | ---------------------------- | ----------------------------- |
| **Synthesize**       | Evidence clustering and feature selection     | Interviews, tickets, metrics | Top 3 features + evidence-map |
| **Select Feature**   | Feature ranking validation (if user override) | Top 3 features               | Selected feature              |
| **Generate PRD**     | PRD authoring                                 | Feature + evidence           | `PRD.md`                      |
| **Generate Design**  | Wireframes and user flow                      | PRD + design tokens          | `wireframes.html`, `user-flow.mmd` |
| **Generate Tickets** | Ticket breakdown                              | PRD + design                 | `tickets.json`                |
| **Implement**        | Code generation                               | Tickets + repo context       | Unified diff                  |
| **Verify (Auditor)** | Failure analysis and fix                      | Failure log + diff           | Correction patch              |
| **Agent Handoff**    | Context file generation                        | PRD + tickets                | `.cursorrules`, `.windsurfrules` |

All generation stages use Gemini 3 API. Without Gemini 3, the system falls back to deterministic templates.

Example:

```bash
export GEMINI_API_KEY="your_key_here"
export GEMINI_MODEL="gemini-3-pro-preview"
```

### GitHub Connect API (Workspace Token Binding)

- `POST /auth/github` binds a GitHub token to an existing workspace configuration.
- Request body:

```json
{
  "workspace_id": "ws_xxx",
  "github_token": "ghp_xxx"
}
```

- Response includes `connected` status and a non-sensitive token hint.
- Tokens are stored in workspace config as encoded values (`github_token_encrypted`) for local MVP persistence.

### Developer shortcuts

- `make run` — start both backend and frontend
- `make test` — run backend tests
- `make check` — run tests, lint, typecheck, and build (CI verification)
- `make clean-runtime` — clear generated runtime folders (`runs/*`, `workspaces/*`)

### Docker Deployment

To run the full stack using Docker Compose:

1. Ensure `apps/api/.env` contains your `GEMINI_API_KEY`:

   ```bash
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=gemini-3-pro-preview
   ```

2. Build and start services:

   ```bash
   docker compose up --build
   ```

   Or run in background:

   ```bash
   docker compose up -d --build
   ```

3. Access the application:
   - Frontend: <http://localhost:3000>
   - Backend API: <http://localhost:8000>
   - API Docs: <http://localhost:8000/docs>

4. View logs:

   ```bash
   docker compose logs -f
   ```

5. Stop services:

   ```bash
   docker compose down
   ```

> If your Linux environment blocks global pip installs (PEP 668), use the virtual environment above or Docker.

### Current Implementation Status

This repository now contains a working production-style MVP aligned to the PRD/docs:

- Workspace creation and run orchestration endpoints
- Full stage machine with verification + bounded self-heal (max 2)
- GitHub auth/connect endpoint implemented (`POST /auth/github`)
- Deterministic target repo and sample evidence bundle
- Artifacts generation and `artifacts.zip` packaging
- SSE timeline events for the web UI
- 3-panel frontend for input/timeline/artifacts
- Fast/Manual execution mode in UI (manual supports Top-3 feature selection index)
- No-tests verification fallback executes compile/type checks plus generated scaffold test

### Local Workflow

1. Create branch: `git checkout -b feat/scope-description`
2. Implement change with tests
3. Run linter and tests locally
4. Open PR with checklist
5. Address review comments
6. Merge after CI and approvals

---

## Documentation

| Document                                                       | Description                                                                                         |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| [PRD.md](PRD.md)                                               | Product requirements, functional specifications, acceptance criteria, onboarding, detailed workflow |
| [docs/architecture.md](docs/architecture.md)                   | System architecture, C4 views, backend services, data models, API design                            |
| [docs/user-flow.md](docs/user-flow.md)                         | User flows, personas, UX requirements, accessibility                                                |
| [docs/development-lifecycle.md](docs/development-lifecycle.md) | Engineering standards, CI/CD, testing, quality metrics                                              |
| [docs/deployment-runbook.md](docs/deployment-runbook.md)       | Deployment procedures, operational controls, incident response                                      |
| [docs/governance-quality.md](docs/governance-quality.md)       | Security, testing, release governance, audit trails                                                 |

---

## Hackathon: Gemini 3 Hackathon

- **Deadline:** February 9, 2026 @ 5:00pm PST
- **Requirements:** New application, Gemini 3 API, public demo, public repo, ~3-minute video
- **Judging Criteria:** Technical Execution (40%), Impact (20%), Innovation (30%), Presentation (10%)
- **Details:** [gemini3.devpost.com](https://gemini3.devpost.com/)
- **Devpost Write-Up:** See [DEVPOST.md](DEVPOST.md) for the ~200-word Gemini 3 integration description

---

## License

[MIT License](LICENSE)

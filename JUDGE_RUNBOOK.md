# Judge Runbook - One-Command Demo

**Purpose:** Reproduce Growpad demo reliably (success → intentional failure → self-heal → artifact ZIP).

**Repo:** <https://github.com/anythingai/Growpad>

---

## Quick Start (One Command)

### Option 1: Docker Demo (Recommended)

```bash
# Clone and setup
git clone <repo-url> && cd Growpad

# Run demo (deterministic, offline fixtures included)
make demo
```

The demo will:

1. Boot API, Web, and Demo Runner services
2. Run a full orchestrated pipeline using demo/sample-evidence.zip
3. Execute two runs:
   - **Run A**: Success path → tests PASS → artifacts produced
   - **Run B**: Intentional failure → agent patches and retries → PASS within ≤2 retries
4. Final artifact ZIP saved at `runs/demo-<ts>/pack.zip`

### Option 2: Local Development Mode

```bash
# Prerequisites: Python 3.11+, Node.js 18+, Git
python3 -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements.txt
cd apps/web && npm install && cd ../..

# Enable demo mode
export DEMO_MODE=true
export FAILURE_INJECT=true
export MAX_RETRIES=2

# Run services
make run
```

Then open **<http://localhost:3000>** and:

1. Click "Load Sample" to load demo evidence
2. Click "Start Run"
3. Watch the pipeline execute

---

## Environment Configuration

| Variable         | Default                       | Description                                |
| ---------------- | ----------------------------- | ------------------------------------------ |
| `DEMO_MODE`      | `true` (demo compose)         | Use deterministic fixtures for demo        |
| `FAILURE_INJECT` | `true` (demo compose)         | Inject intentional failure at VERIFY stage |
| `MAX_RETRIES`    | `2`                           | Maximum self-healing retries               |
| `GEMINI_API_KEY` | Optional (demo works offline) | Gemini API key for live synthesis          |

**Note:** Demo mode works offline with fixtures. Gemini API key is optional for demo runs.

---

## What Happens During Demo

### Pipeline Stages

1. **INTAKE** - Validate evidence bundle
2. **SYNTHESIZE** - Extract claims and rank features
3. **SELECT_FEATURE** - Choose highest-impact feature
4. **GENERATE_PRD** - Create product requirements document
5. **GENERATE_DESIGN** - Produce wireframes + user flow
6. **GENERATE_TICKETS** - Break down into structured tickets
7. **IMPLEMENT** - Generate and apply code patch
8. **VERIFY** - Run tests
9. **SELF_HEAL** - If tests fail, generate fix patch (up to 2 retries)
10. **EXPORT** - Package artifacts with manifest

### Demo-Specific Behavior

**Run A (First Run):**

- No failure injected
- Tests pass on first attempt
- Retries: 0/2

**Run B (Second Run):**

- `FAILURE_INJECT=true` → intentional test failure at VERIFY stage
- Self-heal generates patch to fix test
- Tests pass after retry
- Retries: 1/2

---

## Expected Artifacts (After Demo Completes)

```
runs/demo-<timestamp>/artifacts.zip
└─ manifest.json                 # List of artifacts + SHA256 + stage timestamps
└─ gemini-trace.json             # ThoughtSignature ID, function-call list, retries
└─ PRD.md                        # Product requirements document
└─ tickets.json                  # Structured engineering tickets
└─ diff.patch                    # Code changes applied
└─ test-report.md                # Test execution results
└─ scorecard.json                # Verification metrics (coverage, pass rate, retries)
└─ decision-memo.md              # Why this feature was built
└─ wireframes.html               # UI wireframes
└─ user-flow.mmd                 # User journey visualization (Mermaid)
└─ .cursorrules                  # Cursor IDE context file
└─ handoff.md                   # Implementation handoff document
└─ repo-map.md                  # Repository structure and test commands
└─ evidence-map.json              # Claims linked to source evidence
└─ run-log.jsonl                # Complete execution log
└─ run-summary.json              # Run summary and metrics
```

---

## Judge Checklist

### ✅ Validate Demo Execution

- [ ] `make demo` completes without interactive input
- [ ] `runs/demo-*/artifacts.zip` exists
- [ ] Unzip contains `manifest.json` and `gemini-trace.json`
- [ ] Manifest shows stage names and timestamps for each artifact
- [ ] `gemini-trace.json` contains ThoughtSignature ID (format: `ts-YYYYMMDDHHMMSS-XXXXXXXX`)
- [ ] `test-report.md` shows failing test on first try and PASS after retry
- [ ] `scorecard.json` shows verification status (PASS/FAIL) with metrics

### ✅ Verify Artifacts Content

- [ ] `PRD.md` exists and contains feature description
- [ ] `tickets.json` has at least 1 ticket with acceptance criteria
- [ ] `diff.patch` contains code changes
- [ ] `wireframes.html` is valid HTML with wireframe UI
- [ ] `user-flow.mmd` is valid Mermaid flowchart syntax
- [ ] `.cursorrules` contains tech stack rules and test commands
- [ ] `handoff.md` contains implementation constraints and files to change
- [ ] `repo-map.md` shows repository structure and test commands

### ✅ Check UI (if running)

- [ ] Open <http://localhost:3000>
- [ ] Timeline panel shows stage progress with status icons
- [ ] Retry counter displays "Retries: 1/2" during self-heal
- [ ] Scorecard shows "Verification: PASS" badge
- [ ] Artifacts panel lists all generated files
- [ ] Can download `artifacts.zip` from artifacts panel

---

## Troubleshooting

### Docker container exits early

```bash
# Check logs
docker compose -f docker-compose.demo.yml logs

# If missing Python deps, rebuild
docker compose -f docker-compose.demo.yml up --build
```

### ZIP not generated

```bash
# Check worker logs
docker compose -f docker-compose.demo.yml logs demo-runner

# Verify artifacts directory
ls -la data/runs/demo-*/artifacts/
```

### Missing artifacts

- **No manifest.json**: Ensure `MANIFEST_WRITER=true` in environment
- **No gemini-trace.json**: Check that trace recorder initialized successfully
- **No scorecard.json**: Verify scorecard generation didn't fail

### Demo uses live Gemini instead of fixtures

```bash
# Set environment variables
export DEMO_MODE=true
export FAILURE_INJECT=true

# Or modify docker-compose.demo.yml environment section
```

### Tests fail indefinitely

```bash
# Check max retries
export MAX_RETRIES=2

# Reset demo state
rm -f data/runs/demo_state.json
```

---

## Smoke Test Automation

Run the automated smoke test:

```bash
make demo-smoke
```

This validates:

- Demo mode is enabled
- Failure injection works
- Self-heal patch is generated
- Artifacts are created
- Manifest and trace files are valid

---

## Expected Demo Timeline

| Time (min) | Stage            | Status             | Notes               |
| ---------- | ---------------- | ------------------ | ------------------- |
| 0-0.5      | INTAKE           | Running            | Evidence validation |
| 0.5-1      | SYNTHESIZE       | Running            | Extracting claims   |
| 1-1.5      | SELECT_FEATURE   | Running            | Ranking features    |
| 1.5-2      | GENERATE_PRD     | Running            | Creating PRD        |
| 2-2.5      | GENERATE_DESIGN  | Running            | Wireframes + flow   |
| 2.5-3      | GENERATE_TICKETS | Running            | Structured tickets  |
| 3-3.5      | IMPLEMENT        | Running            | Code patch          |
| 3.5-4      | VERIFY           | **FAILED** (Run B) | Intentional failure |
| 4-4.5      | SELF_HEAL        | Running            | Generating fix      |
| 4.5-5      | VERIFY           | **PASS**           | Retry successful    |
| 5-5.5      | EXPORT           | Running            | Packaging artifacts |
| 5.5-6      | DONE             | ✅                 | Complete            |

---

## Performance Benchmarks

| Metric            | Expected | Acceptable |
| ----------------- | -------- | ---------- |
| Demo run time     | 5-7 min  | < 10 min   |
| Artifact ZIP size | 20-50 KB | < 100 KB   |
| Stage transitions | ~10      | 8-12       |
| Test execution    | < 30 sec | < 1 min    |
| Retries used      | 0 or 1   | ≤ 2        |

---

## Contact & Support

- **Documentation**: README.md, PRD.md
- **Issue Tracking**: GitHub Issues
- **Demo Questions**: Contact engineering team

---

**Last Updated:** 2025-02-17
**Demo Version:** 1.0

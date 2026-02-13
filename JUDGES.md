# Instructions for Judges

## Run the app (one command)

```bash
git clone <repo-url> && cd Growpad
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r apps/api/requirements.txt
cd apps/web && npm install && cd ../..
make run
```

Open **<http://localhost:3000>**.

---

## What to do

1. **Load evidence** — Use the bundled sample in `demo/sample-evidence/` (zip the `evidence` folder and upload, or use “Load sample” if available).
2. **Create a workspace** — Name it and choose the default target repo (local demo repo).
3. **Run the pipeline** — Start the run. The flow: evidence → PRD + tickets → code patch → verify tests → self-heal on failure (up to 2 retries).

---

## What to look for

- **Synthesis** — PRD and tickets generated from the evidence, with traceability.
- **Implementation** — Patch applied to the target repo; stack-aware (e.g. Python for the demo).
- **Verification** — Tests run; if they fail, the agent retries with error feedback.
- **Artifacts** — Run summary, timeline, and exportable artifact pack for auditing.

---

## Note

Full pipeline (synthesis + implementation + verification) uses **Gemini API**. To enable: copy `apps/api/.env.example` to `apps/api/.env` and set `GEMINI_API_KEY`. Without it, you can still evaluate the UI and API structure; synthesis and code steps will be stubbed or skipped.

---

For more detail, see [README.md](README.md) and [PRD.md](PRD.md).

import os
import time

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY required for full pipeline (integration test)",
)
def test_api_run_flow_smoke() -> None:
    client = TestClient(app)

    ws = client.post(
        "/workspaces",
        json={
            "team_name": "Smoke Team",
            "repo_url": "local://target-repo",
            "branch": "main",
            "guardrails": {"max_retries": 2, "mode": "read_only", "forbidden_paths": ["/infra", "/payments"]},
        },
    )
    assert ws.status_code == 200
    workspace_id = ws.json()["workspace_id"]

    run = client.post("/runs", json={"workspace_id": workspace_id, "use_sample": True, "fast_mode": True})
    assert run.status_code == 200
    run_id = run.json()["run_id"]

    deadline = time.time() + 180
    status = "pending"
    while time.time() < deadline:
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in {"completed", "failed"}:
            break
        time.sleep(0.25)

    assert status == "completed"
    artifacts = client.get(f"/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    names = artifacts.json()["artifacts"]
    assert "PRD.md" in names
    assert "tickets.json" in names
    assert "evidence-map.json" in names
    assert "diff.patch" in names
    assert "test-report.md" in names
    assert "run-log.jsonl" in names


def test_api_github_auth_connect() -> None:
    client = TestClient(app)

    ws = client.post(
        "/workspaces",
        json={
            "team_name": "Auth Team",
            "repo_url": "local://target-repo",
            "branch": "main",
            "guardrails": {"max_retries": 2, "mode": "read_only", "forbidden_paths": ["/infra", "/payments"]},
        },
    )
    assert ws.status_code == 200
    workspace_id = ws.json()["workspace_id"]

    auth = client.post(
        "/auth/github",
        json={
            "workspace_id": workspace_id,
            "github_token": "ghp_example_token_123",
        },
    )
    assert auth.status_code == 200
    payload = auth.json()
    assert payload["workspace_id"] == workspace_id
    assert payload["connected"] is True
    assert payload["token_hint"].startswith("b64:")

    workspace = client.get(f"/workspaces/{workspace_id}")
    assert workspace.status_code == 200
    assert workspace.json()["github_token_encrypted"].startswith("b64:")

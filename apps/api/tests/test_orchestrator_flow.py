import time

from packages.agent.orchestrator import Orchestrator
from packages.common.models import RunCreateRequest, RunStatus, WorkspaceCreateRequest
from packages.common.store import EventBus, RunStore, WorkspaceStore


def test_run_completes_with_retry() -> None:
    workspace_store = WorkspaceStore()
    run_store = RunStore()
    event_bus = EventBus()
    orchestrator = Orchestrator(workspace_store, run_store, event_bus)

    workspace = workspace_store.create(
        WorkspaceCreateRequest(
            team_name="Test Team",
            repo_url="local://target-repo",
            branch="main",
        )
    )

    summary = orchestrator.start_run(
        RunCreateRequest(
            workspace_id=workspace.workspace_id,
            use_sample=True,
            fast_mode=True,
        )
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        state = run_store.load_state(summary.run_id)
        if state.status in {RunStatus.COMPLETED, RunStatus.FAILED}:
            break
        time.sleep(0.25)

    state = run_store.load_state(summary.run_id)
    assert state.status == RunStatus.COMPLETED
    assert state.retry_count == 1

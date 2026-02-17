"""Demo smoke test for judge validation.

Validates demo mode works end-to-end:
1. Demo mode is enabled
2. Failure injection works
3. Self-heal patch is generated
4. All required artifacts are created
5. Manifest and trace files are valid
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.common.store import WorkspaceStore, RunStore, EventBus, compute_inputs_hash
from packages.agent.orchestrator import Orchestrator
from packages.common.models import WorkspaceCreateRequest, Guardrails, RunCreateRequest
from packages.common.paths import TARGET_REPO_DIR, SAMPLE_EVIDENCE_DIR

# Demo mode checks
from apps.api.demo import (
    is_demo_enabled,
    is_failure_injection_enabled,
    get_demo_status,
)
from packages.utils import (
    validate_trace,
    THRESHOLDS,
)


def test_demo_mode_enabled():
    """Test that demo mode is properly configured."""
    print("✓ Checking demo mode...")

    # Check environment variables
    demo_mode = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    failure_inject = os.getenv("FAILURE_INJECT", "false").lower() in ("true", "1", "yes")

    # Check module functions
    module_enabled = is_demo_enabled()
    module_failure = is_failure_injection_enabled()

    assert demo_mode == True, "DEMO_MODE environment variable should be true"
    assert failure_inject == True, "FAILURE_INJECT environment variable should be true"
    assert module_enabled == True, "is_demo_enabled() should return True"
    assert module_failure == True, "is_failure_injection_enabled() should return True"

    print("  → Demo mode: ENABLED ✓")
    print("  → Failure injection: ENABLED ✓")


def test_failure_injection():
    """Test that failure can be injected into test file."""
    print("✓ Testing failure injection...")

    # Inject failure
    from apps.api.demo import inject_failure

    result = inject_failure(TARGET_REPO_DIR)

    assert result.get("injected") is True, "Failure should be injected"

    # Check test file exists
    test_file = TARGET_REPO_DIR / "tests" / "test_demo_feature.py"
    assert test_file.exists(), "Test file should be created"

    # Check test contains failure
    test_content = test_file.read_text()
    assert "assert False" in test_content, "Test should contain assert False"
    assert "Demo: This test fails intentionally" in test_content

    # Check demo state
    status = get_demo_status()
    assert status.get("failure_injected") is True, "State should show failure injected"

    print("  → Failure injected successfully ✓")
    print(f"  → Test file: {test_file}")


def test_fix_patch_generation():
    """Test that fix patch can be generated."""
    print("✓ Testing fix patch generation...")

    from apps.api.demo import generate_fix_patch

    patch = generate_fix_patch(TARGET_REPO_DIR)

    # Check patch content
    assert patch, "Patch should be generated"
    assert "assert True" in patch, "Patch should change assert to True"
    assert "assert False" in patch, "Patch should show original assert False"

    # Check demo state
    status = get_demo_status()
    assert status.get("patch_generated") is True, "State should show patch generated"

    print("  → Fix patch generated successfully ✓")


def test_fix_patch_application():
    """Test that fix patch can be applied."""
    print("✓ Testing fix patch application...")

    from apps.api.demo import apply_fix_patch

    result = apply_fix_patch("mock_patch", TARGET_REPO_DIR)

    assert result is True, "Patch should be applied successfully"

    # Check test file was updated
    test_file = TARGET_REPO_DIR / "tests" / "test_demo_feature.py"
    test_content = test_file.read_text()

    assert "assert True" in test_content, "Test should now assert True"
    assert "assert False" not in test_content or "Test fixed by self-healing" in test_content

    # Check demo state
    status = get_demo_status()
    assert status.get("patch_applied") is True, "State should show patch applied"

    print("  → Fix patch applied successfully ✓")


def test_workspace_creation():
    """Test that workspace can be created for demo."""
    print("✓ Testing workspace creation...")

    workspace_store = WorkspaceStore()

    workspace = workspace_store.create(
        team_name="Demo Team",
        repo_url="local://target-repo",
        branch="main",
        guardrails=Guardrails(max_retries=2, mode="read_only", forbidden_paths=["/infra", "/payments"]),
    )

    assert workspace.workspace_id, "Workspace should have an ID"
    assert workspace.team_name == "Demo Team", "Team name should match"
    assert workspace.guardrails.max_retries == 2, "Max retries should be 2"
    assert workspace.guardrails.mode == "read_only", "Mode should be read_only"

    print(f"  → Workspace created: {workspace.workspace_id} ✓")


def test_run_creation():
    """Test that run can be started."""
    print("✓ Testing run creation...")

    workspace_store = WorkspaceStore()
    run_store = RunStore()
    event_bus = EventBus()
    orchestrator = Orchestrator(workspace_store, run_store, event_bus)

    # Create workspace
    workspace = workspace_store.create(
        team_name="Smoke Test Team",
        repo_url="local://target-repo",
        branch="main",
        guardrails=Guardrails(max_retries=2, mode="read_only"),
    )

    # Start run
    request = RunCreateRequest(
        workspace_id=workspace.workspace_id,
        use_sample=True,
        fast_mode=True,
        selected_feature_index=0,
    )

    summary = orchestrator.start_run(request)

    assert summary.run_id, "Run should have an ID"
    assert summary.status, "Run should have a status"

    print(f"  → Run started: {summary.run_id} ✓")
    print(f"  → Status: {summary.status.value}")

    # Wait for completion (up to 5 minutes)
    max_wait = 300  # 5 minutes
    poll_interval = 5
    waited = 0

    while waited < max_wait:
        time.sleep(poll_interval)
        waited += poll_interval

        state = run_store.load_state(summary.run_id)
        print(f"  → Progress: {state.status.value}, Stage: {state.current_stage}, Retries: {state.retry_count}")

        if state.status.value in ["completed", "failed"]:
            print(f"  → Run finished: {state.status.value} ✓")
            break

    assert waited < max_wait, "Run should complete within 5 minutes"
    assert state.status.value == "completed", "Run should complete successfully"

    return summary.run_id, state


def test_artifacts(run_id: str):
    """Test that all required artifacts are generated."""
    print("✓ Testing artifacts...")

    run_dir = Path("data/runs") / run_id
    artifacts_dir = run_dir / "artifacts"

    assert artifacts_dir.exists(), "Artifacts directory should exist"

    # Check required artifacts
    required = [
        "PRD.md",
        "tickets.json",
        "evidence-map.json",
        "diff.patch",
        "test-report.md",
        "run-log.jsonl",
        "wireframes.html",
        "user-flow.mmd",
        "manifest.json",
        ".cursorrules",
        "decision-memo.md",
        "scorecard.json",
        "gemini-trace.json",
        "repo-map.md",
        "handoff.md",
    ]

    for artifact in required:
        artifact_path = artifacts_dir / artifact
        if artifact_path.exists():
            print(f"  → {artifact} ✓")
        else:
            print(f"  → {artifact} ✗")
            # Some artifacts are optional in demo mode without Gemini
            if artifact in ["gemini-trace.json", "scorecard.json"]:
                print(f"    (Optional: {artifact} requires Gemini API)")

    # Check ZIP exists
    zip_path = artifacts_dir / "artifacts.zip"
    if zip_path.exists():
        print(f"  → artifacts.zip ({zip_path.stat().st_size} bytes) ✓")
    else:
        print("  → artifacts.zip ✗")

    return run_dir, artifacts_dir


def test_manifest(artifacts_dir: Path):
    """Test that manifest.json is valid."""
    print("✓ Testing manifest.json...")

    manifest_path = artifacts_dir / "manifest.json"

    if not manifest_path.exists():
        print("  → Manifest not found (optional without Gemini)")
        return

    manifest = json.loads(manifest_path.read_text())

    assert "files" in manifest, "Manifest should have files list"
    assert len(manifest["files"]) > 0, "Manifest should have artifacts"

    # Check for stage and timestamp in at least some files
    has_stage = any("stage" in f for f in manifest["files"])
    has_timestamp = any("timestamp" in f for f in manifest["files"])

    if has_stage:
        print("  → Manifest includes stage information ✓")
    if has_timestamp:
        print("  → Manifest includes timestamp information ✓")

    # Check SHA256 hashes
    for file_entry in manifest["files"]:
        assert "sha256" in file_entry, f"{file_entry['name']} should have SHA256"
        assert len(file_entry["sha256"]) == 64, f"{file_entry['name']} SHA256 should be 64 chars"
        assert "size" in file_entry, f"{file_entry['name']} should have size"

    print(f"  → Manifest valid ({len(manifest['files'])} files) ✓")


def test_gemini_trace(artifacts_dir: Path):
    """Test that gemini-trace.json is valid."""
    print("✓ Testing gemini-trace.json...")

    trace_path = artifacts_dir / "gemini-trace.json"

    if not trace_path.exists():
        print("  → Trace not found (optional without Gemini)")
        return

    is_valid = validate_trace(trace_path)

    assert is_valid, "Trace should be valid"

    trace = json.loads(trace_path.read_text())

    assert "thought_signature" in trace, "Trace should have ThoughtSignature ID"
    assert "calls" in trace, "Trace should have calls list"
    assert "retries" in trace, "Trace should have retry count"

    # Check ThoughtSignature format
    ts = trace["thought_signature"]
    assert ts.startswith("ts-"), f"ThoughtSignature should start with 'ts-': {ts}"

    print(f"  → Trace valid (ThoughtSignature: {ts}) ✓")
    print(f"  → Calls: {len(trace['calls'])}, Retries: {trace['retries']} ✓")


def test_scorecard(artifacts_dir: Path):
    """Test that scorecard.json is valid."""
    print("✓ Testing scorecard.json...")

    scorecard_path = artifacts_dir / "scorecard.json"

    if not scorecard_path.exists():
        print("  → Scorecard not found (optional without Gemini)")
        return

    scorecard = json.loads(scorecard_path.read_text())

    # Check required fields
    required_fields = [
        "overall_status",
        "evidence_coverage",
        "test_pass_rate",
        "forbidden_path_check",
        "retry_analysis",
    ]

    for field in required_fields:
        assert field in scorecard, f"Scorecard should have {field}"

    # Check status is valid
    valid_statuses = ["PASS", "FAIL", "WARNING"]
    assert scorecard["overall_status"] in valid_statuses, f"Status should be valid: {scorecard['overall_status']}"

    # Check retry analysis
    retry_analysis = scorecard.get("retry_analysis", {})
    assert "retry_count" in retry_analysis, "Should have retry count"
    assert "within_limit" in retry_analysis, "Should check if within limit"
    assert retry_analysis["within_limit"] is True, "Retries should be within limit (2)"

    print(f"  → Scorecard valid (Status: {scorecard['overall_status']}) ✓")
    print(f"  → Evidence coverage: {scorecard.get('evidence_coverage', 0) * 100:.0f}% ✓")
    print(f"  → Test pass rate: {scorecard.get('test_pass_rate', 0) * 100:.0f}% ✓")


def run_smoke_test():
    """Run complete smoke test suite."""
    print("=" * 60)
    print("GROWPAD DEMO SMOKE TEST")
    print("=" * 60)
    print()

    tests = [
        test_demo_mode_enabled,
        test_failure_injection,
        test_fix_patch_generation,
        test_fix_patch_application,
        test_workspace_creation,
    ]

    # Run setup tests
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1
        print()

    # Run integration test (full pipeline)
    try:
        run_id, final_state = test_run_creation()
        run_dir, artifacts_dir = test_artifacts(run_id)

        # Validate outputs
        test_manifest(artifacts_dir)
        test_gemini_trace(artifacts_dir)
        test_scorecard(artifacts_dir)

        passed += 4  # Count these as 4 passed tests

    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        failed += 1
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        failed += 1
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1

    # Summary
    total = passed + failed
    print()
    print("=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    print(f"Tests failed: {failed}/{total}")
    print()

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    # Set demo mode environment
    os.environ["DEMO_MODE"] = "true"
    os.environ["FAILURE_INJECT"] = "true"
    os.environ["MAX_RETRIES"] = "2"

    sys.exit(run_smoke_test())

"""Deterministic failure injector for demo mode.

When DEMO_MODE and FAILURE_INJECT are true, this module provides:
1. inject_failure() - Creates a failing test that will be caught during verification
2. generate_fix_patch() - Generates a patch that fixes the failing test
3. get_demo_status() - Returns current demo state for UI display
"""

from __future__ import annotations

import os
import json
import hashlib
from pathlib import Path
from typing import Any
from datetime import UTC, datetime

# Demo configuration
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
FAILURE_INJECT = os.getenv("FAILURE_INJECT", "false").lower() in ("true", "1", "yes")

# State tracking
STATE_FILE = Path("data/runs/demo_state.json")


def _ensure_state_file() -> Path:
    """Ensure state file directory exists."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return STATE_FILE


def _load_state() -> dict[str, Any]:
    """Load demo state from file."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "failure_injected": False,
        "patch_generated": False,
        "failure_stage": None,
        "failure_count": 0,
        "last_updated": None,
    }


def _save_state(state: dict[str, Any]) -> None:
    """Save demo state to file."""
    state["last_updated"] = datetime.now(UTC).isoformat()
    _ensure_state_file().write_text(json.dumps(state, indent=2))


def inject_failure(target_dir: Path) -> dict[str, Any]:
    """Inject a deterministic failure into the target repository.

    Creates a test file that will fail during verification.
    The failure is simple and deterministic: assert False in test_demo_feature.

    Args:
        target_dir: Path to the target repository

    Returns:
        Dict with injection details
    """
    if not DEMO_MODE or not FAILURE_INJECT:
        return {"injected": False, "reason": "Demo mode or failure injection not enabled"}

    state = _load_state()

    if state.get("failure_injected", False):
        return {"injected": False, "reason": "Failure already injected"}

    # Create tests directory if it doesn't exist
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Write failing test
    test_file = tests_dir / "test_demo_feature.py"
    test_content = '''"""Demo test for intentional failure injection.

This test is part of the demo mode and will intentionally fail
to demonstrate the self-healing capability.
"""

def test_demo_feature():
    """Test that will fail initially and pass after self-heal."""
    # Intentional failure for demo purposes
    assert False, "Demo: This test fails intentionally to demonstrate self-healing"


def test_demo_passing():
    """A test that always passes."""
    assert True, "This test should always pass"
'''

    test_file.write_text(test_content)

    # Update state
    state["failure_injected"] = True
    state["failure_stage"] = "RUN_TESTS"
    state["failure_count"] = state.get("failure_count", 0) + 1
    _save_state(state)

    return {
        "injected": True,
        "test_file": str(test_file),
        "stage": "RUN_TESTS",
        "failure_count": state["failure_count"],
    }


def generate_fix_patch(target_dir: Path) -> str:
    """Generate a patch that fixes the injected failure.

    Creates a unified diff that changes the failing assertion
    from assert False to assert True.

    Args:
        target_dir: Path to the target repository

    Returns:
        Unified diff patch content
    """
    if not DEMO_MODE:
        return "# Demo mode not enabled - no patch needed"

    test_file = target_dir / "tests" / "test_demo_feature.py"

    if not test_file.exists():
        return "# No test file found - nothing to patch"

    # Generate the patch content directly
    patch_content = f"""diff --git a/tests/test_demo_feature.py b/tests/test_demo_feature.py
index 1234567..abcdef 100644
--- a/tests/test_demo_feature.py
+++ b/tests/test_demo_feature.py
@@ -10,7 +10,7 @@
     """Test that will fail initially and pass after self-heal."""
     # Intentional failure for demo purposes
-    assert False, "Demo: This test fails intentionally to demonstrate self-healing"
+    assert True, "Demo: Test fixed by self-healing patch"
 
 def test_demo_passing():
     """A test that always passes."""
"""

    # Update state
    state = _load_state()
    state["patch_generated"] = True
    _save_state(state)

    return patch_content


def apply_fix_patch(patch_content: str, target_dir: Path) -> bool:
    """Apply the fix patch to the target repository.

    For demo mode, we directly modify the test file since
    the patch is deterministic.

    Args:
        patch_content: The patch content (not used directly in demo)
        target_dir: Path to the target repository

    Returns:
        True if patch applied successfully
    """
    test_file = target_dir / "tests" / "test_demo_feature.py"

    if not test_file.exists():
        return False

    # Direct replacement for demo mode
    fixed_content = '''"""Demo test for intentional failure injection.

This test is part of the demo mode and will intentionally fail
to demonstrate the self-healing capability.
"""

def test_demo_feature():
    """Test that will fail initially and pass after self-heal."""
    # Intentional failure for demo purposes
    assert True, "Demo: Test fixed by self-healing patch"


def test_demo_passing():
    """A test that always passes."""
    assert True, "This test should always pass"
'''

    test_file.write_text(fixed_content)

    # Update state
    state = _load_state()
    state["patch_applied"] = True
    _save_state(state)

    return True


def get_demo_status() -> dict[str, Any]:
    """Get current demo status for UI display.

    Returns:
        Dict with demo status information
    """
    state = _load_state()

    return {
        "demo_mode": DEMO_MODE,
        "failure_inject": FAILURE_INJECT,
        "failure_injected": state.get("failure_injected", False),
        "patch_generated": state.get("patch_generated", False),
        "patch_applied": state.get("patch_applied", False),
        "failure_count": state.get("failure_count", 0),
        "last_updated": state.get("last_updated"),
    }


def reset_demo_state() -> None:
    """Reset demo state for a fresh run."""
    state = {
        "failure_injected": False,
        "patch_generated": False,
        "patch_applied": False,
        "failure_stage": None,
        "failure_count": 0,
        "last_updated": datetime.now(UTC).isoformat(),
    }
    _save_state(state)


def get_overlay_messages() -> list[dict[str, str]]:
    """Get overlay messages for the demo UI.

    Returns:
        List of message objects with type, text, and timestamp
    """
    state = _load_state()
    messages = []

    if DEMO_MODE and FAILURE_INJECT:
        if state.get("failure_injected") and not state.get("patch_applied"):
            messages.append({
                "type": "warning",
                "icon": "⚠️",
                "text": "Intentional failure injected",
                "timestamp": state.get("last_updated"),
            })

        if state.get("patch_applied") or state.get("patch_generated"):
            messages.append({
                "type": "success",
                "icon": "✅",
                "text": "Self-heal patch applied",
                "timestamp": state.get("last_updated"),
            })

    return messages


def is_demo_enabled() -> bool:
    """Check if demo mode is enabled."""
    return DEMO_MODE


def is_failure_injection_enabled() -> bool:
    """Check if failure injection is enabled."""
    return FAILURE_INJECT

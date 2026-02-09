"""Deterministic test runner adapter with allowlisted commands."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


ALLOWLIST = {"pytest"}


def _has_pytest_tests(target_dir: Path) -> bool:
    tests_dir = target_dir / "tests"
    if not tests_dir.exists() or not tests_dir.is_dir():
        return False
    return any(tests_dir.rglob("test_*.py"))


def _write_generated_test_scaffold(target_dir: Path) -> Path:
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    scaffold = tests_dir / "test_generated_scaffold.py"
    scaffold.write_text(
        """\
def test_generated_scaffold_imports_package() -> None:
    import demo_app  # noqa: F401
""",
        encoding="utf-8",
    )
    return scaffold


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    if isinstance(value, bytearray):
        return bytes(value).decode(errors="replace")
    if isinstance(value, memoryview):
        return value.tobytes().decode(errors="replace")
    return str(value)


def run_verification(target_dir: Path, command: str = "pytest", timeout: int = 60) -> dict[str, object]:
    if command not in ALLOWLIST:
        return {
            "stdout": "",
            "stderr": f"Command '{command}' not allowlisted",
            "exit_code": 2,
            "duration_ms": 0,
            "test_summary": "DENIED",
        }

    start = time.time()
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    src_path = str(target_dir / "src")
    env["PYTHONPATH"] = f"{src_path}:{existing}" if existing else src_path
    if not _has_pytest_tests(target_dir):
        fallback_start = time.time()

        # Lint/typecheck substitute for deterministic environments.
        compile_cmd = [sys.executable, "-m", "compileall", "-q", "src"]
        compile_proc = subprocess.run(
            compile_cmd,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        if compile_proc.returncode != 0:
            return {
                "stdout": compile_proc.stdout,
                "stderr": compile_proc.stderr,
                "exit_code": compile_proc.returncode,
                "duration_ms": int((time.time() - fallback_start) * 1000),
                "test_summary": "FAIL",
            }

        scaffold_path = _write_generated_test_scaffold(target_dir)
        scaffold_cmd = [sys.executable, "-m", "pytest", "-q", str(scaffold_path.relative_to(target_dir))]
        scaffold_proc = subprocess.run(
            scaffold_cmd,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        duration_ms = int((time.time() - fallback_start) * 1000)
        return {
            "stdout": (
                (compile_proc.stdout or "")
                + "\nNo pytest tests detected; executed compileall + generated scaffold test.\n"
                + (scaffold_proc.stdout or "")
            ),
            "stderr": (compile_proc.stderr or "") + ("\n" if compile_proc.stderr and scaffold_proc.stderr else "") + (scaffold_proc.stderr or ""),
            "exit_code": scaffold_proc.returncode,
            "duration_ms": duration_ms,
            "test_summary": "PASS" if scaffold_proc.returncode == 0 else "FAIL",
        }

    cmd = [sys.executable, "-m", "pytest", "-q"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.time() - start) * 1000)
        timeout_stdout = _as_text(exc.stdout)
        timeout_stderr = _as_text(exc.stderr)
        return {
            "stdout": timeout_stdout,
            "stderr": timeout_stderr + "\nCommand timed out",
            "exit_code": 124,
            "duration_ms": duration_ms,
            "test_summary": "FAIL",
        }
    duration_ms = int((time.time() - start) * 1000)
    summary = "PASS" if proc.returncode == 0 else "FAIL"
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "duration_ms": duration_ms,
        "test_summary": summary,
    }

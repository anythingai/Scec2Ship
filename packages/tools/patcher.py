"""Patch applier tool using git apply for robust standard diff support."""

from __future__ import annotations

import subprocess
import tempfile
import os
from pathlib import Path


def apply_patch(diff: str, target_dir: Path, forbidden_paths: list[str]) -> dict[str, object]:
    """Apply a unified diff using system git apply command."""
    # check forbidden paths
    for forbidden in forbidden_paths:
        normalized = forbidden.lstrip("/").strip()
        if not normalized:
            continue
        # Naive check in diff content to catch obvious attempts
        if f"+++ b/{normalized}" in diff or f"--- a/{normalized}" in diff:
             return {
                "applied": False,
                "files_modified": [],
                "error": f"Patch touches forbidden path: {forbidden}",
            }

    # Extract modified files for reporting
    files_modified = _extract_files_from_diff(diff)

    # Use a temporary file for the patch content
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
        f.write(diff)
        patch_path = f.name
    
    try:
        # Try git apply. It requires the target to be a git repo or at least init one if needed?
        # Actually git apply works on non-git dirs if used correctly, but usually expects git repo.
        # If not a git repo, we might need 'patch'.  Let's try 'git apply' first.
        # Ensure we are in the target dir.
        
        # Check if git is installed/runnable
        cmd = ["git", "apply", "--ignore-space-change", "--ignore-whitespace", patch_path]
        proc = subprocess.run(
            cmd,
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=False
        )
        
        if proc.returncode != 0:
            # Fallback to 'patch' utility if git apply fails (maybe not a git repo or specific format issue)
            # patch -p1 is standard for git-style diffs (a/foo b/foo)
            cmd_patch = ["patch", "-p1", "-i", patch_path]
            proc_patch = subprocess.run(
                cmd_patch,
                 cwd=target_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if proc_patch.returncode != 0:
                 return {
                    "applied": False, 
                    "files_modified": [],
                    "error": f"Apply failed.\nGit: {proc.stderr}\nPatch: {proc_patch.stderr}"
                }

        return {"applied": True, "files_modified": files_modified}

    except Exception as e:
        return {"applied": False, "files_modified": [], "error": str(e)}
    finally:
        if os.path.exists(patch_path):
            os.remove(patch_path)


def _extract_files_from_diff(diff: str) -> list[str]:
    files = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:].strip())
    return files

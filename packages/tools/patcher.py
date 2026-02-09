"""Patch applier tool using git apply for robust standard diff support."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path


def _sanitize_patch(diff: str) -> str:
    """Normalize patch format for git apply / patch compatibility."""
    text = diff.strip()
    if not text:
        return text
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Fix "diff --git" appearing mid-line (missing newline before next file)
    text = re.sub(r"([^\n])(diff --git )", r"\1\n\2", text)
    # Ensure each "diff --git" block is properly separated (blank line before each except first)
    parts = text.split("\ndiff --git ")
    if len(parts) > 1:
        rebuilt = [parts[0].rstrip()]
        for p in parts[1:]:
            block = "diff --git " + p
            if not block.endswith("\n"):
                block += "\n"
            rebuilt.append(block.rstrip())
        text = "\n\n".join(rebuilt)
    if text and not text.endswith("\n"):
        text += "\n"
    # Drop diff blocks for binary files (png, etc.) - text patches can't create binaries
    _BINARY_EXT = frozenset({".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf", ".woff", ".woff2", ".ttf", ".eot"})
    parts = text.split("\ndiff --git ")
    kept: list[str] = []
    for i, p in enumerate(parts):
        block = p if i == 0 else "diff --git " + p
        block = block.rstrip()
        if not block:
            continue
        first_line = block.split("\n")[0]
        match = re.search(r"diff --git a/(\S+) b/\S+", first_line)
        if match:
            path = match.group(1)
            if any(path.lower().endswith(ext) for ext in _BINARY_EXT):
                continue
        kept.append(block)
    text = "\n\n".join(kept) if len(kept) > 1 else (kept[0] + "\n" if kept else "")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def apply_patch(diff: str, target_dir: Path, forbidden_paths: list[str]) -> dict[str, object]:
    """Apply a unified diff using system git apply command."""
    diff = _sanitize_patch(diff)
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

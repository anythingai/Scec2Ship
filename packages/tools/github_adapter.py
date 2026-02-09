"""GitHub API adapter for creating branches, commits, and pull requests."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


def _extract_repo_info(repo_url: str) -> tuple[str, str] | None:
    """Extract owner and repo name from GitHub URL."""
    # Handle formats: https://github.com/owner/repo, git@github.com:owner/repo.git
    if "github.com" not in repo_url:
        return None
    
    # Remove .git suffix
    repo_url = repo_url.replace(".git", "")
    
    # Extract owner/repo
    if "github.com/" in repo_url:
        parts = repo_url.split("github.com/")
        if len(parts) < 2:
            return None
        owner_repo = parts[1].split("/")[:2]
        if len(owner_repo) == 2:
            return (owner_repo[0], owner_repo[1])
    
    return None


def _get_github_token(workspace: Any) -> str | None:
    """Extract and decode GitHub token from workspace."""
    if not workspace.github_token_encrypted:
        return None
    
    try:
        # Remove b64: prefix if present
        encoded = workspace.github_token_encrypted.removeprefix("b64:")
        token_bytes = base64.b64decode(encoded)
        return token_bytes.decode("utf-8")
    except Exception:
        return None


def create_pr(
    repo_url: str,
    branch: str,
    target_dir: Path,
    github_token: str,
    pr_title: str,
    pr_body: str,
    base_branch: str = "main",
) -> dict[str, Any]:
    """
    Create a GitHub PR by:
    1. Creating a new branch
    2. Committing changes
    3. Pushing to GitHub
    4. Opening a PR
    
    Returns dict with 'pr_url' on success, or error info on failure.
    """
    repo_info = _extract_repo_info(repo_url)
    if not repo_info:
        return {
            "success": False,
            "error": f"Invalid GitHub repository URL: {repo_url}",
        }
    
    owner, repo = repo_info
    
    # Ensure we're in a git repo
    if not (target_dir / ".git").exists():
        return {
            "success": False,
            "error": "Target directory is not a git repository",
        }
    
    # Create branch and commit changes
    try:
        # Check current branch
        current_branch_proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        original_branch = current_branch_proc.stdout.strip()
        
        # Create new branch
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        
        # Commit changes
        commit_proc = subprocess.run(
            ["git", "commit", "-m", pr_title],
            cwd=target_dir,
            capture_output=True,
            text=True,
        )
        
        if commit_proc.returncode != 0:
            # No changes to commit
            subprocess.run(
                ["git", "checkout", original_branch],
                cwd=target_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=target_dir,
                capture_output=True,
            )
            return {
                "success": False,
                "error": "No changes to commit",
            }
        
        # Push branch to GitHub
        # Configure git to use token for authentication
        remote_url = f"https://{github_token}@github.com/{owner}/{repo}.git"
        
        push_proc = subprocess.run(
            ["git", "push", "-u", remote_url, branch],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if push_proc.returncode != 0:
            # Cleanup: switch back to original branch
            subprocess.run(
                ["git", "checkout", original_branch],
                cwd=target_dir,
                capture_output=True,
            )
            return {
                "success": False,
                "error": f"Failed to push branch: {push_proc.stderr}",
            }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Git operations timed out",
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"Git operation failed: {e.stderr or str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }
    
    # Create PR via GitHub API
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        payload = {
            "title": pr_title,
            "body": pr_body,
            "head": branch,
            "base": base_branch,
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(api_url, headers=headers, json=payload)
            
            if response.status_code == 201:
                pr_data = response.json()
                return {
                    "success": True,
                    "pr_url": pr_data.get("html_url"),
                    "pr_number": pr_data.get("number"),
                    "branch": branch,
                }
            else:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("message", error_msg)
                except Exception:
                    pass
                
                return {
                    "success": False,
                    "error": f"GitHub API error ({response.status_code}): {error_msg}",
                }
    
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "GitHub API request timed out",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create PR: {str(e)}",
        }


def create_pr_from_patch(
    repo_url: str,
    branch_name: str,
    target_dir: Path,
    github_token: str,
    pr_title: str | None = None,
    pr_body: str | None = None,
    base_branch: str = "main",
) -> dict[str, Any]:
    """
    Create a PR from changes already applied to target_dir.
    
    Args:
        repo_url: GitHub repository URL
        branch_name: Name for the new branch
        target_dir: Directory with git repo and changes
        github_token: GitHub personal access token
        pr_title: PR title (defaults to branch name)
        pr_body: PR body (defaults to empty)
        base_branch: Base branch for PR (defaults to "main")
    
    Returns:
        Dict with 'success', 'pr_url' (if successful), or 'error' (if failed)
    """
    if not pr_title:
        pr_title = f"feat: {branch_name}"
    
    if not pr_body:
        pr_body = f"Automated PR created by Growpad\n\nBranch: {branch_name}"
    
    return create_pr(
        repo_url=repo_url,
        branch=branch_name,
        target_dir=target_dir,
        github_token=github_token,
        pr_title=pr_title,
        pr_body=pr_body,
        base_branch=base_branch,
    )

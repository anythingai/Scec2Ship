"""Repository scanner for generating repo-map.md and handoff context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def scan_repository(repo_dir: Path) -> dict[str, Any]:
    """Scan repository to generate structure and metadata.

    Args:
        repo_dir: Path to repository

    Returns:
        Dictionary with repository structure info
    """
    if not repo_dir.exists():
        return {"exists": False, "error": "Repository directory not found"}

    # Detect language/framework
    language = _detect_language(repo_dir)

    # Detect test commands
    test_commands = _detect_test_commands(repo_dir, language)

    # Scan directory structure
    structure = _scan_structure(repo_dir)

    # Find key files
    key_files = _find_key_files(repo_dir)

    return {
        "exists": True,
        "language": language,
        "test_commands": test_commands,
        "structure": structure,
        "key_files": key_files,
        "path": str(repo_dir),
    }


def _detect_language(repo_dir: Path) -> str:
    """Detect programming language from repository files.

    Args:
        repo_dir: Path to repository

    Returns:
        Language name (python, javascript, typescript, go, other)
    """
    language_counts = {}

    # Check for common indicators
    files = list(repo_dir.rglob("*"))
    for file in files:
        if file.is_file():
            suffix = file.suffix.lower()

            if suffix == ".py":
                language_counts["python"] = language_counts.get("python", 0) + 1
            elif suffix in [".js", ".jsx"]:
                language_counts["javascript"] = language_counts.get("javascript", 0) + 1
            elif suffix in [".ts", ".tsx"]:
                language_counts["typescript"] = language_counts.get("typescript", 0) + 1
            elif suffix == ".go":
                language_counts["go"] = language_counts.get("go", 0) + 1

            # Check for package.json
            if file.name == "package.json":
                return "javascript"
            # Check for requirements.txt or pyproject.toml
            if file.name in ["requirements.txt", "pyproject.toml", "setup.py"]:
                return "python"
            # Check for go.mod
            if file.name == "go.mod":
                return "go"

    # Return most common language
    if language_counts:
        return max(language_counts, key=language_counts.get)

    return "other"


def _detect_test_commands(repo_dir: Path, language: str) -> dict[str, str]:
    """Detect test commands based on language.

    Args:
        repo_dir: Path to repository
        language: Detected language

    Returns:
        Dict with test commands
    """
    commands = {}

    if language == "python":
        # Check for pytest
        if (repo_dir / "pytest.ini").exists() or (repo_dir / "pyproject.toml").exists():
            commands["run"] = "pytest"
            commands["with_coverage"] = "pytest --cov=. --cov-report=term-missing"
        # Check for unittest
        elif (repo_dir / "test").exists() or (repo_dir / "tests").exists():
            commands["run"] = "python -m pytest tests/" if (repo_dir / "pytest.ini").exists() else "python -m unittest discover tests/"
        else:
            commands["run"] = "pytest"

    elif language in ["javascript", "typescript"]:
        # Check for package.json scripts
        package_json = repo_dir / "package.json"
        if package_json.exists():
            try:
                package_data = json.loads(package_json.read_text())
                scripts = package_data.get("scripts", {})

                if "test" in scripts:
                    commands["run"] = "npm test"
                if "test:watch" in scripts:
                    commands["watch"] = "npm run test:watch"
                if "test:coverage" in scripts:
                    commands["with_coverage"] = "npm run test:coverage"
                elif "test" in scripts:
                    commands["with_coverage"] = "npm test -- --coverage"

                if not commands:
                    # Default for JS/TS
                    commands["run"] = "npm test"
            except json.JSONDecodeError:
                commands["run"] = "npm test"
        else:
            commands["run"] = "npm test"

    elif language == "go":
        commands["run"] = "go test ./..."
        commands["with_coverage"] = "go test -coverprofile=coverage.out ./..."

    else:
        commands["run"] = "# Add test command for your language"

    return commands


def _scan_structure(repo_dir: Path, max_depth: int = 3) -> dict[str, Any]:
    """Scan repository directory structure.

    Args:
        repo_dir: Path to repository
        max_depth: Maximum directory depth to scan

    Returns:
        Dict with structure info
    """
    structure = {
        "directories": [],
        "test_directories": [],
        "source_directories": [],
        "config_files": [],
    }

    # Directories to skip
    skip_dirs = {
        ".git", ".venv", "venv", "node_modules", "__pycache__",
        ".pytest_cache", "dist", "build", ".next", ".idea",
    }

    for item in repo_dir.iterdir():
        if item.name in skip_dirs or item.name.startswith("."):
            continue

        if item.is_dir():
            structure["directories"].append(item.name)

            # Test directories
            if item.name in ["test", "tests", "__tests__", "spec", "specs"]:
                structure["test_directories"].append(item.name)
            # Source directories
            elif item.name in ["src", "lib", "app", "packages"]:
                structure["source_directories"].append(item.name)
            # Config directories
            elif item.name in ["config", "configs", ".config"]:
                structure["config_directories"] = structure.get("config_directories", [])
                structure["config_directories"].append(item.name)
        elif item.is_file():
            # Config files
            if item.name.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
                structure["config_files"].append(item.name)

    return structure


def _find_key_files(repo_dir: Path) -> dict[str, list[str]]:
    """Find important files in repository.

    Args:
        repo_dir: Path to repository

    Returns:
        Dict with lists of key files by category
    """
    key_files = {
        "documentation": [],
        "configuration": [],
        "build_files": [],
        "license": [],
    }

    for item in repo_dir.glob("*"):
        if item.is_file():
            name = item.name.lower()

            # Documentation
            if name in ["readme.md", "readme.txt", "readme.rst", "docs.md"]:
                key_files["documentation"].append(item.name)

            # Configuration
            elif name.endswith((".json", ".yaml", ".yml", ".toml", ".ini")):
                key_files["configuration"].append(item.name)

            # Build
            elif name in ["makefile", "dockerfile", "docker-compose.yml", "docker-compose.yaml"]:
                key_files["build_files"].append(item.name)

            # License
            elif name.startswith("license"):
                key_files["license"].append(item.name)

    return key_files


def generate_repo_map(repo_info: dict[str, Any], prd_summary: str = "") -> str:
    """Generate repo-map.md content.

    Args:
        repo_info: Repository scan result
        prd_summary: Optional PRD summary for context

    Returns:
        Markdown content for repo-map.md
    """
    if not repo_info.get("exists"):
        return "# Repository Map\n\nError: Repository directory not found.\n"

    language = repo_info.get("language", "unknown")
    test_commands = repo_info.get("test_commands", {})
    structure = repo_info.get("structure", {})
    key_files = repo_info.get("key_files", {})

    lines = [
        "# Repository Map\n",
        "",
        "## Overview\n",
        f"- **Language**: {language.title()}",
        f"- **Path**: `{repo_info['path']}`",
        "",
    ]

    if prd_summary:
        lines.extend([
            "## Feature Context\n",
            "",
            prd_summary,
            "",
        ])

    # Test Commands
    lines.extend([
        "## Test Commands\n",
        "",
    ])

    if test_commands:
        lines.extend([
            f"- **Run tests**: `{test_commands.get('run', 'npm test')}`",
        ])
        if test_commands.get("with_coverage"):
            lines.append(f"- **With coverage**: `{test_commands['with_coverage']}`")
        if test_commands.get("watch"):
            lines.append(f"- **Watch mode**: `{test_commands['watch']}`")
    else:
        lines.append("- No test commands detected. Configure your test framework.")

    lines.append("")

    # Directory Structure
    lines.extend([
        "## Directory Structure\n",
        "",
    ])

    if structure.get("source_directories"):
        lines.append("**Source Code:**")
        for d in structure["source_directories"]:
            lines.append(f"- `/{d}/`")
        lines.append("")

    if structure.get("test_directories"):
        lines.append("**Tests:**")
        for d in structure["test_directories"]:
            lines.append(f"- `/{d}/`")
        lines.append("")

    if structure.get("directories"):
        other_dirs = [d for d in structure["directories"]
                     if d not in (structure.get("source_directories", []) +
                                  structure.get("test_directories", []))]
        if other_dirs:
            lines.append("**Other Directories:**")
            for d in other_dirs[:10]:  # Limit to 10
                lines.append(f"- `/{d}/`")
            lines.append("")

    # Key Files
    if key_files.get("configuration") or key_files.get("build_files"):
        lines.extend([
            "## Configuration & Build\n",
            "",
        ])

        if key_files.get("configuration"):
            lines.append("**Configuration:**")
            for f in key_files["configuration"][:5]:
                lines.append(f"- `{f}`")
            lines.append("")

        if key_files.get("build_files"):
            lines.append("**Build:**")
            for f in key_files["build_files"]:
                lines.append(f"- `{f}`")
            lines.append("")

    # Notes
    lines.extend([
        "## Notes for Cursor/Agents\n",
        "",
        "- This repository has been scanned for automated handoff.",
        "- Use the test commands above to verify changes.",
        "- Focus changes in the source directories listed above.",
        "",
    ])

    return "\n".join(lines)


def generate_handoff(
    repo_info: dict[str, Any],
    prd_summary: str = "",
    tickets_count: int = 0,
    max_retries: int = 2,
) -> str:
    """Generate handoff.md content.

    Args:
        repo_info: Repository scan result
        prd_summary: PRD summary
        tickets_count: Number of tickets generated
        max_retries: Maximum retries allowed

    Returns:
        Markdown content for handoff.md
    """
    if not repo_info.get("exists"):
        return "# Cursor Handoff\n\nError: Repository directory not found.\n"

    language = repo_info.get("language", "unknown")
    test_commands = repo_info.get("test_commands", {})

    lines = [
        "# Cursor Handoff Context",
        "",
        "## Overview",
        "",
        "This handoff package provides context for implementing the feature described in PRD.md.",
        "",
        f"- **Language**: {language.title()}",
        f"- **Tickets to Implement**: {tickets_count}",
        f"- **Max Retries Allowed**: {max_retries}",
        "",
    ]

    # Feature Summary
    if prd_summary:
        lines.extend([
            "## Feature Summary",
            "",
            prd_summary,
            "",
        ])

    # Implementation Constraints
    lines.extend([
        "## Implementation Constraints",
        "",
        "- **Test Coverage**: Must pass all existing tests and add tests for new code.",
        f"- **Retry Limit**: Self-correction limited to {max_retries} retries.",
        "- **Forbidden Paths**: Do not modify infrastructure, payment processing, or security configuration.",
        "- **Code Style**: Follow existing patterns in the repository.",
        "",
    ])

    # Acceptance Criteria
    lines.extend([
        "## Acceptance Criteria",
        "",
        f"1. All {tickets_count} tickets are implemented.",
        "2. All tests pass (`{}` test command).".format(test_commands.get("run", "npm test")),
        "3. Code follows existing patterns and conventions.",
        "4. Feature is ready for code review.",
        "",
    ])

    # Files to Change
    lines.extend([
        "## Files to Modify",
        "",
        "Based on the PRD and tickets, focus changes in these areas:",
        "",
    ])

    structure = repo_info.get("structure", {})
    if structure.get("source_directories"):
        for d in structure["source_directories"]:
            lines.append(f"- Files in `/{d}/` directory")
    if structure.get("test_directories"):
        for d in structure["test_directories"]:
            lines.append(f"- Tests in `/{d}/` directory")

    lines.extend([
        "",
        "## Testing Instructions",
        "",
        "1. Run tests before starting:",
        f"   ```bash",
        f"   {test_commands.get('run', 'npm test')}",
        f"   ```",
        "",
        "2. Implement changes for each ticket.",
        "",
        "3. Run tests after each ticket:",
        f"   ```bash",
        f"   {test_commands.get('run', 'npm test')}",
        f"   ```",
        "",
        "4. Generate final patch with:",
        f"   ```bash",
        f"   git diff > feature.patch",
        f"   ```",
        "",
    ])

    # Cursor Context
    lines.extend([
        "## Cursor Context",
        "",
        "```cursor",
        "# Project Configuration",
        f"language: {language}",
        f"test_command: {test_commands.get('run', 'npm test')}",
        f"max_retries: {max_retries}",
        "",
        "# Implementation Guidelines",
        "- Read PRD.md for full requirements",
        "- Read tickets.json for detailed breakdown",
        "- Apply patches using: git apply diff.patch",
        "- Run tests to verify: " + test_commands.get("run", "npm test"),
        "```",
        "",
    ])

    return "\n".join(lines)

"""Artifact packaging and manifest generation."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Any

from packages.common.io import write_json


def build_manifest(artifacts_dir: Path) -> dict[str, Any]:
    files: list[dict[str, object]] = []
    for item in sorted(artifacts_dir.glob("*")):
        if item.is_file() and item.name != "manifest.json" and item.name != "artifacts.zip":
            checksum = hashlib.sha256(item.read_bytes()).hexdigest()
            files.append({"name": item.name, "sha256": checksum, "size": item.stat().st_size})
    manifest = {"files": files}
    write_json(artifacts_dir / "manifest.json", manifest)
    return manifest


def package_artifacts(artifacts_dir: Path) -> Path:
    build_manifest(artifacts_dir)
    zip_path = artifacts_dir / "artifacts.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(artifacts_dir.glob("*")):
            if item.is_file() and item.name != "artifacts.zip":
                zf.write(item, arcname=item.name)
    return zip_path

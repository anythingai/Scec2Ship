"""Base types and sync logic for live data connectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SyncResult:
    """Result of syncing evidence from an integration provider."""

    provider: str
    records: int
    synced_at: str
    evidence_records: list[dict[str, Any]]
    status: str  # "success" | "partial" | "not_configured" | "error"
    error: str | None = None


def sync_provider(
    provider: str,
    workspace_id: str,
    config: dict[str, Any],
) -> SyncResult:
    """
    Sync evidence from a provider. Uses real adapter implementations.
    Returns actual records; no fake data. Status reflects real outcome.
    """
    from .registry import get_sync_result

    return get_sync_result(provider, workspace_id, config)

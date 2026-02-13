"""Registry of connector adapters. Each adapter performs real API calls when configured."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .base import SyncResult
from .adapters import (
    gong_sync,
    intercom_sync,
    linear_sync,
    posthog_sync,
    slack_sync,
)

CONNECTORS: dict[str, Any] = {
    "gong": gong_sync,
    "intercom": intercom_sync,
    "linear": linear_sync,
    "posthog": posthog_sync,
    "slack": slack_sync,
}


def get_sync_result(
    provider: str,
    workspace_id: str,
    config: dict[str, Any],
) -> SyncResult:
    """
    Call the adapter for provider. Returns real sync result.
    No mocks: status and records reflect actual API outcome.
    """
    adapter = CONNECTORS.get(provider.lower())
    if not adapter:
        return SyncResult(
            provider=provider,
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=f"Unknown provider: {provider}",
        )
    return adapter(workspace_id, config)

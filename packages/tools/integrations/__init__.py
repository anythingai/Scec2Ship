"""Live data connector adapters for Gong, Intercom, Linear, PostHog, Slack."""

from __future__ import annotations

from .base import SyncResult, sync_provider
from .registry import CONNECTORS, get_sync_result

__all__ = ["SyncResult", "sync_provider", "CONNECTORS", "get_sync_result"]

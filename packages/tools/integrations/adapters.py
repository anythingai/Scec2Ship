"""
Live connector adapters. Each performs real API calls when given valid config.
Without config: returns not_configured. No fake success or fake record counts.
"""

from __future__ import annotations

import urllib.request
import urllib.error
import json
from datetime import UTC, datetime
from typing import Any

from .base import SyncResult


def _fetch_api(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch API endpoint. Returns (data, error)."""
    req_headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return (data, None)
    except Exception as e:
        return (None, str(e))


def gong_sync(workspace_id: str, config: dict[str, Any]) -> SyncResult:
    """
    Gong: Fetch call transcripts. Requires api_key or access_token.
    API: https://developers.gong.io/
    """
    api_key = config.get("api_key") or config.get("access_token")
    if not api_key or not str(api_key).strip():
        return SyncResult(
            provider="gong",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="not_configured",
            error="Gong API key required. Set api_key in integration config.",
        )
    # Gong API base - use v2/calls endpoint when available
    base = config.get("api_base", "https://api.gong.io")
    url = f"{base.rstrip('/')}/v2/calls"
    headers = {"Authorization": f"Bearer {api_key}"}
    data, err = _fetch_api(url, headers=headers)
    if err:
        return SyncResult(
            provider="gong",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=err,
        )
    records = []
    if isinstance(data, dict) and "calls" in data and isinstance(data["calls"], list):
        for call in data["calls"][:50]:  # Limit for demo
            records.append({
                "source": "gong",
                "type": "call_transcript",
                "id": call.get("id"),
                "summary": call.get("summary") or call.get("title", ""),
                "created_at": call.get("started", ""),
            })
    return SyncResult(
        provider="gong",
        records=len(records),
        synced_at=datetime.now(UTC).isoformat(),
        evidence_records=records,
        status="success" if records else "partial",
    )


def intercom_sync(workspace_id: str, config: dict[str, Any]) -> SyncResult:
    """
    Intercom: Fetch conversations/tickets. Requires access_token.
    API: https://developers.intercom.com/
    """
    token = config.get("access_token") or config.get("api_key")
    if not token or not str(token).strip():
        return SyncResult(
            provider="intercom",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="not_configured",
            error="Intercom access token required.",
        )
    url = "https://api.intercom.io/conversations?per_page=50"
    headers = {"Authorization": f"Bearer {token}"}
    data, err = _fetch_api(url, headers=headers)
    if err:
        return SyncResult(
            provider="intercom",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=err,
        )
    records = []
    if isinstance(data, dict) and "conversations" in data:
        for c in data.get("conversations", [])[:50]:
            records.append({
                "source": "intercom",
                "type": "conversation",
                "id": c.get("id"),
                "summary": str(c.get("subject") or c.get("summary", ""))[:200],
                "created_at": str(c.get("created_at", "")),
            })
    return SyncResult(
        provider="intercom",
        records=len(records),
        synced_at=datetime.now(UTC).isoformat(),
        evidence_records=records,
        status="success" if records else "partial",
    )


def linear_sync(workspace_id: str, config: dict[str, Any]) -> SyncResult:
    """
    Linear: Fetch issues via GraphQL. Requires api_key.
    API: https://developers.linear.app/
    """
    api_key = config.get("api_key")
    if not api_key or not str(api_key).strip():
        return SyncResult(
            provider="linear",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="not_configured",
            error="Linear API key required.",
        )
    query = """
    query { issues(first: 50) {
      nodes { id title description state { name } createdAt }
    }}
    """
    url = "https://api.linear.app/graphql"
    headers = {"Authorization": api_key}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"query": query}).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return SyncResult(
            provider="linear",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=str(e),
        )
    records = []
    if isinstance(data, dict) and "data" in data and "issues" in data["data"]:
        nodes = data["data"]["issues"].get("nodes", [])
        for n in nodes[:50]:
            records.append({
                "source": "linear",
                "type": "issue",
                "id": n.get("id"),
                "summary": n.get("title", ""),
                "description": (n.get("description") or "")[:500],
                "state": (n.get("state") or {}).get("name"),
                "created_at": n.get("createdAt", ""),
            })
    return SyncResult(
        provider="linear",
        records=len(records),
        synced_at=datetime.now(UTC).isoformat(),
        evidence_records=records,
        status="success" if records else "partial",
    )


def posthog_sync(workspace_id: str, config: dict[str, Any]) -> SyncResult:
    """
    PostHog: Fetch events/insights. Requires api_key and optionally project_id.
    API: https://posthog.com/docs/api
    """
    api_key = config.get("api_key")
    if not api_key or not str(api_key).strip():
        return SyncResult(
            provider="posthog",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="not_configured",
            error="PostHog API key required.",
        )
    project_id = config.get("project_id", "")
    url = f"https://us.i.posthog.com/api/projects/{project_id or 'default'}/insights/?limit=20"
    headers = {"Authorization": f"Bearer {api_key}"}
    data, err = _fetch_api(url, headers=headers)
    if err:
        return SyncResult(
            provider="posthog",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=err,
        )
    records = []
    if isinstance(data, list):
        for r in data[:30]:
            records.append({
                "source": "posthog",
                "type": "insight",
                "summary": str(r.get("name") or r.get("derived_name", ""))[:200],
                "filters": r.get("filters", {}),
            })
    elif isinstance(data, dict) and "results" in data:
        for r in data.get("results", [])[:30]:
            records.append({
                "source": "posthog",
                "type": "insight",
                "summary": str(r.get("name", r))[:200],
            })
    return SyncResult(
        provider="posthog",
        records=len(records),
        synced_at=datetime.now(UTC).isoformat(),
        evidence_records=records,
        status="success" if records else "partial",
    )


def slack_sync(workspace_id: str, config: dict[str, Any]) -> SyncResult:
    """
    Slack: Fetch channel messages. Requires bot_token and channel_id.
    API: https://api.slack.com/methods/conversations.history
    """
    token = config.get("bot_token") or config.get("token") or config.get("api_key")
    channel = config.get("channel_id")
    if not token or not str(token).strip():
        return SyncResult(
            provider="slack",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="not_configured",
            error="Slack bot token required.",
        )
    if not channel:
        return SyncResult(
            provider="slack",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="not_configured",
            error="Slack channel_id required. Add channel to monitor in config.",
        )
    url = f"https://slack.com/api/conversations.history?channel={channel}&limit=50"
    headers = {"Authorization": f"Bearer {token}"}
    data, err = _fetch_api(url, headers=headers)
    if err:
        return SyncResult(
            provider="slack",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=err,
        )
    records = []
    if isinstance(data, dict) and data.get("ok") and "messages" in data:
        for m in data.get("messages", [])[:50]:
            text = m.get("text", "")
            if not text:
                continue
            records.append({
                "source": "slack",
                "type": "message",
                "channel": channel,
                "summary": text[:300],
                "ts": m.get("ts"),
                "user": m.get("user"),
            })
    elif isinstance(data, dict) and not data.get("ok"):
        return SyncResult(
            provider="slack",
            records=0,
            synced_at=datetime.now(UTC).isoformat(),
            evidence_records=[],
            status="error",
            error=data.get("error", "Slack API error"),
        )
    return SyncResult(
        provider="slack",
        records=len(records),
        synced_at=datetime.now(UTC).isoformat(),
        evidence_records=records,
        status="success" if records else "partial",
    )

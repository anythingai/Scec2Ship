"""Gemini tool usage trace recording.

Records all Gemini API calls during a run to provide
audit trail and transparency about model interactions.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class GeminiTraceRecorder:
    """Records Gemini API calls and generates trace file."""

    def __init__(self, run_dir: Path) -> None:
        """Initialize trace recorder for a run.

        Args:
            run_dir: Directory to store trace file
        """
        self.run_dir = run_dir
        self.thought_signature = self._generate_thought_signature()
        self.calls: list[dict[str, Any]] = []
        self.retry_count = 0

    def _generate_thought_signature(self) -> str:
        """Generate unique ThoughtSignature ID for this run."""
        # Simple format: ts-<timestamp>-<short-uuid>
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"ts-{ts}-{short_uuid}"

    def record_call(
        self,
        function: str,
        args_summary: str,
        response_summary: str,
        stage: str | None = None,
        tokens_used: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        """Record a Gemini API call.

        Args:
            function: Name of the function/tool called
            args_summary: Brief summary of arguments
            response_summary: Brief summary of response
            stage: Pipeline stage where call was made
            tokens_used: Approximate token count (if available)
            latency_ms: Call duration in milliseconds
        """
        call_record = {
            "id": f"{self.thought_signature}-{len(self.calls) + 1}",
            "timestamp": datetime.now(UTC).isoformat(),
            "function": function,
            "args_summary": args_summary,
            "response_summary": response_summary,
            "stage": stage,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
        }

        self.calls.append(call_record)

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1

    def set_retry_count(self, count: int) -> None:
        """Set retry count directly."""
        self.retry_count = count

    def get_trace(self) -> dict[str, Any]:
        """Get complete trace as dictionary.

        Returns:
            Dictionary with trace data
        """
        return {
            "thought_signature": self.thought_signature,
            "run_directory": str(self.run_dir),
            "call_count": len(self.calls),
            "retries": self.retry_count,
            "calls": self.calls,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def write_trace(self) -> Path:
        """Write trace to gemini-trace.json file.

        Returns:
            Path to the written trace file
        """
        trace = self.get_trace()
        trace_file = self.run_dir / "artifacts" / "gemini-trace.json"

        # Ensure artifacts directory exists
        trace_file.parent.mkdir(parents=True, exist_ok=True)

        # Write trace with pretty formatting
        trace_file.write_text(json.dumps(trace, indent=2, default=str))

        return trace_file


# Global registry for trace recorders ( keyed by run_id)
_trace_recorders: dict[str, GeminiTraceRecorder] = {}


def get_or_create_recorder(run_id: str, run_dir: Path) -> GeminiTraceRecorder:
    """Get existing recorder or create new one for a run.

    Args:
        run_id: Unique run identifier
        run_dir: Directory for the run

    Returns:
        GeminiTraceRecorder instance
    """
    if run_id not in _trace_recorders:
        _trace_recorders[run_id] = GeminiTraceRecorder(run_dir)
    return _trace_recorders[run_id]


def record_gemini_call(
    run_id: str,
    function: str,
    args_summary: str,
    response_summary: str,
    stage: str | None = None,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
) -> None:
    """Record a Gemini call for the specified run.

    Convenience function for recording calls without direct recorder access.

    Args:
        run_id: Run identifier
        function: Function/tool name
        args_summary: Arguments summary
        response_summary: Response summary
        stage: Pipeline stage
        tokens_used: Token count
        latency_ms: Call duration
    """
    if run_id in _trace_recorders:
        _trace_recorders[run_id].record_call(
            function=function,
            args_summary=args_summary,
            response_summary=response_summary,
            stage=stage,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )


def finalize_trace(run_id: str) -> Path | None:
    """Finalize and write trace for a run.

    Args:
        run_id: Run identifier

    Returns:
        Path to trace file, or None if recorder doesn't exist
    """
    if run_id in _trace_recorders:
        recorder = _trace_recorders[run_id]
        trace_path = recorder.write_trace()
        # Clean up registry
        del _trace_recorders[run_id]
        return trace_path
    return None


def clear_recorder(run_id: str) -> None:
    """Remove recorder for a run without writing trace.

    Args:
        run_id: Run identifier
    """
    if run_id in _trace_recorders:
        del _trace_recorders[run_id]


def validate_trace(trace_path: Path) -> bool:
    """Validate a trace file has required fields.

    Args:
        trace_path: Path to gemini-trace.json

    Returns:
        True if valid, False otherwise
    """
    try:
        trace = json.loads(trace_path.read_text())

        # Check required top-level fields
        required_fields = ["thought_signature", "calls", "retries"]
        if not all(field in trace for field in required_fields):
            return False

        # Validate thought_signature format
        if not trace["thought_signature"].startswith("ts-"):
            return False

        # Check calls structure
        calls = trace.get("calls", [])
        for call in calls:
            if not all(key in call for key in ["function", "args_summary", "response_summary"]):
                return False

        return True
    except (json.JSONDecodeError, FileNotFoundError, TypeError):
        return False


def get_trace_summary(trace_path: Path) -> dict[str, Any]:
    """Get summary of trace file.

    Args:
        trace_path: Path to gemini-trace.json

    Returns:
        Dictionary with trace summary
    """
    trace = json.loads(trace_path.read_text())
    calls = trace.get("calls", [])

    # Count calls by function
    function_counts: dict[str, int] = {}
    for call in calls:
        func = call.get("function", "unknown")
        function_counts[func] = function_counts.get(func, 0) + 1

    # Calculate total latency
    total_latency = sum(call.get("latency_ms", 0) or 0 for call in calls)

    # Count stages
    stages = set(call.get("stage") for call in calls if call.get("stage"))

    return {
        "thought_signature": trace.get("thought_signature"),
        "total_calls": len(calls),
        "retries": trace.get("retries", 0),
        "function_counts": function_counts,
        "total_latency_ms": total_latency,
        "stages_touched": sorted(stages),
        "generated_at": trace.get("generated_at"),
    }

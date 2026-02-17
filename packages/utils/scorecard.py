"""Verification scorecard calculation and generation.

Computes quality metrics for a run including:
- Evidence coverage %
- Test pass rate
- Forbidden path check
- Retry analysis
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Thresholds for passing/failing
THRESHOLDS = {
    "evidence_coverage": 0.70,  # 70% minimum evidence coverage
    "test_pass_rate": 0.80,     # 80% minimum test pass rate
    "max_retries": 2,           # Maximum allowed retries
}


class ScorecardCalculator:
    """Calculates verification scorecard metrics."""

    def __init__(
        self,
        run_dir: Path,
        test_report_path: Path | None = None,
        evidence_map_path: Path | None = None,
    ) -> None:
        """Initialize scorecard calculator.

        Args:
            run_dir: Run directory containing artifacts
            test_report_path: Path to test report (optional)
            evidence_map_path: Path to evidence map (optional)
        """
        self.run_dir = run_dir
        self.test_report_path = test_report_path or (run_dir / "test-report.md")
        self.evidence_map_path = evidence_map_path or (run_dir / "evidence-map.json")

    def calculate(self) -> dict[str, Any]:
        """Calculate all scorecard metrics.

        Returns:
            Dictionary with scorecard data
        """
        metrics = {
            "evidence_coverage": self._calculate_evidence_coverage(),
            "test_pass_rate": self._calculate_test_pass_rate(),
            "forbidden_path_check": self._check_forbidden_paths(),
            "retry_analysis": self._analyze_retries(),
        }

        # Determine overall status
        metrics["overall_status"] = self._determine_status(metrics)
        metrics["passing_thresholds"] = {
            k: metrics[k] >= v if isinstance(v, float) else metrics[k] <= v
            for k, v in THRESHOLDS.items()
            if k in metrics
        }

        return metrics

    def _calculate_evidence_coverage(self) -> float:
        """Calculate evidence coverage percentage.

        Returns:
            Coverage as float between 0.0 and 1.0
        """
        try:
            if not self.evidence_map_path.exists():
                return 0.0

            evidence_map = json.loads(self.evidence_map_path.read_text())

            # Count linked claims and total claims
            claims = evidence_map.get("claims", [])
            if not claims:
                return 0.0

            linked_claims = sum(1 for claim in claims if claim.get("linked_claim_ids"))

            if not claims:
                return 0.0

            return linked_claims / len(claims)

        except (json.JSONDecodeError, FileNotFoundError, TypeError):
            return 0.0

    def _calculate_test_pass_rate(self) -> float:
        """Calculate test pass rate from test report.

        Returns:
            Pass rate as float between 0.0 and 1.0
        """
        try:
            if not self.test_report_path.exists():
                return 0.0

            report_text = self.test_report_path.read_text()

            # Parse test report for pass/fail counts
            # Common formats: "X passed, Y failed", "PASSED: X, FAILED: Y"
            import re

            # Look for patterns
            patterns = [
                r"(\d+)\s+passed(?:,\s*(\d+)\s+failed)?",
                r"PASSED:\s*(\d+)",
                r"passed:\s*(\d+)",
            ]

            passed = 0
            failed = 0

            for pattern in patterns:
                matches = re.findall(pattern, report_text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            passed = int(match[0]) if match[0].isdigit() else 0
                            failed = int(match[1]) if len(match) > 1 and match[1].isdigit() else 0
                        else:
                            passed = int(match) if match.isdigit() else 0

                    break

            total = passed + failed
            if total == 0:
                # Default to pass if no failures found
                return 1.0 if "failed" not in report_text.lower() else 0.0

            return passed / total

        except (FileNotFoundError, ValueError):
            return 0.0

    def _check_forbidden_paths(self) -> dict[str, Any]:
        """Check if any forbidden paths were touched.

        Returns:
            Dict with forbidden path check results
        """
        # Check diff.patch for forbidden paths
        diff_path = self.run_dir / "diff.patch"
        forbidden_paths = ["/infra", "/payments", "/config", "/secrets"]

        result = {
            "checked": False,
            "violations": [],
            "forbidden_paths": forbidden_paths,
        }

        if not diff_path.exists():
            return result

        try:
            diff_content = diff_path.read_text()
            result["checked"] = True

            violations = []
            for path in forbidden_paths:
                if path in diff_content or path.replace("/", "") in diff_content:
                    violations.append(path)

            result["violations"] = violations
            result["clean"] = len(violations) == 0

        except FileNotFoundError:
            pass

        return result

    def _analyze_retries(self) -> dict[str, Any]:
        """Analyze retry usage.

        Returns:
            Dict with retry analysis
        """
        # Check audit-trail.json for retry information
        audit_path = self.run_dir / "audit-trail.json"

        result = {
            "retry_count": 0,
            "max_allowed": THRESHOLDS["max_retries"],
            "within_limit": True,
        }

        if not audit_path.exists():
            return result

        try:
            audit = json.loads(audit_path.read_text())
            result["retry_count"] = audit.get("retries_used", 0)
            result["within_limit"] = result["retry_count"] <= result["max_allowed"]

        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass

        return result

    def _determine_status(self, metrics: dict[str, Any]) -> str:
        """Determine overall verification status.

        Args:
            metrics: Calculated metrics

        Returns:
            "PASS", "FAIL", or "WARNING"
        """
        # Critical failures
        if metrics.get("test_pass_rate", 0) < THRESHOLDS["test_pass_rate"]:
            return "FAIL"

        if metrics.get("forbidden_path_check", {}).get("violations"):
            return "FAIL"

        # Warnings
        if metrics.get("evidence_coverage", 0) < THRESHOLDS["evidence_coverage"]:
            return "WARNING"

        if not metrics.get("retry_analysis", {}).get("within_limit", True):
            return "WARNING"

        # All good
        return "PASS"


def generate_scorecard(
    run_dir: Path,
    retry_count: int = 0,
    test_exit_code: int = 0,
) -> dict[str, Any]:
    """Generate complete scorecard for a run.

    Args:
        run_dir: Run directory
        retry_count: Number of retries used
        test_exit_code: Exit code from test run

    Returns:
        Complete scorecard dictionary
    """
    calculator = ScorecardCalculator(run_dir)
    metrics = calculator.calculate()

    # Override test pass rate with actual exit code if available
    if test_exit_code == 0:
        metrics["test_pass_rate"] = 1.0
        metrics["test_exit_code"] = test_exit_code
    elif test_exit_code != 0:
        metrics["test_pass_rate"] = 0.0
        metrics["test_exit_code"] = test_exit_code

    # Override retry count
    metrics["retry_analysis"]["retry_count"] = retry_count
    metrics["retry_analysis"]["within_limit"] = retry_count <= THRESHOLDS["max_retries"]

    # Re-determine status
    metrics["overall_status"] = calculator._determine_status(metrics)

    # Add summary text
    metrics["summary"] = _generate_summary(metrics)

    return metrics


def _generate_summary(metrics: dict[str, Any]) -> str:
    """Generate human-readable summary.

    Args:
        metrics: Scorecard metrics

    Returns:
        Summary text
    """
    status = metrics.get("overall_status", "UNKNOWN")

    if status == "PASS":
        summary = "✅ Verification: PASS"
    elif status == "FAIL":
        summary = "❌ Verification: FAIL"
    else:
        summary = "⚠️ Verification: WARNING"

    parts = []

    # Evidence coverage
    coverage = metrics.get("evidence_coverage", 0) * 100
    parts.append(f"Coverage: {coverage:.0f}%")

    # Test pass rate
    pass_rate = metrics.get("test_pass_rate", 0) * 100
    parts.append(f"Tests: {pass_rate:.0f}%")

    # Retries
    retry_count = metrics.get("retry_analysis", {}).get("retry_count", 0)
    parts.append(f"Retries: {retry_count}/2")

    return f"{summary} ({', '.join(parts)})"


def write_scorecard(scorecard: dict[str, Any], output_path: Path) -> Path:
    """Write scorecard to JSON file.

    Args:
        scorecard: Scorecard data
        output_path: Path to write scorecard.json

    Returns:
        Path to written file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scorecard, indent=2, default=str))
    return output_path

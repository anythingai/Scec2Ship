from pathlib import Path

from packages.tools.evidence import validate_evidence_bundle


def test_sample_evidence_is_valid() -> None:
    sample = Path("sample-data/evidence")
    result = validate_evidence_bundle(sample)
    assert result.valid is True
    assert result.quality_score >= 90

from pathlib import Path

from packages.common.paths import SAMPLE_EVIDENCE_DIR
from packages.tools.evidence import validate_evidence_bundle


def test_sample_evidence_is_valid() -> None:
    sample = SAMPLE_EVIDENCE_DIR
    result = validate_evidence_bundle(sample)
    assert result.valid is True
    assert result.quality_score >= 90

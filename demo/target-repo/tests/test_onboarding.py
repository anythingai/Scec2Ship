"""Deterministic tests that enforce fail -> self-heal -> pass behavior."""

from demo_app.feature_flags import onboarding_score


def test_onboarding_score_target() -> None:
    assert onboarding_score(50) == 60

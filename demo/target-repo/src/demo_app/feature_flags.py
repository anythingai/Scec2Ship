"""Feature flags for deterministic verification demo."""

BOOST_POINTS = 0


def onboarding_score(base_score: int) -> int:
    return base_score + BOOST_POINTS

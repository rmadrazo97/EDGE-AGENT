"""Basic packaging smoke test for the initial repository skeleton."""

import agents
import clients
import policy
import shared
import strategies


def test_top_level_packages_are_importable() -> None:
    assert agents is not None
    assert clients is not None
    assert policy is not None
    assert shared is not None
    assert strategies is not None

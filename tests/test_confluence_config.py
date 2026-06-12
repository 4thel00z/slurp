"""ConfluenceSettings surface."""

from slurp.domain.settings import ConfluenceSettings


def test_no_random_selection_field():
    cfg = ConfluenceSettings(username="u", api_key="k", space="s")
    assert not hasattr(cfg, "random_selection")

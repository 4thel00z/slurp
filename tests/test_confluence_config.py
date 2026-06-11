"""ConfluenceConfig CLI surface."""

from slurp.domain.config import ConfluenceConfig


def test_no_random_selection_field():
    cfg = ConfluenceConfig(username="u", api_key="k", space="s")
    assert not hasattr(cfg, "random_selection")

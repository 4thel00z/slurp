"""ConfluenceProducer error handling and resource cleanup."""

import logging

from slurp.adapters.producers.confluence import ConfluenceProducer
from slurp.domain.config import ConfluenceConfig
from slurp.domain.config import GeneratorConfig


def _producer():
    p = ConfluenceProducer.__new__(ConfluenceProducer)
    p.config = ConfluenceConfig(username="u", api_key="k", space="s")
    p.generator_config = GeneratorConfig(language="en", model="m")
    p.client = None
    return p


def test_fetch_page_returns_empty_on_client_error(caplog):
    p = _producer()

    class Boom:
        def get_all_pages_from_space_raw(self, **_):
            raise RuntimeError("network down")

    p.client = Boom()
    with caplog.at_level(logging.WARNING):
        assert p.fetch_page(0, 10) == []
    assert "network down" in caplog.text

"""Instrumentation setup is a no-op without a token."""

import logging

from slurp.adapters.instrumentation import setup_instrumentation


def test_no_token_is_noop(caplog):
    with caplog.at_level(logging.INFO):
        setup_instrumentation("")  # must not raise, must not configure logfire
    assert "skipping instrumentation" in caplog.text.lower()

"""AppConfig validation aggregates and fails fast."""

import pytest

from slurp.domain.config import AppConfig
from slurp.domain.config import ConfluenceConfig
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import KafkaConfig
from slurp.domain.config import LocalConfig
from slurp.domain.config import SQLiteConfig
from slurp.domain.config import TokenConfig
from slurp.domain.validation import ConfigError
from slurp.domain.validation import validate_app_config


def _app_config(**overrides):
    base = {
        "token": TokenConfig(api_key="x"),
        "instrumentation": None,
        "confluence": ConfluenceConfig(username="u", api_key="k", space="s"),
        "kafka": KafkaConfig(),
        "generator": GeneratorConfig(language="en", model="m"),
        "sqlite": SQLiteConfig(database="./x.db"),
        "local": LocalConfig(path="./docs"),
        "connector": "local",
    }
    base.update(overrides)
    return AppConfig(**base)


def test_valid_config_passes():
    validate_app_config(_app_config())  # no raise


def test_missing_token_when_generator_enabled():
    with pytest.raises(ConfigError) as ei:
        validate_app_config(_app_config(token=None))
    assert "token" in str(ei.value).lower()


def test_token_not_required_when_generator_disabled():
    cfg = _app_config(
        token=None, generator=GeneratorConfig(language="en", model="m", enabled=False)
    )
    validate_app_config(cfg)  # no raise


def test_confluence_connector_requires_credentials():
    cfg = _app_config(
        connector="confluence",
        confluence=ConfluenceConfig(username="", api_key="", space=""),
    )
    with pytest.raises(ConfigError) as ei:
        validate_app_config(cfg)
    msg = str(ei.value).lower()
    assert "username" in msg and "api" in msg and "space" in msg


def test_out_of_bounds_values_aggregate():
    cfg = _app_config(
        generator=GeneratorConfig(
            language="en", model="m", concurrency=0, temperature=5.0, max_tokens=0, batch_size=0
        ),
    )
    with pytest.raises(ConfigError) as ei:
        validate_app_config(cfg)
    msg = str(ei.value)
    assert (
        "concurrency" in msg
        and "temperature" in msg
        and "max_tokens" in msg
        and "batch_size" in msg
    )

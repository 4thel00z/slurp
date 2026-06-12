"""Section settings: env prefix, legacy aliases, bounds, cross-field."""

import pytest
from pydantic import ValidationError

from slurp.domain.settings import AppSettings
from slurp.domain.settings import ConfluenceSettings
from slurp.domain.settings import GeneratorSettings
from slurp.domain.settings import InstrumentationSettings
from slurp.domain.settings import KafkaSettings
from slurp.domain.settings import LocalSettings
from slurp.domain.settings import SQLiteSettings
from slurp.domain.settings import TokenSettings


def test_kafka_reads_slurp_prefixed_env(monkeypatch):
    monkeypatch.setenv("SLURP_KAFKA_TOPIC", "newtopic")
    assert KafkaSettings().topic == "newtopic"


def test_kafka_reads_legacy_env(monkeypatch):
    monkeypatch.delenv("SLURP_KAFKA_TOPIC", raising=False)
    monkeypatch.setenv("KAFKA_TOPIC", "legacytopic")
    assert KafkaSettings().topic == "legacytopic"


def test_slurp_prefixed_wins_over_legacy(monkeypatch):
    monkeypatch.setenv("SLURP_KAFKA_TOPIC", "new")
    monkeypatch.setenv("KAFKA_TOPIC", "old")
    assert KafkaSettings().topic == "new"


def test_token_reads_aliases(monkeypatch):
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    assert TokenSettings().api_key == "or-key"


def test_generator_model_env_is_new_coverage(monkeypatch):
    monkeypatch.setenv("SLURP_GENERATOR_MODEL", "envmodel")
    assert GeneratorSettings().model == "envmodel"


def test_confluence_space_env(monkeypatch):
    monkeypatch.setenv("SLURP_CONFLUENCE_SPACE", "ENG")
    assert ConfluenceSettings().space == "ENG"


def test_local_extension_list():
    s = LocalSettings(extensions=".md, .HTML ,.txt")
    assert s.extension_list() == [".md", ".html", ".txt"]


def test_generator_bounds_reject():
    with pytest.raises(ValidationError):
        GeneratorSettings(concurrency=0)
    with pytest.raises(ValidationError):
        GeneratorSettings(temperature=5.0)
    with pytest.raises(ValidationError):
        GeneratorSettings(max_tokens=0)
    with pytest.raises(ValidationError):
        GeneratorSettings(batch_size=0)


def test_sqlite_default_database():
    assert SQLiteSettings().database == "./data.db"


def _app(**over):
    base = {
        "token": TokenSettings(api_key="x"),
        "instrumentation": InstrumentationSettings(),
        "confluence": ConfluenceSettings(username="u", api_key="k", space="s"),
        "kafka": KafkaSettings(),
        "generator": GeneratorSettings(),
        "sqlite": SQLiteSettings(),
        "local": LocalSettings(),
        "connector": "local",
    }
    base.update(over)
    return AppSettings(**base)


def _clear_token_env(monkeypatch):
    for var in ("SLURP_LLM_API_KEY", "LLM_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def _clear_confluence_env(monkeypatch):
    for var in (
        "SLURP_CONFLUENCE_USERNAME",
        "CONFLUENCE_USERNAME",
        "SLURP_CONFLUENCE_API_KEY",
        "CONFLUENCE_API_KEY",
        "SLURP_CONFLUENCE_SPACE",
    ):
        monkeypatch.delenv(var, raising=False)


def test_cross_field_token_required_when_generator_enabled(monkeypatch):
    _clear_token_env(monkeypatch)
    with pytest.raises(ValidationError):
        _app(token=TokenSettings(api_key=None))


def test_cross_field_token_not_required_when_disabled(monkeypatch):
    _clear_token_env(monkeypatch)
    _app(token=TokenSettings(api_key=None), generator=GeneratorSettings(enabled=False))


def test_cross_field_confluence_requires_credentials(monkeypatch):
    _clear_confluence_env(monkeypatch)
    with pytest.raises(ValidationError):
        _app(connector="confluence", confluence=ConfluenceSettings())

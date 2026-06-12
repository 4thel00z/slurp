"""load_settings: precedence and fail-fast ConfigError."""

import pytest

from slurp.domain.config import load_settings
from slurp.domain.config import load_sqlite_settings
from slurp.domain.validation import ConfigError


def _argv(*extra):
    return ["slurp", "worker", "--connector", "local", *extra]


def test_cli_flag_beats_env(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "tok")
    monkeypatch.setenv("SLURP_GENERATOR_MODEL", "envmodel")
    s = load_settings(_argv("--generator-model", "climodel"))
    assert s.generator.model == "climodel"


def test_cli_flag_beats_env_for_aliased_field(monkeypatch):
    # kafka.topic uses validation_alias (AliasChoices); the CLI must still win over env.
    monkeypatch.setenv("SLURP_LLM_API_KEY", "tok")
    monkeypatch.setenv("SLURP_KAFKA_TOPIC", "envtopic")
    s = load_settings(_argv("--kafka-topic", "clitopic"))
    assert s.kafka.topic == "clitopic"


def test_env_used_when_no_flag(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "tok")
    monkeypatch.setenv("SLURP_GENERATOR_MODEL", "envmodel")
    s = load_settings(_argv())
    assert s.generator.model == "envmodel"


def test_default_when_neither(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "tok")
    monkeypatch.delenv("SLURP_GENERATOR_MODEL", raising=False)
    s = load_settings(_argv())
    assert s.generator.model.startswith("google/")


def test_missing_token_raises_configerror(monkeypatch):
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigError) as ei:
        load_settings(_argv())
    assert "token" in str(ei.value).lower()


def test_out_of_bounds_raises_configerror(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "tok")
    monkeypatch.setenv("SLURP_GENERATOR_CONCURRENCY", "0")
    with pytest.raises(ConfigError):
        load_settings(_argv())


def test_confluence_connector_requires_creds(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "tok")
    for var in (
        "SLURP_CONFLUENCE_USERNAME",
        "CONFLUENCE_USERNAME",
        "SLURP_CONFLUENCE_API_KEY",
        "CONFLUENCE_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ConfigError) as ei:
        load_settings(["slurp", "scraper", "--connector", "confluence"])
    msg = str(ei.value).lower()
    assert "username" in msg and "api" in msg


def test_load_sqlite_settings_cli_override():
    s = load_sqlite_settings(["slurp", "render", "--sqlite-database", "/tmp/x.db"])
    assert s.database == "/tmp/x.db"


def test_legacy_class_names_reexported(monkeypatch):
    for var in (
        "SLURP_LLM_API_KEY",
        "LLM_API_KEY",
        "OPENROUTER_API_KEY",
        "SLURP_KAFKA_TOPIC",
        "KAFKA_TOPIC",
        "SLURP_SQLITE_DATABASE",
        "SQLITE_DATABASE",
    ):
        monkeypatch.delenv(var, raising=False)
    from slurp.domain.config import ConfluenceConfig
    from slurp.domain.config import GeneratorConfig
    from slurp.domain.config import KafkaConfig
    from slurp.domain.config import SQLiteConfig
    from slurp.domain.config import TokenConfig
    from slurp.domain.settings import ConfluenceSettings

    assert ConfluenceConfig is ConfluenceSettings
    assert TokenConfig(api_key="x").api_key == "x"
    assert GeneratorConfig().concurrency == 5
    assert KafkaConfig().topic == "tasks"
    assert SQLiteConfig().database == "./data.db"

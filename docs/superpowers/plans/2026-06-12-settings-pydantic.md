# Pydantic-Settings Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-rolled argparse+getenv config with a typed, validated pydantic-settings layer where every setting has a CLI flag and a `SLURP_`-prefixed env var (legacy names kept as aliases), plus `.env` loading.

**Architecture:** New `slurp/domain/settings.py` holds one `BaseSettings` per config section plus a top-level `AppSettings` (BaseModel) with a cross-field validator. `slurp/domain/config.py` is rewritten to hold the argparse parser (namespaced dests, `None` defaults) and a `load_settings(argv)` builder applying precedence CLI > env > .env > default, re-raising pydantic `ValidationError` as the existing `ConfigError`. Section attribute names are preserved and the legacy class names (`ConfluenceConfig`, …) are re-exported, so adapters and most tests need no changes.

**Tech Stack:** Python 3.12, pydantic v2, pydantic-settings 2.11, argparse, pytest.

---

## Conventions for every task

- **Run tests with:** `.venv/bin/python -m pytest tests/ -q` (plain `python -m pytest` is hook-intercepted and collects nothing).
- **Commit with:** `git commit --no-verify -m "..."` (pre-commit framework not installed in venv).
- **Lint:** `ruff check slurp/ tests/` and `ruff format slurp/ tests/` (`ruff` is the system binary, not in venv).
- Baseline before starting: `.venv/bin/python -m pytest tests/ -q` → **61 passed**.
- Work on a branch off `main` (the controller creates it).

---

## Task 1: Declare the pydantic-settings dependency

**Files:**
- Modify: `pyproject.toml` (the `dependencies` list)

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add to the `dependencies = [...]` list (after the `pydantic-ai` line):

```toml
    "pydantic-settings>=2.0.0",
```

- [ ] **Step 2: Sync and confirm import**

Run: `uv sync 2>&1 | tail -3` then `.venv/bin/python -c "import pydantic_settings; print(pydantic_settings.__version__)"`
Expected: prints a version (≥ 2.0). (It is already installed transitively; this just declares it.)

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit --no-verify -m "build: declare pydantic-settings dependency"
```

---

## Task 2: Create the settings models

**Files:**
- Create: `slurp/domain/settings.py`
- Test: `tests/test_settings_models.py`

**Context:** `ConfigError` already exists in `slurp/domain/validation.py` as `class ConfigError(ValueError)`. Section attribute names match what adapters already read (`base_url`, `model`, `bootstrap_servers`, `api_key`, `database`, `timeout`, `path`, `extensions`, …). Fields with a legacy env name use `AliasChoices(new, legacy)` (when `validation_alias` is set, `env_prefix` is ignored, so the new name is spelled out). `populate_by_name=True` lets construction by field-name kwargs work (needed by tests and the CLI-override path). `GeneratorSettings` needs `protected_namespaces=()` because it has a field literally named `model`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settings_models.py`:

```python
"""Section settings: env prefix, legacy aliases, bounds, cross-field."""

import pytest
from pydantic import ValidationError

from slurp.domain.settings import AppSettings
from slurp.domain.settings import ConfluenceSettings
from slurp.domain.settings import GeneratorSettings
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
    base = dict(
        token=TokenSettings(api_key="x"),
        instrumentation=None,
        confluence=ConfluenceSettings(username="u", api_key="k", space="s"),
        kafka=KafkaSettings(),
        generator=GeneratorSettings(),
        sqlite=SQLiteSettings(),
        local=LocalSettings(),
        connector="local",
    )
    base.update(over)
    from slurp.domain.settings import InstrumentationSettings

    base["instrumentation"] = InstrumentationSettings()
    return AppSettings(**base)


def test_cross_field_token_required_when_generator_enabled():
    with pytest.raises(ValidationError):
        _app(token=TokenSettings(api_key=None))


def test_cross_field_token_not_required_when_disabled():
    _app(token=TokenSettings(api_key=None), generator=GeneratorSettings(enabled=False))


def test_cross_field_confluence_requires_credentials():
    with pytest.raises(ValidationError):
        _app(connector="confluence", confluence=ConfluenceSettings())
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_settings_models.py -q`
Expected: FAIL — `slurp.domain.settings` does not exist.

- [ ] **Step 3: Create `slurp/domain/settings.py`**

```python
"""Typed, validated application settings (pydantic-settings).

Every setting is available as a CLI flag and an environment variable. Env vars
use a unified ``SLURP_`` prefix; the previous names are kept as aliases for
backward compatibility. A ``.env`` file in the working directory is loaded
automatically. Section attribute names match what the adapters read, so the
adapters consume these models unchanged.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

_ENV = dict(env_file=".env", extra="ignore", populate_by_name=True, env_ignore_empty=True)


class TokenSettings(BaseSettings):
    model_config = SettingsConfigDict(**_ENV)

    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SLURP_LLM_API_KEY", "LLM_API_KEY", "OPENROUTER_API_KEY"),
    )


class InstrumentationSettings(BaseSettings):
    model_config = SettingsConfigDict(**_ENV)

    logfire_token: str = Field(
        default="",
        validation_alias=AliasChoices("SLURP_LOGFIRE_TOKEN", "LOGFIRE_TOKEN"),
    )


class KafkaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLURP_KAFKA_", **_ENV)

    bootstrap_servers: str = Field(
        default="localhost:19092",
        validation_alias=AliasChoices("SLURP_KAFKA_BOOTSTRAP_SERVERS", "KAFKA_BOOTSTRAP_SERVERS"),
    )
    topic: str = Field(
        default="tasks",
        validation_alias=AliasChoices("SLURP_KAFKA_TOPIC", "KAFKA_TOPIC"),
    )
    client_id: str = Field(
        default="slurp",
        validation_alias=AliasChoices("SLURP_KAFKA_CLIENT_ID", "KAFKA_CLIENT_ID"),
    )


class SQLiteSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLURP_SQLITE_", **_ENV)

    database: str = Field(
        default="./data.db",
        validation_alias=AliasChoices("SLURP_SQLITE_DATABASE", "SQLITE_DATABASE"),
    )
    timeout: float = Field(
        default=5.0,
        gt=0,
        validation_alias=AliasChoices("SLURP_SQLITE_TIMEOUT", "SQLITE_TIMEOUT"),
    )


class LocalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLURP_LOCAL_", **_ENV)

    path: str = Field(default="", validation_alias=AliasChoices("SLURP_LOCAL_PATH", "LOCAL_PATH"))
    glob: str = Field(
        default="**/*", validation_alias=AliasChoices("SLURP_LOCAL_GLOB", "LOCAL_GLOB")
    )
    extensions: str = Field(
        default=".md,.html,.txt",
        validation_alias=AliasChoices("SLURP_LOCAL_EXTENSIONS", "LOCAL_EXTENSIONS"),
    )

    def extension_list(self) -> list[str]:
        return [e.strip().lower() for e in self.extensions.split(",") if e.strip()]


class ConfluenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLURP_CONFLUENCE_", **_ENV)

    username: str = Field(
        default="", validation_alias=AliasChoices("SLURP_CONFLUENCE_USERNAME", "CONFLUENCE_USERNAME")
    )
    api_key: str = Field(
        default="", validation_alias=AliasChoices("SLURP_CONFLUENCE_API_KEY", "CONFLUENCE_API_KEY")
    )
    base_url: str = Field(
        default="https://aleph-alpha.atlassian.net",
        validation_alias=AliasChoices("SLURP_CONFLUENCE_BASE_URL", "CONFLUENCE_BASE_URL"),
    )
    space: str = ""
    cloud: bool = True
    months_back: int = Field(default=0, ge=0)
    concurrency: int = Field(default=4, gt=0)
    max_pages: int = Field(default=50, ge=0)
    page_batch_size: int = Field(default=50, gt=0)
    skip: int = Field(default=0, ge=0)
    enabled: bool = True


class GeneratorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SLURP_GENERATOR_", protected_namespaces=(), **_ENV
    )

    language: Literal["de", "en"] = "de"
    model: str = "google/gemini-2.5-flash-preview-05-20"
    max_tokens: int = Field(default=4096, gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    base_url: str = "https://openrouter.ai/api/v1"
    difficulty_ratio: Literal["easy", "medium", "hard", "mixed", "balanced"] = "mixed"
    concurrency: int = Field(default=5, gt=0)
    is_short: bool = True
    batch_size: int = Field(default=1, ge=1)
    enabled: bool = True


class AppSettings(BaseModel):
    token: TokenSettings
    instrumentation: InstrumentationSettings
    confluence: ConfluenceSettings
    kafka: KafkaSettings
    generator: GeneratorSettings
    sqlite: SQLiteSettings
    local: LocalSettings
    connector: Literal["local", "confluence"] = "local"

    @model_validator(mode="after")
    def _check_cross_field(self) -> "AppSettings":
        problems: list[str] = []
        if self.generator.enabled and not self.token.api_key:
            problems.append(
                "LLM token required when the generator is enabled "
                "(set SLURP_LLM_API_KEY / LLM_API_KEY / OPENROUTER_API_KEY, "
                "or pass --generator-disabled)."
            )
        if self.connector == "confluence":
            c = self.confluence
            if not c.base_url:
                problems.append("Confluence base_url is required (SLURP_CONFLUENCE_BASE_URL).")
            if not c.username:
                problems.append("Confluence username is required (SLURP_CONFLUENCE_USERNAME).")
            if not c.api_key:
                problems.append("Confluence api_key is required (SLURP_CONFLUENCE_API_KEY).")
            if not c.space:
                problems.append(
                    "Confluence space is required (--confluence-space / SLURP_CONFLUENCE_SPACE)."
                )
        if problems:
            raise ValueError("Invalid configuration:\n  - " + "\n  - ".join(problems))
        return self
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_settings_models.py -q`
Expected: all pass. (If `test_kafka_reads_slurp_prefixed_env` fails because an unrelated `SLURP_KAFKA_*` is set in your shell, that's environment leakage — the monkeypatch sets it explicitly, so it should pass.)

- [ ] **Step 5: Lint + commit**

```bash
ruff check slurp/ tests/ && ruff format slurp/ tests/
git add slurp/domain/settings.py tests/test_settings_models.py
git commit --no-verify -m "feat(settings): pydantic-settings models with SLURP_ env + legacy aliases"
```

---

## Task 3: Rewrite `config.py` — parser + `load_settings`

**Files:**
- Modify: `slurp/domain/config.py` (full rewrite)
- Test: `tests/test_settings_loader.py`

**Context:** `config.py` becomes the CLI/loader module. It builds argparse with **namespaced dests** (e.g. `generator_model`, `confluence_space`) all defaulting to `None`, collects only the set ones as overrides, constructs each section settings (which load env/.env for the rest), builds `AppSettings`, and converts any pydantic `ValidationError` into `ConfigError`. It re-exports the legacy class names so adapters' imports keep working. `__main__.py` imports `create_cli_parser` from here — keep that name and the subcommand structure.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settings_loader.py`:

```python
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
    for var in ("SLURP_CONFLUENCE_USERNAME", "CONFLUENCE_USERNAME",
                "SLURP_CONFLUENCE_API_KEY", "CONFLUENCE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ConfigError) as ei:
        load_settings(["slurp", "scraper", "--connector", "confluence"])
    msg = str(ei.value).lower()
    assert "username" in msg and "api" in msg


def test_load_sqlite_settings_cli_override():
    s = load_sqlite_settings(["slurp", "render", "--sqlite-database", "/tmp/x.db"])
    assert s.database == "/tmp/x.db"


def test_legacy_class_names_reexported():
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_settings_loader.py -q`
Expected: FAIL — `load_settings` / `load_sqlite_settings` don't exist yet.

- [ ] **Step 3: Rewrite `slurp/domain/config.py`**

Replace the ENTIRE file with:

```python
"""CLI parser and settings loader.

Builds the argparse surface (subcommands + flags), then loads validated
``AppSettings`` applying precedence CLI flag > env var > .env > default. Every
flag defaults to ``None`` so unset flags never mask environment variables.
"""

import argparse
import os
import sys

from pydantic import ValidationError

from slurp.domain.settings import AppSettings
from slurp.domain.settings import ConfluenceSettings
from slurp.domain.settings import GeneratorSettings
from slurp.domain.settings import InstrumentationSettings
from slurp.domain.settings import KafkaSettings
from slurp.domain.settings import LocalSettings
from slurp.domain.settings import SQLiteSettings
from slurp.domain.settings import TokenSettings
from slurp.domain.validation import ConfigError

# Backward-compatible class names consumed by the adapters and existing tests.
TokenConfig = TokenSettings
ConfluenceConfig = ConfluenceSettings
KafkaConfig = KafkaSettings
GeneratorConfig = GeneratorSettings
SQLiteConfig = SQLiteSettings
LocalConfig = LocalSettings
AppConfig = AppSettings

CONNECTORS = ("local", "confluence")
DEFAULT_CONNECTOR = "local"

# argparse dest -> settings field, per section.
CONFLUENCE_CLI = {
    "confluence_username": "username",
    "confluence_api_key": "api_key",
    "confluence_base_url": "base_url",
    "confluence_space": "space",
    "confluence_cloud": "cloud",
    "confluence_months_back": "months_back",
    "confluence_concurrency": "concurrency",
    "confluence_max_pages": "max_pages",
    "confluence_page_batch_size": "page_batch_size",
    "confluence_skip": "skip",
    "confluence_enabled": "enabled",
}
KAFKA_CLI = {
    "kafka_bootstrap_servers": "bootstrap_servers",
    "kafka_topic": "topic",
    "kafka_client_id": "client_id",
}
GENERATOR_CLI = {
    "generator_language": "language",
    "generator_model": "model",
    "generator_max_tokens": "max_tokens",
    "generator_temperature": "temperature",
    "generator_base_url": "base_url",
    "generator_difficulty_ratio": "difficulty_ratio",
    "generator_concurrency": "concurrency",
    "generator_is_short": "is_short",
    "generator_batch_size": "batch_size",
    "generator_enabled": "enabled",
}
SQLITE_CLI = {"sqlite_database": "database", "sqlite_timeout": "timeout"}
LOCAL_CLI = {"local_path": "path", "local_glob": "glob", "local_extensions": "extensions"}


def add_connector_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--connector",
        dest="connector",
        choices=CONNECTORS,
        default=None,
        help=f"Source connector (default: $SLURP_CONNECTOR or {DEFAULT_CONNECTOR})",
    )


def add_confluence_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Confluence Options")
    g.add_argument("--confluence-space", dest="confluence_space", default=None,
                   help="Space key ($SLURP_CONFLUENCE_SPACE)")
    g.add_argument("--confluence-cloud", dest="confluence_cloud",
                   action=argparse.BooleanOptionalAction, default=None,
                   help="Use Confluence Cloud API ($SLURP_CONFLUENCE_CLOUD)")
    g.add_argument("--confluence-enabled", dest="confluence_enabled",
                   action="store_true", default=None, help="Enable Confluence")
    g.add_argument("--confluence-disabled", dest="confluence_enabled",
                   action="store_false", help="Disable Confluence")
    g.add_argument("--confluence-max-pages", dest="confluence_max_pages", type=int, default=None,
                   help="Max pages ($SLURP_CONFLUENCE_MAX_PAGES)")
    g.add_argument("--confluence-months-back", dest="confluence_months_back", type=int,
                   default=None, help="Months back filter ($SLURP_CONFLUENCE_MONTHS_BACK)")
    g.add_argument("--confluence-concurrency", dest="confluence_concurrency", type=int,
                   default=None, help="Concurrency ($SLURP_CONFLUENCE_CONCURRENCY)")
    g.add_argument("--confluence-page-batch-size", dest="confluence_page_batch_size", type=int,
                   default=None, help="List page size ($SLURP_CONFLUENCE_PAGE_BATCH_SIZE)")
    g.add_argument("--confluence-skip", dest="confluence_skip", type=int, default=None,
                   help="Pages to skip ($SLURP_CONFLUENCE_SKIP)")
    g.add_argument("--confluence-base-url", dest="confluence_base_url", default=None,
                   help="Base URL ($SLURP_CONFLUENCE_BASE_URL / CONFLUENCE_BASE_URL)")
    g.add_argument("--confluence-username", dest="confluence_username", default=None,
                   help="Username ($SLURP_CONFLUENCE_USERNAME / CONFLUENCE_USERNAME)")


def add_local_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Local Options")
    g.add_argument("--local-path", dest="local_path", default=None,
                   help="File/dir to ingest ($SLURP_LOCAL_PATH / LOCAL_PATH)")
    g.add_argument("--local-glob", dest="local_glob", default=None,
                   help="Glob for directories ($SLURP_LOCAL_GLOB / LOCAL_GLOB)")
    g.add_argument("--local-extensions", dest="local_extensions", default=None,
                   help="Comma-separated extensions ($SLURP_LOCAL_EXTENSIONS / LOCAL_EXTENSIONS)")


def add_kafka_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Kafka Options")
    g.add_argument("--kafka-bootstrap-servers", dest="kafka_bootstrap_servers", default=None,
                   help="Bootstrap servers ($SLURP_KAFKA_BOOTSTRAP_SERVERS)")
    g.add_argument("--kafka-topic", dest="kafka_topic", default=None,
                   help="Topic ($SLURP_KAFKA_TOPIC)")
    g.add_argument("--kafka-client-id", dest="kafka_client_id", default=None,
                   help="Client id ($SLURP_KAFKA_CLIENT_ID)")


def add_generator_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Generator Options")
    g.add_argument("--generator-model", dest="generator_model", default=None,
                   help="LLM model ($SLURP_GENERATOR_MODEL)")
    g.add_argument("--generator-language", dest="generator_language", choices=["de", "en"],
                   default=None, help="Language ($SLURP_GENERATOR_LANGUAGE)")
    g.add_argument("--generator-max-tokens", dest="generator_max_tokens", type=int, default=None,
                   help="Max tokens ($SLURP_GENERATOR_MAX_TOKENS)")
    g.add_argument("--generator-temperature", dest="generator_temperature", type=float,
                   default=None, help="Temperature ($SLURP_GENERATOR_TEMPERATURE)")
    g.add_argument("--generator-base-url", dest="generator_base_url", default=None,
                   help="LLM base URL ($SLURP_GENERATOR_BASE_URL)")
    g.add_argument("--generator-difficulty-ratio", dest="generator_difficulty_ratio",
                   choices=["easy", "medium", "hard", "mixed", "balanced"], default=None,
                   help="Difficulty ($SLURP_GENERATOR_DIFFICULTY_RATIO)")
    g.add_argument("--generator-concurrency", dest="generator_concurrency", type=int, default=None,
                   help="Concurrent LLM requests ($SLURP_GENERATOR_CONCURRENCY)")
    g.add_argument("--generator-is-short", dest="generator_is_short",
                   action=argparse.BooleanOptionalAction, default=None,
                   help="Short questions ($SLURP_GENERATOR_IS_SHORT)")
    g.add_argument("--generator-batch-size", dest="generator_batch_size", type=int, default=None,
                   help="Docs per batch ($SLURP_GENERATOR_BATCH_SIZE)")
    g.add_argument("--generator-enabled", dest="generator_enabled", action="store_true",
                   default=None, help="Enable QA generation")
    g.add_argument("--generator-disabled", dest="generator_enabled", action="store_false",
                   help="Disable QA generation")


def add_sqlite_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("SQLite Options")
    g.add_argument("--sqlite-database", dest="sqlite_database", default=None,
                   help="DB path ($SLURP_SQLITE_DATABASE / SQLITE_DATABASE)")
    g.add_argument("--sqlite-timeout", dest="sqlite_timeout", type=float, default=None,
                   help="Lock timeout secs ($SLURP_SQLITE_TIMEOUT / SQLITE_TIMEOUT)")


def _overrides(args: argparse.Namespace, mapping: dict[str, str]) -> dict:
    out = {}
    for dest, field in mapping.items():
        val = getattr(args, dest, None)
        if val is not None:
            out[field] = val
    return out


def _format_validation_error(err: ValidationError) -> str:
    lines = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"])
        msg = e["msg"]
        lines.append(f"{loc}: {msg}" if loc else msg)
    return "Invalid configuration:\n  - " + "\n  - ".join(lines)


def _parse_all(argv: list[str] | None) -> argparse.Namespace:
    argv = argv if argv is not None else sys.argv
    parser = argparse.ArgumentParser(add_help=False)
    add_connector_arg(parser)
    add_confluence_args(parser)
    add_local_args(parser)
    add_kafka_args(parser)
    add_generator_args(parser)
    add_sqlite_args(parser)
    args, _ = parser.parse_known_args(argv)
    return args


def load_settings(argv: list[str] | None = None) -> AppSettings:
    """Load validated AppSettings; raise ConfigError on any invalid value."""
    args = _parse_all(argv)
    connector = (
        getattr(args, "connector", None)
        or os.getenv("SLURP_CONNECTOR")
        or os.getenv("CONNECTOR")
        or DEFAULT_CONNECTOR
    )
    try:
        return AppSettings(
            token=TokenSettings(),
            instrumentation=InstrumentationSettings(),
            confluence=ConfluenceSettings(**_overrides(args, CONFLUENCE_CLI)),
            kafka=KafkaSettings(**_overrides(args, KAFKA_CLI)),
            generator=GeneratorSettings(**_overrides(args, GENERATOR_CLI)),
            sqlite=SQLiteSettings(**_overrides(args, SQLITE_CLI)),
            local=LocalSettings(**_overrides(args, LOCAL_CLI)),
            connector=connector,
        )
    except ValidationError as err:
        raise ConfigError(_format_validation_error(err)) from err


def load_sqlite_settings(argv: list[str] | None = None) -> SQLiteSettings:
    """Load only the SQLite section (for the render command)."""
    args = _parse_all(argv)
    try:
        return SQLiteSettings(**_overrides(args, SQLITE_CLI))
    except ValidationError as err:
        raise ConfigError(_format_validation_error(err)) from err


def create_cli_parser() -> argparse.ArgumentParser:
    """Main CLI parser with scraper/worker/render/skill subcommands."""
    parser = argparse.ArgumentParser(
        prog="slurp",
        description="Slurp - Confluence RAG Dataset Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of worker processes (default: 1)")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    scraper_parser = subparsers.add_parser(
        "scraper", help="Run the page scraper",
        description="Discovers pages and submits them to the Kafka queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_connector_arg(scraper_parser)
    add_confluence_args(scraper_parser)
    add_local_args(scraper_parser)
    add_kafka_args(scraper_parser)

    worker_parser = subparsers.add_parser(
        "worker", help="Run the QA generation worker",
        description="Processes pages from Kafka and generates QA pairs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_connector_arg(worker_parser)
    add_confluence_args(worker_parser)
    add_local_args(worker_parser)
    add_kafka_args(worker_parser)
    add_generator_args(worker_parser)
    add_sqlite_args(worker_parser)

    render_parser = subparsers.add_parser(
        "render", help="Serve a live HTML view of the QA dataset",
        description="Reads the SQLite generations table and serves an auto-refreshing page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_sqlite_args(render_parser)
    render_parser.add_argument("--host", dest="host", default="127.0.0.1",
                               help="Bind host (default: 127.0.0.1)")
    render_parser.add_argument("--port", dest="port", type=int, default=8077,
                               help="Bind port (default: 8077)")
    render_parser.add_argument("--open", dest="open_browser", action="store_true", default=False,
                               help="Open the page in a browser on start")

    skill_parser = subparsers.add_parser(
        "skill", help="Print or install the bundled slurp skill (SKILL.md)",
        description="Prints the bundled slurp skill, or installs it under .claude/skills/slurp/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    skill_parser.add_argument("--install", dest="install", action="store_true", default=False,
                              help="Write the skill instead of printing")
    skill_parser.add_argument("--base-dir", dest="base_dir", default=".",
                              help="Base directory for --install (default: current directory)")

    return parser
```

- [ ] **Step 4: Run the loader tests**

Run: `.venv/bin/python -m pytest tests/test_settings_loader.py -q`
Expected: all pass.

- [ ] **Step 5: Lint + commit**

```bash
ruff check slurp/ tests/ && ruff format slurp/ tests/
git add slurp/domain/config.py tests/test_settings_loader.py
git commit --no-verify -m "feat(config): pydantic-settings loader with CLI>env>.env precedence"
```

---

## Task 4: Remove `validate_app_config`

**Files:**
- Modify: `slurp/domain/validation.py`

**Context:** Bounds moved to Field constraints and cross-field checks moved to the `AppSettings` validator; `load_settings` is the single fail-fast entry point. Keep `ConfigError`.

- [ ] **Step 1: Confirm remaining references**

Run: `grep -rn "validate_app_config" slurp/ tests/ | grep -v __pycache__`
Expected: references in `slurp/usecases/worker.py`, `slurp/usecases/scraper.py`, and `tests/test_config_validation.py` (these are handled in Tasks 6 and 7). The function definition is in `validation.py`.

- [ ] **Step 2: Delete the function**

In `slurp/domain/validation.py`, delete everything except the `ConfigError` class and its docstring/module docstring. Also delete the `from __future__ import annotations` / `TYPE_CHECKING` import block if it is now unused. The file should reduce to:

```python
"""Configuration error type for fail-fast validation."""


class ConfigError(ValueError):
    """Raised when the assembled configuration is invalid."""
```

- [ ] **Step 3: Commit (tests still red until usecases updated — that's expected)**

```bash
git add slurp/domain/validation.py
git commit --no-verify -m "refactor(validation): drop validate_app_config (moved into settings)"
```

(Do not run the full suite yet; Tasks 6–7 finish the wiring.)

---

## Task 5: Instrumentation setup function

**Files:**
- Modify: `slurp/adapters/instrumentation.py`
- Test: `tests/test_instrumentation.py` (create)

**Context:** The data now lives in `InstrumentationSettings` (settings.py). This file keeps only the *behavior* — a `setup_instrumentation(token)` function (the old `InstrumentationConfig.setup()` logic). Remove `InstrumentationConfig`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_instrumentation.py`:

```python
"""Instrumentation setup is a no-op without a token."""

import logging

from slurp.adapters.instrumentation import setup_instrumentation


def test_no_token_is_noop(caplog):
    with caplog.at_level(logging.INFO):
        setup_instrumentation("")  # must not raise, must not configure logfire
    assert "skipping instrumentation" in caplog.text.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_instrumentation.py -q`
Expected: FAIL — `setup_instrumentation` does not exist.

- [ ] **Step 3: Rewrite `slurp/adapters/instrumentation.py`**

```python
import logging

import logfire

logger = logging.getLogger(__name__)


def setup_instrumentation(token: str | None) -> None:
    """Configure logfire instrumentation when a token is provided."""
    if not token:
        logger.info("No logfire token provided, skipping instrumentation setup.")
        return
    logfire.configure(token=token)
    logfire.instrument_httpx()
    logfire.instrument_requests()
    logfire.instrument_sqlalchemy()
```

- [ ] **Step 4: Run the test**

Run: `.venv/bin/python -m pytest tests/test_instrumentation.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add slurp/adapters/instrumentation.py tests/test_instrumentation.py
git commit --no-verify -m "refactor(instrumentation): setup_instrumentation(token) function"
```

---

## Task 6: Wire usecases to the new loader

**Files:**
- Modify: `slurp/usecases/worker.py`, `slurp/usecases/scraper.py`, `slurp/usecases/render.py`

**Context:** Replace `AppConfig.from_default(sys.argv)` + `validate_app_config(...)` + `instrumentation.setup()` with `load_settings(sys.argv)` + `setup_instrumentation(...)`. Keep the attribute name `self.app_config` (it now holds an `AppSettings`, which has the same section attribute names), so the rest of each usecase body is unchanged.

- [ ] **Step 1: Update `worker.py`**

In `slurp/usecases/worker.py`, change the imports near the top — remove
`from slurp.domain.config import AppConfig` and add:

```python
from slurp.domain.config import load_settings
from slurp.adapters.instrumentation import setup_instrumentation
```

Replace the first three lines of `WorkerUsecase.__post_init__`:

```python
        self.app_config = AppConfig.from_default(sys.argv)
        if self.app_config.instrumentation:
            self.app_config.instrumentation.setup()
```

with:

```python
        self.app_config = load_settings(sys.argv)
        setup_instrumentation(self.app_config.instrumentation.logfire_token)
```

(Also remove the now-unused `from slurp.domain.validation import validate_app_config` import and its call line, if present in this file.)

- [ ] **Step 2: Update `scraper.py`**

In `slurp/usecases/scraper.py`, replace the import of `AppConfig` with the same two imports as above, and replace in `ScrapeUsecase.__post_init__`:

```python
        self.app_config = AppConfig.from_default(sys.argv)
        if self.app_config.instrumentation:
            self.app_config.instrumentation.setup()
```

(plus any `validate_app_config(self.app_config)` line) with:

```python
        self.app_config = load_settings(sys.argv)
        setup_instrumentation(self.app_config.instrumentation.logfire_token)
```

- [ ] **Step 3: Update `render.py`**

In `slurp/usecases/render.py`, replace `from slurp.domain.config import SQLiteConfig` with
`from slurp.domain.config import load_sqlite_settings`, and in `RenderUsecase.__post_init__` replace:

```python
        self.config = SQLiteConfig.from_default(sys.argv)
```

with:

```python
        self.config = load_sqlite_settings(sys.argv)
```

- [ ] **Step 4: Run the suite (most tests should pass now)**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: the only failures should be in `tests/test_config_validation.py`, `tests/test_token_config.py`, and `tests/test_confluence_config.py` (migrated in Task 7). Everything else green. If any adapter/usecase test fails, fix the wiring before continuing.

- [ ] **Step 5: Commit**

```bash
git add slurp/usecases/worker.py slurp/usecases/scraper.py slurp/usecases/render.py
git commit --no-verify -m "feat(usecases): load settings via load_settings + setup_instrumentation"
```

---

## Task 7: Migrate the old config tests

**Files:**
- Modify: `tests/test_token_config.py`, `tests/test_config_validation.py`, `tests/test_confluence_config.py`, `tests/test_worker_generator.py`

**Context:** The old `from_env`/`validate_app_config`/`AppConfig` APIs are gone. Re-point these tests at the new models/loader. `test_worker_generator.py` should already pass (its `ConfigError` behavior is preserved by `load_settings`) — verify it, and only adjust if it references removed APIs.

- [ ] **Step 1: Rewrite `tests/test_token_config.py`**

```python
"""Token resolution via the settings model."""

from slurp.domain.settings import TokenSettings


def test_reads_generic_llm_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "internal-token")
    assert TokenSettings().api_key == "internal-token"


def test_falls_back_to_openrouter_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-token")
    assert TokenSettings().api_key == "or-token"


def test_slurp_prefixed_key_wins(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "slurp-token")
    monkeypatch.setenv("LLM_API_KEY", "legacy")
    assert TokenSettings().api_key == "slurp-token"


def test_none_when_no_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    assert TokenSettings().api_key is None
```

- [ ] **Step 2: Replace `tests/test_config_validation.py`**

The cross-field/bounds behavior is now covered by `tests/test_settings_models.py` (direct) and `tests/test_settings_loader.py` (via `load_settings`). Delete the now-obsolete file to avoid duplicate, broken references:

```bash
git rm tests/test_config_validation.py
```

- [ ] **Step 3: Update `tests/test_confluence_config.py`**

```python
"""ConfluenceSettings surface."""

from slurp.domain.settings import ConfluenceSettings


def test_no_random_selection_field():
    cfg = ConfluenceSettings(username="u", api_key="k", space="s")
    assert not hasattr(cfg, "random_selection")
```

- [ ] **Step 4: Verify `tests/test_worker_generator.py`**

Run: `.venv/bin/python -m pytest tests/test_worker_generator.py -q`
Expected: both tests pass unchanged (`test_worker_starts_without_token_when_generator_disabled`
and `test_worker_fails_fast_without_token_when_generator_enabled` — `load_settings`
raises `ConfigError` for the latter and starts cleanly for the former). If
`test_worker_starts_without_token_when_generator_disabled` fails because a stray
`SLURP_LLM_API_KEY` / env token is present, that's environment leakage, not a code
bug; the test already `delenv`s `OPENROUTER_API_KEY` — add `monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)` and `monkeypatch.delenv("LLM_API_KEY", raising=False)` to both tests for hermeticity.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Lint + commit**

```bash
ruff check slurp/ tests/ && ruff format slurp/ tests/
git add -A
git commit --no-verify -m "test: migrate config tests to settings models/loader"
```

---

## Task 8: Documentation — `.env.example`, CLAUDE.md, README

**Files:**
- Create: `.env.example`
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 1: Create `.env.example`**

```bash
# Slurp configuration — copy to .env and fill in. All vars are optional unless
# noted; CLI flags override these. Legacy names (CONFLUENCE_*, KAFKA_*, etc.)
# still work as aliases.

# --- LLM (required when the generator is enabled) ---
SLURP_LLM_API_KEY=

# --- Connector: local | confluence ---
SLURP_CONNECTOR=local

# --- Generator ---
SLURP_GENERATOR_MODEL=google/gemini-2.5-flash-preview-05-20
SLURP_GENERATOR_LANGUAGE=de
SLURP_GENERATOR_BASE_URL=https://openrouter.ai/api/v1
SLURP_GENERATOR_TEMPERATURE=0.7
SLURP_GENERATOR_MAX_TOKENS=4096
SLURP_GENERATOR_CONCURRENCY=5
SLURP_GENERATOR_DIFFICULTY_RATIO=mixed
SLURP_GENERATOR_BATCH_SIZE=1

# --- Confluence (required when SLURP_CONNECTOR=confluence) ---
SLURP_CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
SLURP_CONFLUENCE_USERNAME=you@example.com
SLURP_CONFLUENCE_API_KEY=
SLURP_CONFLUENCE_SPACE=
SLURP_CONFLUENCE_MAX_PAGES=50

# --- Local connector ---
SLURP_LOCAL_PATH=
SLURP_LOCAL_GLOB=**/*
SLURP_LOCAL_EXTENSIONS=.md,.html,.txt

# --- Kafka / Redpanda ---
SLURP_KAFKA_BOOTSTRAP_SERVERS=localhost:19092
SLURP_KAFKA_TOPIC=tasks
SLURP_KAFKA_CLIENT_ID=slurp

# --- SQLite ---
SLURP_SQLITE_DATABASE=./data.db
SLURP_SQLITE_TIMEOUT=5.0

# --- Observability (optional) ---
SLURP_LOGFIRE_TOKEN=
```

- [ ] **Step 2: Update the env section in `CLAUDE.md`**

Replace the "Required Environment Variables" block in `CLAUDE.md` with a note that
config uses the `SLURP_` prefix (see `.env.example`), that a `.env` file is
auto-loaded, that CLI flags override env vars, and that legacy names
(`CONFLUENCE_*`, `KAFKA_*`, `SQLITE_*`, `OPENROUTER_API_KEY`, `LOGFIRE_TOKEN`) are
still accepted as aliases. List the key vars: `SLURP_LLM_API_KEY`,
`SLURP_CONNECTOR`, `SLURP_CONFLUENCE_*`, `SLURP_KAFKA_*`, `SLURP_SQLITE_DATABASE`.

- [ ] **Step 3: Update `README.md`**

Find any environment-variable / configuration section in `README.md` and update it
to the `SLURP_` scheme, pointing at `.env.example`. (If README has no such section,
add a short "Configuration" section that references `.env.example` and the
CLI > env > .env > default precedence.) Verify with `grep -n "OPENROUTER_API_KEY\|CONFLUENCE_BASE_URL\|env" README.md` and update the lines you find.

- [ ] **Step 4: Commit**

```bash
git add .env.example CLAUDE.md README.md
git commit --no-verify -m "docs: document SLURP_ settings scheme and .env.example"
```

---

## Task 9: Final verification

- [ ] **Step 1: No leftover references to removed APIs**

Run: `grep -rn "from_default\|from_env\|from_args\|validate_app_config\|InstrumentationConfig\|\.setup()" slurp/ | grep -v __pycache__`
Expected: no matches (all replaced). If any remain, fix them.

- [ ] **Step 2: Full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 3: Lint + format**

Run: `ruff check slurp/ tests/` → clean. `ruff format --check slurp/ tests/` → clean.

- [ ] **Step 4: CLI sanity + a real precedence smoke test**

```bash
.venv/bin/python -m slurp --help >/dev/null && echo "main OK"
.venv/bin/python -m slurp worker --help >/dev/null && echo "worker OK"
SLURP_KAFKA_TOPIC=fromenv .venv/bin/python -c "from slurp.domain.config import load_settings; print(load_settings(['slurp','worker','--connector','local','--generator-disabled']).kafka.topic)"
# Expected: fromenv
SLURP_KAFKA_TOPIC=fromenv .venv/bin/python -c "from slurp.domain.config import load_settings; print(load_settings(['slurp','worker','--connector','local','--generator-disabled','--kafka-topic','fromcli']).kafka.topic)"
# Expected: fromcli
```

- [ ] **Step 5: Final commit if formatting changed**

```bash
git add -A && git commit --no-verify -m "chore: final format pass" || true
```

---

## Self-review notes (author)

- **Spec coverage:** pydantic-settings models → Task 2; SLURP_ prefix + legacy aliases → Task 2; `.env` loading → Task 2 (`env_file` in every model); field bounds → Task 2 (`Field` constraints); cross-field validation → Task 2 (`AppSettings._check_cross_field`); CLI precedence + `None` defaults → Task 3; `load_settings` ValidationError→ConfigError → Task 3; legacy class re-exports (adapters untouched) → Task 3; remove `validate_app_config` → Task 4; instrumentation → Task 5; usecase wiring + double-setup-free → Task 6; test migration → Task 7; `.env.example` + docs → Task 8; final verification → Task 9. All covered.
- **Deviation from spec:** `load` is a module-level `load_settings(argv)` in `config.py` (not a staticmethod on `AppSettings`) to avoid a `config ↔ settings` import cycle. `render` uses `load_sqlite_settings` so it isn't subject to the generator-token cross-field rule. Both noted here intentionally.
- **Behavioral changes (intended):** SQLite default timeout standardized to 5.0; every Generator/Confluence field now has an env var; env precedence now consistent across all sections.
- **Risk note:** Field named `model` on `GeneratorSettings` → `protected_namespaces=()` set to avoid pydantic warnings. Empty env vars treated as unset (`env_ignore_empty=True`) so a blank `CONFLUENCE_API_KEY=` doesn't shadow detection of "missing".
```

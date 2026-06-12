# Proper Settings Format (pydantic-settings) — Design

**Date:** 2026-06-12
**Status:** Approved

## Goal

Replace the hand-rolled `argparse` + `os.getenv` configuration in
`slurp/domain/config.py` with a typed, validated settings layer built on
**pydantic-settings**. Give every setting both a CLI option and an environment
variable under a unified `SLURP_` prefix, load a `.env` file, and keep full
backward compatibility with the existing environment-variable names.

## Decisions (from brainstorming)

- **Mechanism:** pydantic-settings `BaseSettings`. (pydantic-settings 2.11 is
  already present transitively; declare it explicitly in `pyproject.toml`.)
- **Naming:** unified `SLURP_` prefix (`SLURP_GENERATOR_MODEL`,
  `SLURP_KAFKA_TOPIC`, …). Existing names kept as aliases so nothing breaks.
- **.env:** auto-loaded from the working directory.
- **CLI:** keep the bespoke argparse subcommands (`scraper`/`worker`/`render`/
  `skill`); do **not** adopt pydantic-settings' experimental CLI.
- **Attribute names preserved** so adapters/usecases that read config are
  untouched; only the construction layer changes.

## Precedence

`CLI flag > env var > .env file > field default`.

pydantic-settings native priority is `init args > env > .env > defaults`.
To make an explicit CLI flag win over env without argparse defaults masking env
vars: **every argparse flag defaults to `None`**; after parsing, only the
non-`None` flags are collected and passed as init overrides to the settings
model. Unset flags are omitted, so env/.env/default decide them.

## Components

### `slurp/domain/settings.py` (new)

One `BaseSettings` subclass per section. Each sets
`model_config = SettingsConfigDict(env_prefix="SLURP_<SECTION>_", env_file=".env",
extra="ignore", populate_by_name=True)`.

| Class | env_prefix | Fields (attr names preserved) | Legacy aliases (`AliasChoices`) |
|---|---|---|---|
| `TokenSettings` | `SLURP_` | `api_key` (→ `SLURP_LLM_API_KEY`) | `LLM_API_KEY`, `OPENROUTER_API_KEY` |
| `ConfluenceSettings` | `SLURP_CONFLUENCE_` | `username`, `api_key`, `space`, `base_url`, `cloud`, `months_back`, `concurrency`, `max_pages`, `page_batch_size`, `skip`, `enabled` | `CONFLUENCE_BASE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_KEY` |
| `KafkaSettings` | `SLURP_KAFKA_` | `bootstrap_servers`, `topic`, `client_id` | `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`, `KAFKA_CLIENT_ID` |
| `GeneratorSettings` | `SLURP_GENERATOR_` | `language`, `model`, `max_tokens`, `temperature`, `base_url`, `difficulty_ratio`, `concurrency`, `is_short`, `batch_size`, `enabled` | — (new env coverage) |
| `SQLiteSettings` | `SLURP_SQLITE_` | `database`, `timeout` | `SQLITE_DATABASE`, `SQLITE_TIMEOUT` |
| `LocalSettings` | `SLURP_LOCAL_` | `path`, `glob`, `extensions` | `LOCAL_PATH`, `LOCAL_GLOB`, `LOCAL_EXTENSIONS` |
| `InstrumentationSettings` | `SLURP_` | `logfire_token` (→ `SLURP_LOGFIRE_TOKEN`) | `LOGFIRE_TOKEN` |

For a field with a legacy alias, the `AliasChoices` lists **both** the new
prefixed name and the legacy name (when `validation_alias` is set,
pydantic-settings ignores `env_prefix` for that field, so the new name must be
spelled out explicitly). `populate_by_name=True` lets tests still construct
models with plain field-name kwargs (e.g. `ConfluenceSettings(space="s")`).

`TokenSettings.api_key` is optional (`str | None = None`) — the "no token when
generator disabled" path stays valid. The `LocalConfig.extension_list()` helper
is preserved as a method.

### Field-level validation (replaces bounds in `validate_app_config`)

- `GeneratorSettings`: `concurrency: int = Field(5, gt=0)`,
  `temperature: float = Field(0.7, ge=0, le=2)`, `max_tokens: int = Field(4096, gt=0)`,
  `batch_size: int = Field(1, ge=1)`, `language: Literal["de","en"]`,
  `difficulty_ratio: Literal["easy","medium","hard","mixed","balanced"]`.
- `ConfluenceSettings`: `page_batch_size: int = Field(50, gt=0)`,
  `max_pages: int = Field(50, ge=0)`, `concurrency: int = Field(4, gt=0)`,
  `skip: int = Field(0, ge=0)`, `months_back: int = Field(0, ge=0)`.

### `AppSettings` (new top-level)

Aggregates the sections plus `connector: Literal["local","confluence"]`
(env `SLURP_CONNECTOR`, alias `CONNECTOR`, default `"local"`).

- `@model_validator(mode="after")` enforces the cross-field rules:
  - if `generator.enabled` and `token.api_key is None` → error listing the token
    requirement.
  - if `connector == "confluence"` → require `confluence.base_url`, `username`,
    `api_key`, `space` (collect all missing).
  Multiple problems are aggregated into one message.
- `@staticmethod load(argv: list[str]) -> AppSettings`: builds the argparse
  parser, parses `argv`, collects non-`None` overrides per section, constructs
  each section settings with those overrides, constructs `AppSettings`, and on
  any pydantic `ValidationError` re-raises `ConfigError` (kept in
  `slurp/domain/validation.py`) with a single aggregated, readable message.

### `slurp/domain/validation.py`

Keep the `ConfigError(ValueError)` type. Remove `validate_app_config` (its
bounds move to Field constraints and its cross-field checks move to the
`AppSettings` model_validator). `load()` is the single fail-fast entry point.

### CLI (`create_cli_parser` and the per-section `add_to_parser`)

- Stays in place and keeps every existing flag (so the public CLI surface is
  unchanged), and adds flags for any field that lacked one.
- **All flag defaults become `None`.** Help text documents the resolved default
  (e.g. "default: $SLURP_GENERATOR_MODEL or google/gemini-2.5-flash-...").
- Help strings (`--help`) reference the corresponding env var names.

### Usecases

`ScrapeUsecase` / `WorkerUsecase` / `RenderUsecase` replace
`AppConfig.from_default(sys.argv)` (+ `validate_app_config(...)`) with
`AppSettings.load(sys.argv)`. `RenderUsecase` continues to need only the SQLite
section. Instrumentation: usecases call a `setup_instrumentation(token)` helper
(the existing `InstrumentationConfig.setup()` logic, sourced from
`settings.instrumentation.logfire_token`); the double-setup fix from the prior
pass is preserved (configured exactly once).

### `slurp/adapters/instrumentation.py`

`InstrumentationConfig` is folded into `InstrumentationSettings` in the settings
module; the `setup()` behavior (configure logfire + instrument httpx/requests/
sqlalchemy when a token is present, else log-and-skip) becomes a module function
or a method retained on the settings object. No behavior change.

## Backward compatibility

All 15 legacy env vars resolve unchanged via `AliasChoices`:
`CONFLUENCE_BASE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_KEY`, `CONNECTOR`,
`KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_CLIENT_ID`, `KAFKA_TOPIC`, `LLM_API_KEY`,
`LOCAL_EXTENSIONS`, `LOCAL_GLOB`, `LOCAL_PATH`, `OPENROUTER_API_KEY`,
`SQLITE_DATABASE`, `SQLITE_TIMEOUT`, `LOGFIRE_TOKEN`. When both the new
`SLURP_*` name and a legacy name are set, the order in `AliasChoices` decides;
the new `SLURP_*` name is listed first and wins.

## Documentation

- `pyproject.toml`: add `pydantic-settings>=2.0.0` to `dependencies`.
- `.env.example` (new): every `SLURP_*` variable with a comment and the default.
- `CLAUDE.md` + `README.md`: update the "Required Environment Variables" section
  to the `SLURP_*` scheme, noting legacy names still work.

## Testing

- **Per-section env loading:** set `SLURP_<SECTION>_<FIELD>` and assert the
  section reads it; set the legacy name and assert the alias resolves.
- **.env loading:** write a `tmp_path/.env`, point the loader at it, assert
  values load.
- **Precedence:** CLI override beats env; env beats default; an unset CLI flag
  does not mask an env var.
- **Bounds:** out-of-range values raise (`ConfigError` via `load`).
- **Cross-field:** missing token with generator enabled → `ConfigError`; missing
  Confluence creds with `connector=confluence` → `ConfigError`; generator
  disabled → no token required.
- **Adapters untouched:** the full existing suite stays green (attribute names
  preserved).
- Migrate the existing `tests/test_token_config.py`, `tests/test_config_validation.py`,
  and `tests/test_confluence_config.py` to the new models/loader.

## Non-goals

- No change to adapter logic, ports, or the pipeline.
- No switch to pydantic-settings' experimental CLI parser.
- No new config sources beyond env, `.env`, and CLI (no remote/secret-manager
  backends).

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


_ENV = {
    "env_file": ".env",
    "extra": "ignore",
    "populate_by_name": True,
    "env_ignore_empty": True,
    # CLI overrides are applied via setattr after env/.env/default resolve, so
    # assignment must validate (enforces field bounds on CLI-supplied values).
    "validate_assignment": True,
}


class TokenSettings(BaseSettings):
    model_config = SettingsConfigDict(**_ENV)

    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SLURP_LLM_API_KEY", "LLM_API_KEY", "OPENROUTER_API_KEY"),
    )


class InstrumentationSettings(BaseSettings):
    model_config = SettingsConfigDict(**_ENV)

    logfire_token: str = Field(
        default="", validation_alias=AliasChoices("SLURP_LOGFIRE_TOKEN", "LOGFIRE_TOKEN")
    )


class KafkaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLURP_KAFKA_", **_ENV)

    bootstrap_servers: str = Field(
        default="localhost:19092",
        validation_alias=AliasChoices("SLURP_KAFKA_BOOTSTRAP_SERVERS", "KAFKA_BOOTSTRAP_SERVERS"),
    )
    topic: str = Field(
        default="tasks", validation_alias=AliasChoices("SLURP_KAFKA_TOPIC", "KAFKA_TOPIC")
    )
    client_id: str = Field(
        default="slurp", validation_alias=AliasChoices("SLURP_KAFKA_CLIENT_ID", "KAFKA_CLIENT_ID")
    )


class SQLiteSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLURP_SQLITE_", **_ENV)

    database: str = Field(
        default="./data.db",
        validation_alias=AliasChoices("SLURP_SQLITE_DATABASE", "SQLITE_DATABASE"),
    )
    timeout: float = Field(
        default=5.0, gt=0, validation_alias=AliasChoices("SLURP_SQLITE_TIMEOUT", "SQLITE_TIMEOUT")
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
        default="",
        validation_alias=AliasChoices("SLURP_CONFLUENCE_USERNAME", "CONFLUENCE_USERNAME"),
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
    def _check_cross_field(self) -> AppSettings:
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

"""Fail-fast validation for the assembled AppConfig."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from slurp.domain.config import AppConfig


class ConfigError(ValueError):
    """Raised when the assembled configuration is invalid."""


def validate_app_config(config: AppConfig) -> None:
    """Validate config; raise ConfigError listing every problem found."""
    problems: list[str] = []

    if config.generator.enabled and config.token is None:
        problems.append(
            "LLM token required when the generator is enabled "
            "(set LLM_API_KEY or OPENROUTER_API_KEY, or pass --generator-disabled)."
        )

    if config.connector == "confluence":
        c = config.confluence
        if not c.base_url:
            problems.append("Confluence base_url is required (CONFLUENCE_BASE_URL).")
        if not c.username:
            problems.append("Confluence username is required (CONFLUENCE_USERNAME).")
        if not c.api_key:
            problems.append("Confluence api_key is required (CONFLUENCE_API_KEY).")
        if not c.space:
            problems.append("Confluence space is required (--confluence-space).")

    g = config.generator
    if g.concurrency <= 0:
        problems.append(f"generator concurrency must be > 0 (got {g.concurrency}).")
    if not 0.0 <= g.temperature <= 2.0:
        problems.append(f"generator temperature must be in [0, 2] (got {g.temperature}).")
    if g.max_tokens <= 0:
        problems.append(f"generator max_tokens must be > 0 (got {g.max_tokens}).")
    if g.batch_size < 1:
        problems.append(f"generator batch_size must be >= 1 (got {g.batch_size}).")

    c = config.confluence
    if c.page_batch_size <= 0:
        problems.append(f"confluence page_batch_size must be > 0 (got {c.page_batch_size}).")
    if c.max_pages < 0:
        problems.append(f"confluence max_pages must be >= 0 (got {c.max_pages}).")

    if problems:
        raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(problems))

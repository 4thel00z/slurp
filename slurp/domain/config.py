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
    g.add_argument(
        "--confluence-space",
        dest="confluence_space",
        default=None,
        help="Space key ($SLURP_CONFLUENCE_SPACE)",
    )
    g.add_argument(
        "--confluence-cloud",
        dest="confluence_cloud",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use Confluence Cloud API ($SLURP_CONFLUENCE_CLOUD)",
    )
    g.add_argument(
        "--confluence-enabled",
        dest="confluence_enabled",
        action="store_true",
        default=None,
        help="Enable Confluence",
    )
    g.add_argument(
        "--confluence-disabled",
        dest="confluence_enabled",
        action="store_false",
        help="Disable Confluence",
    )
    g.add_argument(
        "--confluence-max-pages",
        dest="confluence_max_pages",
        type=int,
        default=None,
        help="Max pages ($SLURP_CONFLUENCE_MAX_PAGES)",
    )
    g.add_argument(
        "--confluence-months-back",
        dest="confluence_months_back",
        type=int,
        default=None,
        help="Months back filter ($SLURP_CONFLUENCE_MONTHS_BACK)",
    )
    g.add_argument(
        "--confluence-concurrency",
        dest="confluence_concurrency",
        type=int,
        default=None,
        help="Concurrency ($SLURP_CONFLUENCE_CONCURRENCY)",
    )
    g.add_argument(
        "--confluence-page-batch-size",
        dest="confluence_page_batch_size",
        type=int,
        default=None,
        help="List page size ($SLURP_CONFLUENCE_PAGE_BATCH_SIZE)",
    )
    g.add_argument(
        "--confluence-skip",
        dest="confluence_skip",
        type=int,
        default=None,
        help="Pages to skip ($SLURP_CONFLUENCE_SKIP)",
    )
    g.add_argument(
        "--confluence-base-url",
        dest="confluence_base_url",
        default=None,
        help="Base URL ($SLURP_CONFLUENCE_BASE_URL / CONFLUENCE_BASE_URL)",
    )
    g.add_argument(
        "--confluence-username",
        dest="confluence_username",
        default=None,
        help="Username ($SLURP_CONFLUENCE_USERNAME / CONFLUENCE_USERNAME)",
    )


def add_local_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Local Options")
    g.add_argument(
        "--local-path",
        dest="local_path",
        default=None,
        help="File/dir to ingest ($SLURP_LOCAL_PATH / LOCAL_PATH)",
    )
    g.add_argument(
        "--local-glob",
        dest="local_glob",
        default=None,
        help="Glob for directories ($SLURP_LOCAL_GLOB / LOCAL_GLOB)",
    )
    g.add_argument(
        "--local-extensions",
        dest="local_extensions",
        default=None,
        help="Comma-separated extensions ($SLURP_LOCAL_EXTENSIONS / LOCAL_EXTENSIONS)",
    )


def add_kafka_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Kafka Options")
    g.add_argument(
        "--kafka-bootstrap-servers",
        dest="kafka_bootstrap_servers",
        default=None,
        help="Bootstrap servers ($SLURP_KAFKA_BOOTSTRAP_SERVERS)",
    )
    g.add_argument(
        "--kafka-topic", dest="kafka_topic", default=None, help="Topic ($SLURP_KAFKA_TOPIC)"
    )
    g.add_argument(
        "--kafka-client-id",
        dest="kafka_client_id",
        default=None,
        help="Client id ($SLURP_KAFKA_CLIENT_ID)",
    )


def add_generator_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("Generator Options")
    g.add_argument(
        "--generator-model",
        dest="generator_model",
        default=None,
        help="LLM model ($SLURP_GENERATOR_MODEL)",
    )
    g.add_argument(
        "--generator-language",
        dest="generator_language",
        choices=["de", "en"],
        default=None,
        help="Language ($SLURP_GENERATOR_LANGUAGE)",
    )
    g.add_argument(
        "--generator-max-tokens",
        dest="generator_max_tokens",
        type=int,
        default=None,
        help="Max tokens ($SLURP_GENERATOR_MAX_TOKENS)",
    )
    g.add_argument(
        "--generator-temperature",
        dest="generator_temperature",
        type=float,
        default=None,
        help="Temperature ($SLURP_GENERATOR_TEMPERATURE)",
    )
    g.add_argument(
        "--generator-base-url",
        dest="generator_base_url",
        default=None,
        help="LLM base URL ($SLURP_GENERATOR_BASE_URL)",
    )
    g.add_argument(
        "--generator-difficulty-ratio",
        dest="generator_difficulty_ratio",
        choices=["easy", "medium", "hard", "mixed", "balanced"],
        default=None,
        help="Difficulty ($SLURP_GENERATOR_DIFFICULTY_RATIO)",
    )
    g.add_argument(
        "--generator-concurrency",
        dest="generator_concurrency",
        type=int,
        default=None,
        help="Concurrent LLM requests ($SLURP_GENERATOR_CONCURRENCY)",
    )
    g.add_argument(
        "--generator-is-short",
        dest="generator_is_short",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Short questions ($SLURP_GENERATOR_IS_SHORT)",
    )
    g.add_argument(
        "--generator-batch-size",
        dest="generator_batch_size",
        type=int,
        default=None,
        help="Docs per batch ($SLURP_GENERATOR_BATCH_SIZE)",
    )
    g.add_argument(
        "--generator-enabled",
        dest="generator_enabled",
        action="store_true",
        default=None,
        help="Enable QA generation",
    )
    g.add_argument(
        "--generator-disabled",
        dest="generator_enabled",
        action="store_false",
        help="Disable QA generation",
    )


def add_sqlite_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_argument_group("SQLite Options")
    g.add_argument(
        "--sqlite-database",
        dest="sqlite_database",
        default=None,
        help="DB path ($SLURP_SQLITE_DATABASE / SQLITE_DATABASE)",
    )
    g.add_argument(
        "--sqlite-timeout",
        dest="sqlite_timeout",
        type=float,
        default=None,
        help="Lock timeout secs ($SLURP_SQLITE_TIMEOUT / SQLITE_TIMEOUT)",
    )


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
    parser.add_argument(
        "--workers", type=int, default=1, help="Number of worker processes (default: 1)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    scraper_parser = subparsers.add_parser(
        "scraper",
        help="Run the page scraper",
        description="Discovers pages and submits them to the Kafka queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_connector_arg(scraper_parser)
    add_confluence_args(scraper_parser)
    add_local_args(scraper_parser)
    add_kafka_args(scraper_parser)

    worker_parser = subparsers.add_parser(
        "worker",
        help="Run the QA generation worker",
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
        "render",
        help="Serve a live HTML view of the QA dataset",
        description="Reads the SQLite generations table and serves an auto-refreshing page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_sqlite_args(render_parser)
    render_parser.add_argument(
        "--host", dest="host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)"
    )
    render_parser.add_argument(
        "--port", dest="port", type=int, default=8077, help="Bind port (default: 8077)"
    )
    render_parser.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        default=False,
        help="Open the page in a browser on start",
    )

    skill_parser = subparsers.add_parser(
        "skill",
        help="Print or install the bundled slurp skill (SKILL.md)",
        description="Prints the bundled slurp skill, or installs it under .claude/skills/slurp/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    skill_parser.add_argument(
        "--install",
        dest="install",
        action="store_true",
        default=False,
        help="Write the skill instead of printing",
    )
    skill_parser.add_argument(
        "--base-dir",
        dest="base_dir",
        default=".",
        help="Base directory for --install (default: current directory)",
    )

    return parser

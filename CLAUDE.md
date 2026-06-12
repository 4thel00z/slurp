# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Slurp** is a distributed Confluence RAG Dataset Generator that scrapes Confluence pages and generates Question-Answer pairs for evaluating RAG systems. It follows **Hexagonal/Ports & Adapters** architecture.

## Commands

```bash
# Install dependencies
uv sync                    # Core package
uv sync --extra scripts    # With standalone script dependencies

# Run distributed system (requires Kafka/Redpanda on localhost:19092)
python -m slurp scraper --confluence-space MYSPACE --confluence-max-pages 100
python -m slurp worker --generator-batch-size 4 --generator-language de

# Live HTML view of the generated QA dataset (auto-refreshing)
python -m slurp render --open --sqlite-database ./data.db

# Print or install the bundled slurp skill (.claude/skills/slurp/SKILL.md)
python -m slurp skill
python -m slurp skill --install

# Linting and formatting
ruff check .               # Lint
ruff check --fix .         # Lint with auto-fix
ruff format .              # Format

# Type checking (relaxed config, not in pre-commit)
mypy slurp/

# Run tests
pytest                     # All tests
pytest tests/test_html_parser.py           # Single file
pytest tests/test_html_parser.py::test_parse_empty_html  # Single test
pytest -k "html"           # Tests matching pattern

# Security scan
bandit -c pyproject.toml -r slurp/

# Pre-commit hooks
pre-commit run --all-files
```

## Architecture

```
slurp/
├── domain/           # Pure business logic (models, ports/protocols, config)
├── adapters/         # Infrastructure implementations
│   ├── producers/    # Task sources (Confluence spaces)
│   ├── downloader/   # Content fetchers (Confluence API)
│   ├── mutators/     # Transformers (HTMLParser, SqlitePersistence)
│   ├── generators/   # QA generation (LLM via OpenRouter)
│   └── kafka.py      # Message queue consumer/producer
└── usecases/         # Application orchestration (scraper, worker)
```

**Data Flow:**
```
Scraper: <Producer> → KafkaQueueSubmitter → Kafka
Worker:  Kafka → <Downloader> → HTMLParser → SqlitePersistence → LLMGenerator → SqlitePersistence
```

**Connectors:** The scraper picks a producer from `--connector {local,confluence}`
(default `local`). The worker dispatches a downloader per task via the lazy
`DownloaderRegistry` keyed on `task.downloader`, so unused connectors (e.g. the
Confluence client in local mode) are never constructed. Add a connector by
registering a producer and a downloader under a shared name.

**Core Protocols** (in `domain/ports.py`):
- `ProducerProtocol` - Generates tasks to process
- `ConsumerProtocol` - Consumes tasks from queue
- `DownloaderProtocol` - Downloads content from sources
- `GeneratorProtocol` - Generates QA pairs from content
- `TaskResultMutatorProtocol` - Transforms task results in pipeline

## Configuration

Configuration uses **pydantic-settings** with a unified `SLURP_` env-var prefix.
Precedence is **CLI flag > env var > `.env` file > default**. A `.env` file in the
working directory is auto-loaded. See `.env.example` for the full list.

Key variables:

```bash
SLURP_LLM_API_KEY=""            # required when the generator is enabled
SLURP_CONNECTOR="local"         # local | confluence
SLURP_GENERATOR_MODEL="..."     # every generator option has a SLURP_GENERATOR_* var
SLURP_CONFLUENCE_BASE_URL="https://your-domain.atlassian.net"
SLURP_CONFLUENCE_USERNAME="you@example.com"
SLURP_CONFLUENCE_API_KEY=""
SLURP_CONFLUENCE_SPACE=""       # required when SLURP_CONNECTOR=confluence
SLURP_KAFKA_BOOTSTRAP_SERVERS="localhost:19092"
SLURP_KAFKA_TOPIC="tasks"
SLURP_SQLITE_DATABASE="./data.db"
```

Legacy names (`CONFLUENCE_*`, `KAFKA_*`, `SQLITE_*`, `LLM_API_KEY`,
`OPENROUTER_API_KEY`, `LOGFIRE_TOKEN`) still work as aliases.

## Development Notes

- **Read `reports/` folder first** before making changes - contains architecture analysis and design decisions
- All imports use `slurp` as the package name
- Async/await throughout for I/O-bound operations
- Configuration follows 12-factor pattern: env vars (defaults) + CLI args (overrides)
- `scripts/` folder contains standalone utilities that don't require Kafka

**Adding new components:**
- New data source → Create `ProducerProtocol` in `adapters/producers/`
- New LLM provider → Extend `GeneratorProtocol` in `adapters/generators/`
- New storage → Implement `TaskResultMutatorProtocol` in `adapters/mutators/`

## Code Style

- Ruff for linting/formatting (configured in `pyproject.toml`)
- Isort style: single imports per line, `slurp` as first-party
- Double quotes for strings
- Line length: 100 characters
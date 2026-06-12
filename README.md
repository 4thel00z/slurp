<div align="center">

# 🌊 Slurp

<img src="logo.jpeg" alt="Slurp Logo" width="400"/>

### Cross-Document RAG Dataset Generator

A comprehensive tool for generating RAG (Retrieval-Augmented Generation) eval datasets from Confluence pages (more sources planned).

[![CI](https://github.com/4thel00z/slurp/workflows/CI/badge.svg)](https://github.com/4thel00z/slurp/actions)
[![CodeQL](https://github.com/4thel00z/slurp/workflows/CodeQL%20Security%20Scan/badge.svg)](https://github.com/4thel00z/slurp/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</div>

---
This system uses a distributed architecture with Kafka for task queue management, separate scraper and worker processes, and supports both batch and streaming processing.

## Architecture

- **Scraper**: Discovers and submits Confluence pages to a Kafka topic
- **Worker**: Processes pages from Kafka, generates QA pairs, and stores results in SQLite
- **Kafka/Redpanda**: Message queue for task distribution
- **SQLite**: Storage for processed documents and generated QA pairs

## Features

- **Distributed Processing**: Separate scraper and worker processes for scalability
- **Batch Processing**: Support for processing documents in batches for cross-document questions
- **Hierarchical Crawling**: Discovers parent-child relationships between pages
- **Date Filtering**: Filter pages by last modification date (e.g., only pages updated in last 6 months)
- **Intelligent Question Generation**: Creates questions of varying difficulty levels
- **Multiple Languages**: Support for German and English content
- **HTML Processing**: Robust HTML parsing for clean text extraction

## Installation

```bash
# Install core package (using uv)
uv sync

# Install with standalone script dependencies
uv sync --extra scripts

# Start Redpanda (Kafka-compatible message broker) for distributed mode
docker-compose up -d  # If you have a docker-compose.yml for Kafka/Redpanda
```

## Configuration

Copy `.env.example` to `.env` and fill in the values. A `.env` file in the working
directory is auto-loaded. Precedence is **CLI flag > env var > `.env` file > default**.
Legacy names (`CONFLUENCE_*`, `KAFKA_*`, `SQLITE_*`, `OPENROUTER_API_KEY`) still work
as aliases for the new `SLURP_` vars.

Key variables:

```bash
SLURP_LLM_API_KEY=""            # required when the generator is enabled
SLURP_CONNECTOR="local"         # local | confluence
SLURP_CONFLUENCE_BASE_URL="https://your-domain.atlassian.net"
SLURP_CONFLUENCE_USERNAME="you@example.com"
SLURP_CONFLUENCE_API_KEY=""
SLURP_CONFLUENCE_SPACE=""       # required when SLURP_CONNECTOR=confluence
SLURP_KAFKA_BOOTSTRAP_SERVERS="localhost:19092"
SLURP_KAFKA_TOPIC="tasks"
SLURP_SQLITE_DATABASE="./data.db"
```

See `.env.example` for the full list including generator, local connector, and
observability options.

### LLM provider

The QA generator talks to any **OpenAI-compatible** endpoint, selected by
`--generator-base-url` and an API key. The key is read from `SLURP_LLM_API_KEY`
(legacy `LLM_API_KEY` and `OPENROUTER_API_KEY` still work as aliases).

```bash
# Default: OpenRouter
export SLURP_LLM_API_KEY="your-openrouter-key"

# Any other OpenAI-compatible endpoint
export SLURP_LLM_API_KEY="$(your-token-command)"   # or a static key
python -m slurp worker \
  --generator-base-url https://your-llm-endpoint.example/v1 \
  --generator-model your-model
```

## Usage

### Connectors

Slurp ingests content through pluggable **connectors**, selected with
`--connector`. The default is `local`.

| Connector    | Source                         | Requires                          |
|--------------|--------------------------------|-----------------------------------|
| `local`      | Files on disk (`.md/.html/.txt`) | nothing (no Confluence creds)     |
| `confluence` | A Confluence space             | `CONFLUENCE_*` credentials        |

Both connectors still flow through Kafka and the LLM generator, so a broker
(`infra/docker-compose.yaml`) and `SLURP_LLM_API_KEY` are required either way.

#### Local files (default)

```bash
# Scrape a directory of documents into the queue
python -m slurp scraper --local-path ./docs

# Only markdown files
python -m slurp scraper --local-path ./docs --local-extensions .md

# A single file
python -m slurp scraper --local-path ./docs/intro.md

# Then run the worker (it dispatches on each task's connector automatically)
python -m slurp worker --generator-batch-size 1
```

### Live dataset view

```bash
# Serve an auto-refreshing HTML view of the generated QA pairs (default :8077)
python -m slurp render --open --sqlite-database ./data.db
```

The page polls the SQLite `generations` table, so QA pairs appear as the worker
produces them.

### Slurp skill (for Claude Code)

```bash
python -m slurp skill            # print the bundled SKILL.md
python -m slurp skill --install  # write it to ./.claude/skills/slurp/SKILL.md
```

### Distributed System (Production Mode)

#### Running the Scraper

The scraper discovers Confluence pages and submits them to Kafka
(note the explicit `--connector confluence`, since `local` is the default):

```bash
# Scrape up to 50 pages from a Confluence space
python -m slurp scraper --connector confluence --confluence-space RESEARCH --confluence-max-pages 50

# Filter by recent pages (last 3 months)
python -m slurp scraper --connector confluence --confluence-space RESEARCH --confluence-months-back 3

# Skip the first 100 pages
python -m slurp scraper --connector confluence --confluence-space RESEARCH --confluence-skip 100

# Run multiple scraper workers
python -m slurp scraper --workers 2 --connector confluence --confluence-space RESEARCH
```

#### Running the Worker

The worker processes pages from Kafka and generates QA pairs:

```bash
# Process pages individually
python -m slurp worker --generator-batch-size 1

# Process pages in batches of 4 for cross-document questions
python -m slurp worker --generator-batch-size 4

# Specify a different model
python -m slurp worker --generator-model "anthropic/claude-3-sonnet"

# Run multiple worker processes
python -m slurp worker --workers 4 --generator-language de
```

## Command Line Options

### Scraper Options

- `--confluence-space`: Confluence space key to scrape
- `--confluence-max-pages`: Maximum number of pages to fetch (default: 50)
- `--confluence-months-back`: Only process pages modified within last N months (0 = no filter, default: 0)
- `--confluence-skip`: Number of pages to skip (default: 0)
- `--confluence-concurrency`: Number of concurrent requests (default: 4)
- `--confluence-page-batch-size`: Number of pages to fetch per batch (default: 50)

### Worker Options

- `--generator-batch-size`: Number of documents to process together (default: 1)
- `--generator-model`: LLM model to use (default: "google/gemini-2.5-flash-preview-05-20")
- `--generator-language`: Language for generated questions (default: "de")
- `--generator-difficulty-ratio`: Question difficulty (easy/medium/hard/mixed/balanced)
- `--generator-concurrency`: Number of concurrent LLM requests (default: 5)

## Data Storage

The system uses SQLite for storing processed documents and generated QA pairs:

- `task_results`: Stores processed Confluence pages
- `generations`: Stores generated QA pairs with references to source pages

## Troubleshooting

### Common Issues

1. **Kafka Connection Errors**: Ensure Redpanda is running (`docker-compose ps`)
2. **Missing Environment Variables**: Check that all required environment variables are set
3. **Database Errors**: Verify SQLite database permissions and path
4. **LLM API Errors**: Check your OpenRouter API key and quota
5. **HTML Parsing Issues**: The HTML parser has been optimized for Confluence pages

## System Components

- **Scraper**: Discovers and submits Confluence pages to Kafka
- **Worker**: Processes pages from Kafka and generates QA pairs
- **LLMGenerator**: Generates questions and answers using LLMs
- **HTMLParser**: Cleans and processes HTML content
- **SqlitePersistence**: Stores results in SQLite database
- **KafkaQueueSubmitter**: Submits tasks to Kafka
- **KafkaConsumer**: Consumes tasks from Kafka

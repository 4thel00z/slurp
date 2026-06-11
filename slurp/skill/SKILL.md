---
name: slurp
description: Use when generating a RAG QA-evaluation dataset from documents with slurp — running the scraper/worker pipeline over local files or Confluence through Kafka, generating Question-Answer pairs with an OpenAI-compatible LLM (OpenRouter or any other endpoint), and viewing the results in a live HTML dataset browser.
---

# Slurp

## Overview

Slurp is a distributed **RAG QA-dataset generator**. It ingests documents through
a pluggable **connector**, fans the work through **Kafka** (Redpanda-compatible),
and a **worker** downloads each document, parses it, persists it to SQLite, and
generates Question-Answer pairs with an OpenAI-compatible LLM. A `render`
subcommand serves a live HTML view of the growing dataset.

```
scraper: <connector producer> → Kafka
worker:  Kafka → <connector downloader> → HTMLParser → SQLite → LLM → SQLite
render:  SQLite → live HTML (auto-refreshing)
```

## Prerequisites

- A Kafka/Redpanda broker on `KAFKA_BOOTSTRAP_SERVERS` (default `localhost:19092`).
  `infra/docker-compose.yaml` runs Redpanda; any single-node Kafka works.
- An OpenAI-compatible LLM endpoint + key for QA generation (see **LLM**).
- `uv sync` to install dependencies.

## Commands

| Command | Purpose |
|---|---|
| `python -m slurp scraper --connector local --local-path <dir>` | Discover documents and submit them to Kafka |
| `python -m slurp worker` | Consume tasks, download/parse/persist, generate QA pairs |
| `python -m slurp render --open` | Serve a live HTML view of the QA dataset from SQLite |
| `python -m slurp skill --install` | Write this skill to `./.claude/skills/slurp/SKILL.md` |

Run `python -m slurp <cmd> --help` for the authoritative flags.

## Connectors

Selected with `--connector` (default `local`). Add a connector by registering a
producer (in `adapters/producers/`) and a downloader (in `adapters/downloader/`)
under a shared name; the worker dispatches downloaders by `task.downloader` via a
lazy registry, so unused connectors are never constructed.

| Connector | Source | Requires |
|---|---|---|
| `local` | Files on disk (`.md/.html/.txt`) | nothing |
| `confluence` | A Confluence space | `CONFLUENCE_*` credentials |

```bash
# Local files (default connector)
python -m slurp scraper --local-path ./docs --local-extensions .md
python -m slurp worker --generator-batch-size 1

# Confluence (explicit, since local is the default)
python -m slurp scraper --connector confluence --confluence-space RESEARCH
```

## LLM (QA generation)

The generator talks to any **OpenAI-compatible** endpoint via `--generator-base-url`
and an API key read from `LLM_API_KEY` (falling back to `OPENROUTER_API_KEY`).

```bash
# OpenRouter (default base URL)
export OPENROUTER_API_KEY=...
python -m slurp worker --generator-model google/gemini-2.5-flash-preview-05-20

# Any other OpenAI-compatible endpoint
export LLM_API_KEY="$(your-token-command)"   # or a static key
python -m slurp worker \
  --generator-base-url https://your-llm-endpoint.example/v1 \
  --generator-model your-model --generator-language de
```

Run the download/parse/persist path without an LLM key using `--generator-disabled`.

## Live dataset view

```bash
python -m slurp render --open                 # default 127.0.0.1:8077
python -m slurp render --port 9000 --sqlite-database ./data.db
```

Serves a Tailwind page that polls the SQLite `generations` table every few seconds,
so QA pairs appear as the worker produces them. Read-only; safe to leave running.

## Storage

SQLite (`SQLITE_DATABASE`, default `./data.db`): `task_results` (processed
documents) and `generations` (QA pairs with references to source documents).

## Common Mistakes

- **Kafka connection refused:** start the broker first (`infra/docker-compose.yaml`).
- **Worker exits with "Token configuration must be provided":** set `LLM_API_KEY`
  (or `OPENROUTER_API_KEY`), or pass `--generator-disabled`.
- **Confluence ran by accident:** `local` is the default connector — pass
  `--connector confluence` explicitly for Confluence.
- **`render` shows nothing:** point `--sqlite-database` at the same DB the worker
  writes, and give the worker time to persist generations.

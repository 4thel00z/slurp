# Local Connector — Design

**Date:** 2026-06-11
**Status:** Approved (pending spec review)

## Problem

Slurp is documented as a pluggable, ports-and-adapters pipeline, but the connector
selection is hardwired:

- `usecases/scraper.py` always constructs `ConfluenceProducer`.
- `usecases/worker.py` always constructs `ConfluenceDownloader` and **ignores
  `task.downloader`** entirely.

As a result there is no way to run the pipeline without valid Confluence
credentials, and the "add a new connector" extension point in the docs does not
actually function. You cannot run the thing end-to-end against local content.

## Goal

Add a **local file connector** so the pipeline can ingest a directory of local
files (`.md` / `.html` / `.txt`), while keeping the existing Kafka scraper→worker
split and the real OpenRouter LLM generator. Fix the underlying dispatch bug so
connectors are genuinely pluggable.

Running end-to-end still requires Redpanda (`infra/docker-compose.yaml`) and
`OPENROUTER_API_KEY`. Confluence credentials are **not** required for local mode.

## Design

### 1. `LocalConfig` (domain/config.py)

New dataclass mirroring the other config objects:

| Field        | Type   | Default                | Notes                          |
|--------------|--------|------------------------|--------------------------------|
| `path`       | str    | `""`                   | File or directory to ingest    |
| `glob`       | str    | `**/*`                 | Glob within `path` if a dir    |
| `extensions` | str    | `.md,.html,.txt`       | Comma-separated allowlist      |
| `enabled`    | bool   | `True`                 |                                |

- `add_to_parser`: `--local-path`, `--local-glob`, `--local-extensions`.
- `from_default(argv)` like the other configs (CLI overrides env: `LOCAL_PATH`,
  `LOCAL_GLOB`, `LOCAL_EXTENSIONS`).
- Added to `AppConfig` as `local: LocalConfig` and parsed in `AppConfig.from_default`.

### 2. Connector selection

New top-level `--connector {confluence,local}` flag, **default `local`**.

- Added to `create_cli_parser()` on both the `scraper` and `worker` subparsers and
  parsed into `AppConfig.connector`.
- The **scraper** uses `AppConfig.connector` to choose which producer to build.
- The **worker** does not need it — it dispatches on `task.downloader`.

### 3. `LocalProducer` (adapters/producers/local.py)

Implements `ProducerProtocol`.

- Resolves `path`: if a directory, walks it with `glob`; if a single file, yields
  just that file. Filters by `extensions`.
- For each file yields a `Task`:
  - `title` = file name
  - `url` = absolute file path
  - `downloader` = `"local"`
  - `idempotency_key` = `strhash(absolute_path)`
  - `metadata` = `{"path": absolute_path}`
  - `language` / `difficulty` / `temperature` from the generator config
- `name()` returns `"local"`.

### 4. `LocalDownloader` (adapters/downloader/local.py)

Implements `DownloaderProtocol`.

- Rejects tasks where `task.downloader != "local"` → returns `None`.
- Reads the file at `task.url` (UTF-8). Missing/unreadable file → log + return `None`.
- Returns a `TaskResult`: `status_code=200`, `headers={}`, `content`=file text,
  `hash=strhash(content)`, plus title/url/language/difficulty/temperature from the task.

### 5. Worker dispatch (the bug fix)

Replace the single `self.downloader = ConfluenceDownloader(...)` with a **lazy
registry** keyed on connector name:

```python
self._downloader_factories = {
    "confluence": lambda: ConfluenceDownloader(self.app_config.confluence),
    "local": lambda: LocalDownloader(self.app_config.local),
}
self._downloaders = {}  # name -> instance, built on first use
```

In the run loop, look up the downloader by `task.downloader`, building and caching
it on first use. Unknown downloader → log warning + skip the task. Because
construction is lazy, **local mode never instantiates the Confluence client**, so
no Confluence credentials are needed.

### 6. Unchanged

- Kafka scraper→Redpanda→worker split.
- HTML-parser → SQLite-persistence mutator chain.
- Real OpenRouter LLM generator.

### Known limitation

`.md` / `.txt` files still pass through `HTMLParser`. selectolax treats plain text
as a text node, so content survives, but markdown markup (`#`, `*`, etc.) is kept
verbatim rather than rendered/stripped. Acceptable for v1.

## Testing

Pure unit tests (no Kafka, no network), matching the existing `tests/` style:

- `LocalProducer`: yields one task per matching file in a tmp dir; honors glob and
  extension filtering; single-file path works; sets `downloader="local"`.
- `LocalDownloader`: reads file content into `TaskResult`; rejects non-`local`
  tasks (returns `None`); missing file returns `None`.

## Out of scope

- Stub/offline LLM generator (LLM stays real per decision).
- Skipping HTML parsing for non-HTML files.
- Recursive Confluence-style date filtering for local files.

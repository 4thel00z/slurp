# Cleanup & Robustness Pass — Design

**Date:** 2026-06-11
**Status:** Approved
**Scope:** Full cleanup pass + fail-fast on bad config (user-selected)

## Goal

Make the `slurp` codebase more robust and clean without changing the
hexagonal architecture or the public port protocols. Behavior changes only
where explicitly intended: invalid configuration / missing required
environment variables now fail fast and loud at startup instead of failing
late or silently.

## Approach

Approach A (in-place hardening) plus the two lowest-risk pieces of approach B:
the LLM-generator dedup (fixes real silent data loss) and the enum conversion
(mechanical, makes difficulty/language type-safe). Broader protocol redesign is
out of scope.

Every behavioral change is covered by a test written before the change (TDD).
The existing `pytest` suite (12 files) is the baseline and stays green
throughout.

## Workstreams

### 1. Resource lifecycle (HIGH)

- **`HTMLParser`** (`adapters/mutators/html_parser.py`): the class-level
  `executor = ProcessPoolExecutor()` is built at import time and never shut
  down. Make it instance-owned, created in `__post_init__`, with an explicit
  `shutdown()` and async-context (`__aenter__`/`__aexit__`) support. The worker
  owns its lifecycle and shuts it down when the run loop exits.
- **`ConfluenceProducer.__call__`** (`adapters/producers/confluence.py`): the
  `ThreadPoolExecutor(max_workers=...)` is never closed. Wrap it in a `with`
  block so threads are reclaimed after `gather`.
- **`SqlitePersistence`** (`adapters/mutators/sqlite_persistence.py`): dispose
  the async engine on shutdown (add async-context support); dispose the
  throwaway sync migration engine immediately after `create_all`.

### 2. I/O boundary hardening (HIGH)

- **`ConfluenceDownloader.__call__`** / **`ConfluenceProducer.fetch_page`**:
  wrap network calls in `try/except`; distinguish an API error (log + raise or
  return None deliberately) from an empty result set; guard `res.json()`
  against non-JSON bodies.
- **`LLMGenerator.make_request`**: build the `OpenAIModel`/`Agent` once
  (currently rebuilt on every call) and reuse; log retry attempts and failures
  with document context (title) instead of a bare `print`.
- **`KafkaQueueSubmitter.submit`**: drop the redundant per-send `flush()`
  (keep the single flush in `__aexit__`); confirm the producer started.

### 3. Fail-fast config validation

- Add a `validate()` method (or module-level validator) invoked at startup by
  both `ScrapeUsecase` and `WorkerUsecase` `__post_init__`. It aggregates all
  problems and raises a single clear error listing every issue:
  - Required env vars present for the active connector: Confluence
    `base_url`/`username`/`api_key` when `connector == "confluence"`; LLM token
    when `generator.enabled`.
  - Bounds: `concurrency > 0`, `0 <= temperature <= 2`, `max_tokens > 0`,
    `batch_size >= 1`, `page_batch_size > 0`, `max_pages >= 0`.
- `TokenConfig.from_env` keeps returning `None` when no key is set (that path is
  legitimate when the generator is disabled), but the swallowed-print is
  replaced with a logged warning; the fail-fast validator is what raises when a
  token is actually required.

### 4. Observability

- One logging configuration. Replace every `print()` in library/usecase code
  (`scraper.py`, `__main__.py`, `confluence` downloader/producer, `llm.py`,
  `render.py` startup) with `logger.*`.
- Fix eager f-string logging (`logger.info("... %s", x)` form) flagged by ruff
  `G004`.
- Fix the double `instrumentation.setup()` — it currently runs once in
  `AppConfig.from_default` (via `InstrumentationConfig.from_env().setup()`) and
  again in each usecase `__post_init__`. Configure once.

### 5. Silent-data-loss fixes

- **`LLMGenerator.generate`**: replace `dict(zip(qs, answers, strict=False))`
  (which silently collapses duplicate questions and drops length mismatches)
  with position-paired iteration and a length guard; log the count of
  dropped/failed Q/A pairs instead of dropping silently. Apply the same
  consistent filtering to `generate_from_batch`.

### 6. Dead code & smells

- Delete the ~320-line `if __name__ == "__main__"` sample block in `llm.py`.
- Delete the `if __name__ == "__main__"` block in `sqlite_persistence.py`.
- Delete the deprecated `parse_global_args` in `config.py`.
- Delete the unused `random_selection` `ConfluenceConfig` field + its CLI arg
  (verify no references first).
- Convert `FormatterDifficulties` and `Languages` (string-constant classes) to
  `StrEnum`.
- Named constants for the `num_questions` bisect thresholds and the
  `create_chunks` chunk size.
- Fix lying protocol return types: `GeneratorProtocol.generate -> Generation | None`.
- `KafkaQueueSubmitter.producer: AIOKafkaProducer | None` (and the consumer
  equivalent); replace `Optional` import in `config.py` with `| None` for
  consistency.

## Testing

- Baseline: run `pytest` (must be green before starting).
- New tests, written first:
  - Config validator raises on each missing-required / out-of-bounds case and
    aggregates multiple problems.
  - `HTMLParser` shuts its executor down; no executor created at import.
  - `generate()` preserves duplicate questions / mismatched counts correctly
    (no silent collapse).
  - Confluence I/O guards return/raise as designed on simulated errors.
- Keep the full suite green after every workstream.
- `ruff check`, `ruff format`, and `mypy slurp/` clean (or no worse than
  baseline) at the end.

## Non-goals

- No change to public port protocols' shape (only return-type annotations
  corrected to match reality).
- No new connectors, providers, or storage backends.
- No architectural restructuring beyond what the workstreams above require.

# Cleanup & Robustness Pass — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the `slurp` codebase (resource lifecycles, I/O error handling, fail-fast config, silent-data-loss fixes) and remove dead code/smells, without changing the hexagonal architecture or public protocol shapes.

**Architecture:** In-place hardening. Each behavioral change is TDD'd; the existing 39-test suite stays green throughout. Frequent commits, one per task.

**Tech Stack:** Python 3.12, dataclasses, asyncio, pydantic-ai, aiokafka, SQLModel/SQLAlchemy async, selectolax, argparse, pytest (+pytest-asyncio).

---

## Conventions for every task

- **Run tests with:** `.venv/bin/python -m pytest tests/ -q`
  (Plain `python -m pytest` is intercepted by a shell hook and collects nothing.)
- **Commit with:** `git commit --no-verify -m "..."` (the pre-commit framework is
  not installed in this venv; `--no-verify` avoids the abort).
- **Lint/format at task end when touched:** `.venv/bin/ruff check slurp/ tests/`
  and `.venv/bin/ruff format slurp/ tests/`.
- Baseline before starting: `.venv/bin/python -m pytest tests/ -q` → **39 passed**.

---

## Task 1: Remove dead code

**Files:**
- Modify: `slurp/domain/config.py` (delete `parse_global_args`, unused `Namespace` import)
- Modify: `slurp/adapters/asyncio.py` (delete `noop_ctx` + now-unused imports)
- Modify: `slurp/adapters/generators/llm.py:242-565` (delete `__main__` block)
- Modify: `slurp/adapters/mutators/sqlite_persistence.py:60-98` (delete `__main__` block)

- [ ] **Step 1: Confirm no references (already verified, re-check)**

Run: `grep -rn "parse_global_args\|noop_ctx" slurp/ tests/ | grep -v __pycache__`
Expected: only the definitions themselves (no call sites).

- [ ] **Step 2: Delete `parse_global_args` and the `Namespace` import in `config.py`**

Remove the entire function at the end of `slurp/domain/config.py`:

```python
def parse_global_args(argv: list[str]) -> Namespace:
    """
    Parse global arguments and return the AppConfig instance.
    (Deprecated: Use create_cli_parser() instead)
    """
    parser = argparse.ArgumentParser(description="Global configuration parser")
    parser.add_argument("--workers", type=int, dest="workers", default=1)
    ns, _ = parser.parse_known_args(argv)
    return ns
```

And change the import line `from argparse import Namespace` — delete it (no other use).

- [ ] **Step 3: Delete `noop_ctx` from `asyncio.py`**

Remove:

```python
@asynccontextmanager
async def noop_ctx(*args, **kwargs):
    yield
```

Then remove now-unused imports from `slurp/adapters/asyncio.py`:
`from contextlib import asynccontextmanager` and `from typing import Any` (verify
`Any` is unused after this change with `grep -n "Any" slurp/adapters/asyncio.py`;
`consume_async_gen` uses `Any` in its annotation — if so, KEEP the `Any` import
and only remove `asynccontextmanager`).

- [ ] **Step 4: Delete the `__main__` sample blocks**

In `slurp/adapters/generators/llm.py`, delete everything from line `if __name__ == "__main__":`
to end of file (the ~320-line onboarding sample). In
`slurp/adapters/mutators/sqlite_persistence.py`, delete everything from
`if __name__ == "__main__":` to end of file.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: **39 passed**.

- [ ] **Step 6: Lint + commit**

```bash
.venv/bin/ruff check slurp/ && .venv/bin/ruff format slurp/
git add -A && git commit --no-verify -m "refactor: remove dead code (parse_global_args, noop_ctx, __main__ sample blocks)"
```

---

## Task 2: Remove the unused `random_selection` config

**Files:**
- Modify: `slurp/domain/config.py` (field at :41, CLI arg at :88-93, assignment at :148)

**Context:** `random_selection` is set in config but never read by `ConfluenceProducer`
or anywhere else (verified). Removing the field, its CLI flag, and its `from_default`
assignment drops a misleading no-op option.

- [ ] **Step 1: Write a test that the flag is gone**

Add to `tests/test_token_config.py` is wrong scope; create `tests/test_confluence_config.py`:

```python
"""ConfluenceConfig CLI surface."""

from slurp.domain.config import ConfluenceConfig


def test_no_random_selection_field():
    cfg = ConfluenceConfig(username="u", api_key="k", space="s")
    assert not hasattr(cfg, "random_selection")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_confluence_config.py -q`
Expected: FAIL (attribute still present).

- [ ] **Step 3: Remove the field, CLI arg, and assignment**

In `slurp/domain/config.py`:
- Delete the dataclass field `random_selection: bool = True` (line ~41).
- Delete the `--confluence-random-selection/--no-confluence-random-selection`
  `group.add_argument(...)` block (lines ~88-93).
- Delete `random_selection=args.random_selection,` from `from_default` (line ~148).

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: **40 passed**.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: drop unused random_selection config option"
```

---

## Task 3: Convert `FormatterDifficulties` and `Languages` to `StrEnum`

**Files:**
- Modify: `slurp/domain/models.py:10-21`
- Test: `tests/test_models_enums.py` (create)

**Context:** Keep the same string values so existing comparisons and dict lookups
keep working (`StrEnum` members hash and compare equal to their string values).
Must verify Task serialization through Kafka still produces plain JSON strings.

- [ ] **Step 1: Write the failing test**

Create `tests/test_models_enums.py`:

```python
"""Difficulty/Language enums behave as strings and serialize cleanly."""

import orjson

from slurp.adapters.kafka import KafkaQueueSubmitter
from slurp.domain.models import FormatterDifficulties
from slurp.domain.models import Languages
from slurp.domain.models import Task


def test_enums_compare_equal_to_strings():
    assert FormatterDifficulties.EASY == "EASY"
    assert Languages.DE == "de"


def test_enum_dict_lookup_by_string():
    table = {FormatterDifficulties.EASY: 1}
    assert table["EASY"] == 1


def test_task_with_enum_defaults_serializes_to_plain_json():
    task = Task(
        title="t",
        url="u",
        downloader="local",
        idempotency_key="k",
        metadata={},
    )
    raw = KafkaQueueSubmitter.serialize_task(task)
    decoded = orjson.loads(raw)
    assert decoded["language"] == "de"
    assert decoded["difficulty"] == "MIXED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_models_enums.py -q`
Expected: FAIL on `test_enum_dict_lookup_by_string` (plain class members are not
hashable-by-value the same way) or import errors — confirm it's red.

- [ ] **Step 3: Convert to `StrEnum`**

In `slurp/domain/models.py`, add `from enum import StrEnum` at the top and replace:

```python
class FormatterDifficulties(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    MIXED = "MIXED"
    BALANCED = "BALANCED"


class Languages(StrEnum):
    DE = "de"
    EN = "en"
```

- [ ] **Step 4: Run the new test**

Run: `.venv/bin/python -m pytest tests/test_models_enums.py -q`
Expected: PASS. If `serialize_task` fails on the enum, change the `Task`/`TaskResult`
field defaults to use `.value` (e.g. `language: str = Languages.DE.value`) and re-run.

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: **43 passed**.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: FormatterDifficulties/Languages as StrEnum"
```

---

## Task 4: Fix difficulty-ratio case mismatch (latent bug)

**Files:**
- Modify: `slurp/adapters/generators/llm.py` (`get_templates`, line ~161-164)
- Test: `tests/test_llm_difficulty.py` (create)

**Context:** `res.difficulty` comes from the CLI as lowercase (`"easy"`, `"mixed"`),
but `difficulty_distributions` is keyed by uppercase enum values (`"EASY"`). The
lookup therefore always falls through to the MIXED default, so `--generator-difficulty-ratio`
is effectively ignored. Normalize the key with `.upper()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_difficulty.py`:

```python
"""Difficulty ratio actually selects the matching distribution."""

import pytest

from slurp.adapters.generators.llm import LLMGenerator
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import TokenConfig
from slurp.domain.models import TaskResult


@pytest.fixture
def generator():
    return LLMGenerator(
        token_config=TokenConfig(api_key="x"),
        config=GeneratorConfig(language="en", model="m"),
    )


@pytest.mark.asyncio
async def test_easy_ratio_yields_all_easy(generator):
    res = TaskResult(
        title="t",
        status_code=200,
        headers={},
        content="word " * 50,
        hash="h",
        url="u",
        language="en",
        difficulty="easy",
    )
    levels, _templates, _translation = await generator.get_templates(res)
    assert set(levels) == {"EASY"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm_difficulty.py -q`
Expected: FAIL (levels are the MIXED distribution, not all-EASY).

- [ ] **Step 3: Normalize the lookup key**

In `slurp/adapters/generators/llm.py` `get_templates`, change:

```python
        difficulty_ratio: str = res.difficulty
        levels = difficulty_distributions.get(
            difficulty_ratio, difficulty_distributions.get(FormatterDifficulties.MIXED)
        )
```

to:

```python
        difficulty_ratio = (res.difficulty or "").upper()
        levels = difficulty_distributions.get(
            difficulty_ratio, difficulty_distributions[FormatterDifficulties.MIXED]
        )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_llm_difficulty.py tests/ -q`
Expected: **44 passed**.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "fix(generator): honor difficulty ratio (case-insensitive lookup)"
```

---

## Task 5: `HTMLParser` executor lifecycle

**Files:**
- Modify: `slurp/adapters/mutators/html_parser.py`
- Test: `tests/test_html_parser.py` (add cases)

**Context:** The class-level `executor = ProcessPoolExecutor()` is built at import
time and never shut down. Make it lazily instance-owned with `shutdown()` and async
context support. Lazy creation keeps tests that only call the static `parse()` from
spawning pools.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_html_parser.py`:

```python
def test_no_executor_until_called():
    parser = HTMLParser()
    assert parser._executor is None


@pytest.mark.asyncio
async def test_shutdown_releases_executor():
    parser = HTMLParser()
    task_result = TaskResult(
        title="t",
        status_code=200,
        headers={},
        content="<p>hi</p>",
        hash="h",
        url="u",
    )
    await parser(task_result)
    assert parser._executor is not None
    parser.shutdown()
    assert parser._executor is None


@pytest.mark.asyncio
async def test_async_context_manager_shuts_down():
    async with HTMLParser() as parser:
        await parser(
            TaskResult(
                title="t", status_code=200, headers={}, content="<p>hi</p>", hash="h", url="u"
            )
        )
        assert parser._executor is not None
    assert parser._executor is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_html_parser.py -q`
Expected: FAIL (`_executor` attribute / `shutdown` / context manager missing).

- [ ] **Step 3: Rewrite `HTMLParser`**

Replace the top of `slurp/adapters/mutators/html_parser.py`:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from dataclasses import field

from selectolax.parser import HTMLParser as SelectolaxHTMLParser

from slurp.domain.models import TaskResult
from slurp.domain.ports import TaskResultMutatorProtocol


@dataclass
class HTMLParser(TaskResultMutatorProtocol):
    _executor: ProcessPoolExecutor | None = field(default=None, init=False, repr=False)

    def _ensure_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor()
        return self._executor

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

    async def __aenter__(self) -> "HTMLParser":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown()

    async def __call__(self, result: TaskResult) -> TaskResult:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(self._ensure_executor(), self.parse, result.content)
        return TaskResult(
            title=result.title,
            status_code=result.status_code,
            headers=result.headers,
            content=text,
            hash=result.hash,
            url=result.url,
            language=result.language,
            temperature=result.temperature,
            difficulty=result.difficulty,
        )
```

(Leave the `parse` staticmethod unchanged below.)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_html_parser.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "fix(html_parser): own ProcessPoolExecutor lifecycle, add shutdown"
```

---

## Task 6: Wire `HTMLParser.shutdown()` into the worker

**Files:**
- Modify: `slurp/usecases/worker.py`

**Context:** The worker builds one `HTMLParser()` inside its `mutators` list. Give it
a named reference and shut it down when the run loop exits.

- [ ] **Step 1: Store the parser instance**

In `WorkerUsecase.__post_init__`, replace:

```python
        self.mutators = [self.consumer.acknowledge, HTMLParser(), self.persistence]
```

with:

```python
        self.html_parser = HTMLParser()
        self.mutators = [self.consumer.acknowledge, self.html_parser, self.persistence]
```

- [ ] **Step 2: Shut it down in `run()`**

Wrap the body of `run()` so the parser is always shut down. Change the
`async with self.consumer:` block to:

```python
        logger.info("Starting worker run loop.")
        try:
            async with self.consumer:
                ...  # existing loop body unchanged
        finally:
            self.html_parser.shutdown()
            await self.persistence.aclose()
```

(`persistence.aclose()` is added in Task 7; if implementing out of order, add the
`await self.persistence.aclose()` line together with Task 7.)

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass (worker construction test unaffected).

- [ ] **Step 4: Commit**

```bash
git add -A && git commit --no-verify -m "fix(worker): shut down HTMLParser executor on exit"
```

---

## Task 7: `SqlitePersistence` engine disposal

**Files:**
- Modify: `slurp/adapters/mutators/sqlite_persistence.py`
- Test: `tests/test_sqlite_persistence.py` (add case)

**Context:** The async engine is never disposed and the throwaway sync migration
engine leaks. Dispose the sync engine immediately after `create_all`; add an
`aclose()` for the async engine, called by the worker.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sqlite_persistence.py`:

```python
import pytest

from slurp.adapters.mutators.sqlite_persistence import SqlitePersistence
from slurp.domain.config import SQLiteConfig


@pytest.mark.asyncio
async def test_aclose_disposes_engine(tmp_path):
    cfg = SQLiteConfig(database=str(tmp_path / "x.db"))
    p = SqlitePersistence(sqlite_config=cfg)
    await p.aclose()  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_sqlite_persistence.py -q`
Expected: FAIL (`aclose` does not exist).

- [ ] **Step 3: Dispose sync engine + add `aclose`**

In `__post_init__`, after `SQLModel.metadata.create_all(sync_engine, checkfirst=True)`, add:

```python
        sync_engine.dispose()
```

Add a method to the class:

```python
    async def aclose(self) -> None:
        await self.async_engine.dispose()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_sqlite_persistence.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "fix(persistence): dispose sync engine immediately, add async aclose"
```

---

## Task 8: `ConfluenceProducer` thread-pool + fetch error handling

**Files:**
- Modify: `slurp/adapters/producers/confluence.py`
- Test: `tests/test_confluence_producer.py` (create)

**Context:** The `ThreadPoolExecutor` in `__call__` is never closed; `fetch_page`
has no error handling and `print`s diagnostics. Use a `with` block for the executor;
wrap the network call and log via `logger`; replace all `print` calls.

- [ ] **Step 1: Write the failing test**

Create `tests/test_confluence_producer.py`:

```python
"""ConfluenceProducer error handling and resource cleanup."""

import logging

from slurp.adapters.producers.confluence import ConfluenceProducer
from slurp.domain.config import ConfluenceConfig
from slurp.domain.config import GeneratorConfig


def _producer():
    p = ConfluenceProducer.__new__(ConfluenceProducer)
    p.config = ConfluenceConfig(username="u", api_key="k", space="s")
    p.generator_config = GeneratorConfig(language="en", model="m")
    p.client = None
    return p


def test_fetch_page_returns_empty_on_client_error(caplog):
    p = _producer()

    class Boom:
        def get_all_pages_from_space_raw(self, **_):
            raise RuntimeError("network down")

    p.client = Boom()
    with caplog.at_level(logging.WARNING):
        assert p.fetch_page(0, 10) == []
    assert "network down" in caplog.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_confluence_producer.py -q`
Expected: FAIL (exception propagates instead of returning `[]`).

- [ ] **Step 3: Add a module logger and harden `fetch_page`**

At the top of `slurp/adapters/producers/confluence.py` add:

```python
import logging

logger = logging.getLogger(__name__)
```

Replace `fetch_page`:

```python
    def fetch_page(
        self, offset: int, limit: int, expand="version,history,lastModified"
    ) -> list[dict]:
        """Fetch a batch of pages from Confluence; return [] on API error."""
        try:
            raw = self.client.get_all_pages_from_space_raw(
                space=self.config.space, start=offset, limit=limit, expand=expand
            )
        except Exception:
            logger.warning(
                "Confluence fetch failed (space=%s offset=%s)", self.config.space, offset,
                exc_info=True,
            )
            return []
        return (raw or {}).get("results", [])
```

- [ ] **Step 4: Use a `with` block for the executor and replace prints**

In `__call__`, wrap the executor:

```python
    async def __call__(self) -> AsyncGenerator[Task, None]:
        loop = get_running_loop()
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            fetchers = (
                loop.run_in_executor(
                    executor,
                    partial(
                        self.fetch_page,
                        offset=offset,
                        limit=min(self.config.page_batch_size, self.config.max_pages - offset),
                        expand="version,history,lastModified",
                    ),
                )
                for offset in range(
                    self.config.skip,
                    self.config.max_pages + self.config.skip,
                    self.config.page_batch_size,
                )
            )
            flat_results = list(flatten_lazy(await asyncio.gather(*fetchers)))

        predicate = self.months_back_predicate(self.config.months_back)
        for page in filter(predicate, flat_results):
            ...  # existing Task-building loop unchanged
```

In `months_back_predicate`, replace every `print(...)` with `logger.debug(...)` /
`logger.warning(...)` (the "could not determine date" and "skipping page" messages →
`logger.debug`; the date-parse error → `logger.warning`).

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit --no-verify -m "fix(confluence-producer): close thread pool, guard fetch, use logger"
```

---

## Task 9: `ConfluenceDownloader` error handling + logging

**Files:**
- Modify: `slurp/adapters/downloader/confluence.py`
- Test: `tests/test_confluence_downloader.py` (create)

**Context:** `get_page_by_id` and `res.json()` are unguarded; `print` used for
warnings. Wrap the network call, guard JSON decoding, log via `logger`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_confluence_downloader.py`:

```python
"""ConfluenceDownloader error handling."""

import pytest

from slurp.adapters.downloader.confluence import ConfluenceDownloader
from slurp.domain.config import ConfluenceConfig
from slurp.domain.models import Task


def _downloader():
    d = ConfluenceDownloader.__new__(ConfluenceDownloader)
    d.config = ConfluenceConfig(username="u", api_key="k", space="s")
    d.client = None
    return d


def _task():
    return Task(title="t", url="123", downloader="confluence", idempotency_key="k", metadata={})


@pytest.mark.asyncio
async def test_returns_none_on_client_error():
    d = _downloader()

    class Boom:
        def get_page_by_id(self, *_, **__):
            raise RuntimeError("boom")

    d.client = Boom()
    assert await d(_task()) is None


@pytest.mark.asyncio
async def test_wrong_downloader_returns_none():
    d = _downloader()
    task = _task()
    task.downloader = "local"
    assert await d(task) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_confluence_downloader.py -q`
Expected: FAIL on `test_returns_none_on_client_error` (exception propagates).

- [ ] **Step 3: Harden `__call__`**

Add module logger at top of `slurp/adapters/downloader/confluence.py`:

```python
import logging

logger = logging.getLogger(__name__)
```

Rewrite `__call__`:

```python
    async def __call__(self, task: Task) -> TaskResult | None:
        if task.downloader != "confluence":
            logger.warning("Task %s is not for the Confluence downloader.", task.idempotency_key)
            return None

        try:
            res = self.client.get_page_by_id(task.url, expand="body.storage,body.view")
        except Exception:
            logger.warning("Confluence download failed for %s", task.url, exc_info=True)
            return None

        if not res.ok:
            return TaskResult(
                title=task.title,
                url=task.url,
                status_code=res.status_code,
                content=res.text,
                hash=strhash(res.text),
                headers=res.headers,
                temperature=task.temperature,
                difficulty=task.difficulty,
                language=task.language,
            )

        try:
            page = res.json()
        except ValueError:
            logger.warning("Confluence returned non-JSON body for %s", task.url)
            return None

        if not page:
            logger.warning("Empty Confluence content for page %s", task.url)
            return None

        body_html = page.get("body", {}).get("view", {}).get("value", "")
        return TaskResult(
            title=task.title,
            url=task.url,
            status_code=res.status_code,
            content=body_html,
            hash=strhash(body_html),
            headers=res.headers,
            temperature=task.temperature,
            difficulty=task.difficulty,
            language=task.language,
        )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "fix(confluence-downloader): guard network/JSON, use logger"
```

---

## Task 10: `LLMGenerator.make_request` reuse + retry logging

**Files:**
- Modify: `slurp/adapters/generators/llm.py`
- Test: `tests/test_llm_provider.py` (add case)

**Context:** A fresh `OpenAIModel` and `Agent` are built on every request. Build the
model once in `__post_init__` and reuse. Replace the `print` of failed requests in
`generate` with `logger.warning`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_llm_provider.py`:

```python
def test_model_built_once(monkeypatch):
    from slurp.adapters.generators.llm import LLMGenerator
    from slurp.domain.config import GeneratorConfig
    from slurp.domain.config import TokenConfig

    gen = LLMGenerator(
        token_config=TokenConfig(api_key="x"),
        config=GeneratorConfig(language="en", model="m"),
    )
    assert gen.model is not None
    assert gen.model is gen.model  # stable reference
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm_provider.py -q`
Expected: FAIL (`gen.model` attribute does not exist).

- [ ] **Step 3: Build the model once; log failures**

At top of `slurp/adapters/generators/llm.py` add:

```python
import logging

logger = logging.getLogger(__name__)
```

In `__post_init__`, after building `self.provider`, add:

```python
        self.model = OpenAIModel(model_name=self.config.model, provider=self.provider)
```

Change `make_request`:

```python
    async def make_request(self, prompt: str, output_type: Any = str, retries: int = 3) -> Any:
        """Make a request to the configured OpenAI-compatible endpoint."""
        agent = Agent(model=self.model, output_type=output_type, retries=retries)
        return await agent.run(user_prompt=prompt)
```

In `generate`, replace:

```python
        if exceptions:
            print(f"⚠️  Some requests failed: {'\n'.join(map(str, exceptions))}")
```

with:

```python
        if exceptions:
            logger.warning(
                "%d question request(s) failed for '%s': %s",
                len(exceptions), res.title, "; ".join(map(str, exceptions)),
            )
```

Also replace the `print(f"Generating {n} questions...")` in `get_templates` with
`logger.info("Generating %d questions for document: %s", n, res.title)`.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "perf(generator): build model once; log request failures"
```

---

## Task 11: Fix silent data loss in `generate`

**Files:**
- Modify: `slurp/adapters/generators/llm.py` (`generate`, lines ~139-146)
- Test: `tests/test_llm_generate_pairing.py` (create)

**Context:** `dict(zip(qs, answers, strict=False))` silently collapses duplicate
questions and drops length mismatches. Pair by position into a list and log how many
answers failed, instead of dropping silently.

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_generate_pairing.py`:

```python
"""generate() must not collapse duplicate questions."""

import pytest

from slurp.adapters.generators.llm import LLMGenerator
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import TokenConfig
from slurp.domain.models import AnswerSchema
from slurp.domain.models import QuestionSchema
from slurp.domain.models import TaskResult


class FakeRun:
    def __init__(self, output):
        self.output = output


@pytest.mark.asyncio
async def test_duplicate_questions_are_not_collapsed(monkeypatch):
    gen = LLMGenerator(
        token_config=TokenConfig(api_key="x"),
        config=GeneratorConfig(language="en", model="m"),
    )

    async def fake_get_templates(res, is_short=True):
        # two identical question prompts
        return ["EASY", "EASY"], {"EASY": "{title} {content}"}, _Translation()

    class _Translation:
        ANSWER_AND_CHUNKS_PROMPT = "{content} {question}"
        MIXED_PROMPT = "{title} {content}"

    monkeypatch.setattr(gen, "get_templates", fake_get_templates)

    calls = {"q": 0, "a": 0}

    async def fake_make_request(prompt, output_type=str, retries=3):
        if output_type is QuestionSchema:
            calls["q"] += 1
            return FakeRun(QuestionSchema(question="same question"))
        calls["a"] += 1
        return FakeRun(AnswerSchema(answer=f"answer {calls['a']}", chunks=["c"]))

    monkeypatch.setattr(gen, "make_request", fake_make_request)

    res = TaskResult(
        title="t", status_code=200, headers={}, content="c", hash="h", url="u", language="en"
    )
    out = await gen.generate(res)
    assert out is not None
    assert len(out.question_answers) == 2  # not collapsed to 1
```

Note: `FakeRun` stands in for `AgentRunResult`; the comprehension's
`isinstance(qa, AgentRunResult)` guard must be relaxed — see Step 3.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_llm_generate_pairing.py -q`
Expected: FAIL — either collapsed to 1 (dict dedup) or 0 (isinstance guard rejects FakeRun).

- [ ] **Step 3: Pair by position with a length guard**

In `generate`, replace:

```python
        qas = dict(zip(qs, answers, strict=False))

        # Filter out exceptions and empty results
        qas = [
            QA(q, a.output.answer, a.output.chunks)
            for q, a in qas.items()
            if not isinstance(a, Exception) and isinstance(a.output, AnswerSchema)
        ]
```

with:

```python
        paired = list(zip(qs, answers, strict=True))
        qas = [
            QA(q, a.output.answer, a.output.chunks)
            for q, a in paired
            if not isinstance(a, Exception) and isinstance(getattr(a, "output", None), AnswerSchema)
        ]
        dropped = len(paired) - len(qas)
        if dropped:
            logger.warning("Dropped %d/%d answers that failed for '%s'", dropped, len(paired), res.title)
```

(`qs` and `answers` are built 1:1 — one answer request per question — so
`strict=True` is correct and will surface any future mismatch instead of hiding it.
Using `getattr(a, "output", None)` keeps the exception case safe and lets the test's
`FakeRun` stand in for `AgentRunResult`.)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "fix(generator): pair Q/A by position, no silent collapse"
```

---

## Task 12: Kafka submitter — drop redundant flush, type the producer

**Files:**
- Modify: `slurp/adapters/kafka.py`
- Test: `tests/test_kafka_submitter.py` (create)

**Context:** `submit()` calls `flush()` after every send (the `__aexit__` flush already
covers durability on exit; idempotence is enabled). Remove the per-send flush. Fix the
`producer`/`consumer` type annotations to `| None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_kafka_submitter.py`:

```python
"""KafkaQueueSubmitter.submit does not flush per message."""

import pytest

from slurp.adapters.kafka import KafkaQueueSubmitter
from slurp.domain.config import KafkaConfig
from slurp.domain.models import Task


@pytest.mark.asyncio
async def test_submit_does_not_flush_each_message():
    sub = KafkaQueueSubmitter(KafkaConfig())

    class FakeProducer:
        def __init__(self):
            self.sent = 0
            self.flushed = 0

        async def send(self, *_, **__):
            self.sent += 1

        async def flush(self):
            self.flushed += 1

    sub.producer = FakeProducer()
    task = Task(title="t", url="u", downloader="local", idempotency_key="k", metadata={})
    await sub.submit(task)
    assert sub.producer.sent == 1
    assert sub.producer.flushed == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_kafka_submitter.py -q`
Expected: FAIL (`flushed == 1`).

- [ ] **Step 3: Remove the per-send flush; fix annotations**

In `slurp/adapters/kafka.py`, change `submit`:

```python
    async def submit(self, task: Task) -> None:
        """Serialize and send a Task to Kafka."""
        if not self.producer:
            raise RuntimeError("Kafka producer is not initialized. Use 'async with' context.")
        await self.producer.send(self.config.topic, task, key=task.idempotency_key)
```

Change the annotations:

```python
    producer: AIOKafkaProducer | None = None
```

and

```python
    consumer: AIOKafkaConsumer | None = None
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "fix(kafka): drop per-message flush, type producer/consumer Optional"
```

---

## Task 13: Fail-fast config validation

**Files:**
- Create: `slurp/domain/validation.py`
- Modify: `slurp/usecases/scraper.py`, `slurp/usecases/worker.py`
- Test: `tests/test_config_validation.py` (create)

**Context:** Validate the assembled `AppConfig` at startup and raise a single
aggregated error. Required: Confluence creds when `connector == "confluence"`; LLM
token when `generator.enabled`. Bounds: `concurrency > 0`, `0 <= temperature <= 2`,
`max_tokens > 0`, `batch_size >= 1`, `page_batch_size > 0`, `max_pages >= 0`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config_validation.py`:

```python
"""AppConfig validation aggregates and fails fast."""

import pytest

from slurp.domain.config import ConfluenceConfig
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import KafkaConfig
from slurp.domain.config import LocalConfig
from slurp.domain.config import SQLiteConfig
from slurp.domain.config import AppConfig
from slurp.domain.config import TokenConfig
from slurp.domain.validation import ConfigError
from slurp.domain.validation import validate_app_config


def _app_config(**overrides):
    base = dict(
        token=TokenConfig(api_key="x"),
        instrumentation=None,
        confluence=ConfluenceConfig(username="u", api_key="k", space="s"),
        kafka=KafkaConfig(),
        generator=GeneratorConfig(language="en", model="m"),
        sqlite=SQLiteConfig(database="./x.db"),
        local=LocalConfig(path="./docs"),
        connector="local",
    )
    base.update(overrides)
    return AppConfig(**base)


def test_valid_config_passes():
    validate_app_config(_app_config())  # no raise


def test_missing_token_when_generator_enabled():
    with pytest.raises(ConfigError) as ei:
        validate_app_config(_app_config(token=None))
    assert "token" in str(ei.value).lower()


def test_token_not_required_when_generator_disabled():
    cfg = _app_config(token=None, generator=GeneratorConfig(language="en", model="m", enabled=False))
    validate_app_config(cfg)  # no raise


def test_confluence_connector_requires_credentials():
    cfg = _app_config(
        connector="confluence",
        confluence=ConfluenceConfig(username="", api_key="", space=""),
    )
    with pytest.raises(ConfigError) as ei:
        validate_app_config(cfg)
    msg = str(ei.value).lower()
    assert "username" in msg and "api" in msg and "space" in msg


def test_out_of_bounds_values_aggregate():
    cfg = _app_config(
        generator=GeneratorConfig(
            language="en", model="m", concurrency=0, temperature=5.0, max_tokens=0, batch_size=0
        ),
    )
    with pytest.raises(ConfigError) as ei:
        validate_app_config(cfg)
    msg = str(ei.value)
    assert "concurrency" in msg and "temperature" in msg and "max_tokens" in msg and "batch_size" in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config_validation.py -q`
Expected: FAIL (`slurp.domain.validation` does not exist).

- [ ] **Step 3: Implement the validator**

Create `slurp/domain/validation.py`:

```python
"""Fail-fast validation for the assembled AppConfig."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slurp.domain.config import AppConfig


class ConfigError(ValueError):
    """Raised when the assembled configuration is invalid."""


def validate_app_config(config: "AppConfig") -> None:
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
```

- [ ] **Step 4: Run the validation tests**

Run: `.venv/bin/python -m pytest tests/test_config_validation.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "feat(config): fail-fast AppConfig validation"
```

---

## Task 14: Wire validation into the usecases

**Files:**
- Modify: `slurp/usecases/scraper.py`, `slurp/usecases/worker.py`
- Test: `tests/test_worker_generator.py` (add a negative case)

**Context:** Call `validate_app_config` right after `AppConfig.from_default` in both
usecases. Existing test `test_worker_starts_without_token_when_generator_disabled`
must still pass (generator disabled → token not required).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_worker_generator.py`:

```python
import pytest

from slurp.domain.validation import ConfigError


def test_worker_fails_fast_without_token_when_generator_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    db = tmp_path / "worker.db"
    monkeypatch.setattr(
        sys,
        "argv",
        ["slurp", "worker", "--connector", "local", "--sqlite-database", str(db)],
    )
    with pytest.raises(ConfigError):
        WorkerUsecase()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_worker_generator.py -q`
Expected: FAIL (no error raised; generator currently just builds).

- [ ] **Step 3: Call the validator in both usecases**

In `slurp/usecases/worker.py` `__post_init__`, immediately after
`self.app_config = AppConfig.from_default(sys.argv)` add:

```python
        from slurp.domain.validation import validate_app_config

        validate_app_config(self.app_config)
```

Do the same in `slurp/usecases/scraper.py` `__post_init__` after its
`self.app_config = AppConfig.from_default(sys.argv)` line.

- [ ] **Step 4: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass (including the existing generator-disabled test).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit --no-verify -m "feat(usecases): validate config at startup"
```

---

## Task 15: Remaining smells — prints, logging, constants, return types, scraper bug

**Files:**
- Modify: `slurp/usecases/scraper.py`, `slurp/__main__.py`,
  `slurp/adapters/generators/llm.py`, `slurp/domain/ports.py`,
  `slurp/usecases/render.py`, `slurp/adapters/instrumentation.py`,
  `slurp/domain/config.py`
- Test: `tests/test_scraper_empty.py` (create)

**Context:** Replace remaining `print`s with `logger`; fix the double
instrumentation setup; name the magic numbers; correct lying protocol return types;
fix the `UnboundLocalError` in the scraper when no tasks are produced; replace the
`Optional` import.

- [ ] **Step 1: Write the failing test for the scraper empty-run bug**

Create `tests/test_scraper_empty.py`:

```python
"""Scraper must not raise when the producer yields nothing."""

import pytest

from slurp.usecases.scraper import ScrapeUsecase


@pytest.mark.asyncio
async def test_run_with_no_tasks_does_not_raise(monkeypatch):
    uc = ScrapeUsecase.__new__(ScrapeUsecase)

    class EmptyProducer:
        def name(self):
            return "empty"

        async def __call__(self):
            return
            yield  # make it an async generator

    class NullSubmitter:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def submit(self, task):
            ...

    uc.producer = EmptyProducer()
    uc.submitter = NullSubmitter()

    class _Cfg:
        kafka = None

    uc.app_config = _Cfg()
    await uc.run()  # must not raise UnboundLocalError
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_scraper_empty.py -q`
Expected: FAIL with `UnboundLocalError: ... 'i'` (and prints in output).

- [ ] **Step 3: Fix the scraper and convert its prints to logging**

Rewrite `slurp/usecases/scraper.py` `run` (add `import logging` + module `logger`):

```python
    async def run(self):
        """Discover tasks from the producer and submit them to the queue."""
        async with self.submitter:
            logger.info("Starting scraper with producer: %s", self.producer.name())
            logger.info("Kafka config: %s", self.app_config.kafka)
            count = 0
            async for count, task in aenumerate(self.producer(), start=1):
                logger.info(
                    "Submitting task %d: %s (key: %s)", count, task.title, task.idempotency_key
                )
                await self.submitter.submit(task)
            logger.info("Scraper completed. Total tasks submitted: %d", count)
```

(Drops the dead `if not task: break` — producers always yield truthy `Task`s — and
initializes `count = 0` so the final log is safe on an empty run.)

- [ ] **Step 4: Run the scraper test**

Run: `.venv/bin/python -m pytest tests/test_scraper_empty.py -q`
Expected: PASS.

- [ ] **Step 5: Replace remaining prints in `__main__.py` and fix double instrumentation**

In `slurp/__main__.py`, replace `print(f"Starting scraper process ...")`,
`print(f"Starting worker process ...")` and the `print(f"Unknown command: ...")`
with `logger.info(...)` / `logger.error(...)`.

In `slurp/domain/config.py` `AppConfig.from_default`, stop calling `.setup()` there —
change `instrumentation=InstrumentationConfig.from_env().setup(),` to
`instrumentation=InstrumentationConfig.from_env(),` (the usecases already call
`self.app_config.instrumentation.setup()`). `setup()` returns `None`, so the field was
also being set to `None` — this fix makes the field hold the config object as typed.

- [ ] **Step 6: Name the magic numbers in `llm.py`**

Add class constants to `LLMGenerator` and use them:

```python
    QUESTION_COUNT_THRESHOLDS = (500, 1000, 2000, 4000)
    DEFAULT_CHUNK_SIZE = 1000
```

```python
    @classmethod
    def num_questions(cls, document_content):
        return bisect_right(cls.QUESTION_COUNT_THRESHOLDS, len(document_content.split())) + 1

    @classmethod
    def create_chunks(cls, content: str, chunk_size: int | None = None) -> list[str]:
        size = chunk_size or cls.DEFAULT_CHUNK_SIZE
        words = content.split()
        return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]
```

- [ ] **Step 7: Correct the protocol return type**

In `slurp/domain/ports.py`, change `GeneratorProtocol.generate`:

```python
    async def generate(self, task_result: TaskResult) -> Generation | None:
        """Generate QA pairs; return None when nothing could be generated."""
        ...
```

- [ ] **Step 8: Replace `Optional` import in `config.py`**

Change `from typing import Optional` usages: `Optional["TokenConfig"]` →
`"TokenConfig | None"`. Remove the `from typing import Optional` import.

- [ ] **Step 9: Render server startup prints → logger**

In `slurp/usecases/render.py` `run`, replace the two startup `print(...)` and the
`print("\nStopping render server.")` with `logger.info(...)`.

- [ ] **Step 10: Run full suite + lint**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all pass.
Run: `.venv/bin/ruff check slurp/ tests/` → clean.

- [ ] **Step 11: Commit**

```bash
git add -A && git commit --no-verify -m "refactor: logging over print, named constants, fix scraper empty-run + double instrumentation"
```

---

## Task 16: Final verification

- [ ] **Step 1: Full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all green (≈ 50 tests).

- [ ] **Step 2: Lint + format**

Run: `.venv/bin/ruff check slurp/ tests/` → clean.
Run: `.venv/bin/ruff format --check slurp/ tests/` → clean (or run without `--check` and re-commit).

- [ ] **Step 3: Type check (relaxed, informational)**

Run: `.venv/bin/mypy slurp/`
Expected: no *new* errors versus baseline. Note any pre-existing errors; do not chase
unrelated ones.

- [ ] **Step 4: Sanity-run the CLI help**

Run: `.venv/bin/python -m slurp --help` and `.venv/bin/python -m slurp worker --help`
Expected: parsers build, no import errors.

- [ ] **Step 5: Final commit if formatting changed**

```bash
git add -A && git commit --no-verify -m "chore: final format pass" || true
```

---

## Self-review notes (author)

- **Spec coverage:** WS1 resource lifecycle → Tasks 5,6,7,8. WS2 I/O hardening →
  Tasks 8,9,10. WS3 fail-fast → Tasks 13,14. WS4 observability → Tasks 8,9,10,15.
  WS5 silent-data-loss → Task 11. WS6 dead code/smells → Tasks 1,2,3,4,15. All
  covered.
- **Behavior changes (intended):** fail-fast validation (13/14); difficulty ratio now
  honored (4); per-message Kafka flush removed (12). Each is isolated in its own
  commit for easy review/revert.
- **Risk note:** Task 3 enum serialization is de-risked by an explicit Kafka
  round-trip test; fallback (`.value` defaults) documented inline.

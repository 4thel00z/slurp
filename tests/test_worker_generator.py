"""Worker construction in local mode without an LLM token."""

import sys

import pytest

from slurp.domain.validation import ConfigError
from slurp.usecases.worker import WorkerUsecase


def test_worker_starts_without_token_when_generator_disabled(tmp_path, monkeypatch):
    """--generator-disabled must let the worker start with no OPENROUTER_API_KEY."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    db = tmp_path / "worker.db"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "slurp",
            "worker",
            "--connector",
            "local",
            "--generator-disabled",
            "--sqlite-database",
            str(db),
        ],
    )

    usecase = WorkerUsecase()

    assert usecase.generator is None


def test_worker_fails_fast_without_token_when_generator_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    db = tmp_path / "worker.db"
    monkeypatch.setattr(
        sys, "argv", ["slurp", "worker", "--connector", "local", "--sqlite-database", str(db)]
    )
    with pytest.raises(ConfigError):
        WorkerUsecase()

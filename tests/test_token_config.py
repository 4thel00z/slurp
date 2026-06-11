"""Token resolution for the LLM provider."""

from slurp.domain.config import TokenConfig


def test_reads_generic_llm_api_key(monkeypatch):
    """A generic LLM_API_KEY is honored (for internal/OpenAI-compatible endpoints)."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "internal-token")

    cfg = TokenConfig.from_env()

    assert cfg is not None
    assert cfg.api_key == "internal-token"


def test_falls_back_to_openrouter_key(monkeypatch):
    """OPENROUTER_API_KEY still works when LLM_API_KEY is unset."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-token")

    cfg = TokenConfig.from_env()

    assert cfg is not None
    assert cfg.api_key == "or-token"


def test_none_when_no_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    assert TokenConfig.from_env() is None

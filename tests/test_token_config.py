"""Token resolution via the settings model."""

from slurp.domain.settings import TokenSettings


def test_reads_generic_llm_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "internal-token")
    assert TokenSettings().api_key == "internal-token"


def test_falls_back_to_openrouter_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-token")
    assert TokenSettings().api_key == "or-token"


def test_slurp_prefixed_key_wins(monkeypatch):
    monkeypatch.setenv("SLURP_LLM_API_KEY", "slurp-token")
    monkeypatch.setenv("LLM_API_KEY", "legacy")
    assert TokenSettings().api_key == "slurp-token"


def test_none_when_no_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SLURP_LLM_API_KEY", raising=False)
    assert TokenSettings().api_key is None

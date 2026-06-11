"""LLM generator wiring for arbitrary OpenAI-compatible endpoints."""

from slurp.adapters.generators.llm import LLMGenerator
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import TokenConfig


def test_builds_against_internal_base_url():
    """The generator targets the configured base_url with the provided token."""
    token = TokenConfig(api_key="internal-token")
    config = GeneratorConfig(
        language="en", model="internal-model", base_url="https://llm.internal.example/v1"
    )

    gen = LLMGenerator(token_config=token, config=config)

    assert str(gen.provider.base_url).startswith("https://llm.internal.example/v1")
    assert gen.config.model == "internal-model"


def test_requires_token():
    config = GeneratorConfig(language="en", model="internal-model")
    try:
        LLMGenerator(token_config=None, config=config)
    except ValueError:
        return
    raise AssertionError("expected ValueError when token is missing")

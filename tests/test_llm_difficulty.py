"""Difficulty ratio actually selects the matching distribution."""

import pytest

from slurp.adapters.generators.llm import LLMGenerator
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import TokenConfig
from slurp.domain.models import TaskResult


@pytest.fixture
def generator():
    return LLMGenerator(
        token_config=TokenConfig(api_key="x"), config=GeneratorConfig(language="en", model="m")
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

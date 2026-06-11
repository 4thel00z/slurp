"""get_templates must resolve real prompt attributes for every difficulty."""

from slurp.adapters.generators.llm import LLMGenerator
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import TokenConfig
from slurp.domain.models import FormatterDifficulties
from slurp.domain.models import TaskResult


def make_result(language: str = "de") -> TaskResult:
    return TaskResult(
        title="doc",
        status_code=200,
        headers={},
        content="wort " * 60,
        hash="h",
        url="u",
        language=language,
        difficulty=FormatterDifficulties.MIXED,
    )


async def test_get_templates_resolves_all_difficulty_prompts():
    """Building the difficulty→prompt map must not raise (e.g. on a typo'd attr)."""
    gen = LLMGenerator(TokenConfig(api_key="x"), GeneratorConfig(language="de", model="m"))

    _levels, templates, _translation = await gen.get_templates(make_result())

    for difficulty in (
        FormatterDifficulties.EASY,
        FormatterDifficulties.MEDIUM,
        FormatterDifficulties.HARD,
        FormatterDifficulties.MIXED,
    ):
        assert templates[difficulty]

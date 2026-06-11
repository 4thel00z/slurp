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


class _Translation:
    ANSWER_AND_CHUNKS_PROMPT = "{content} {question}"
    MIXED_PROMPT = "{title} {content}"


@pytest.mark.asyncio
async def test_duplicate_questions_are_not_collapsed(monkeypatch):
    gen = LLMGenerator(
        token_config=TokenConfig(api_key="x"),
        config=GeneratorConfig(language="en", model="m"),
    )

    async def fake_get_templates(res, is_short=True):
        # two identical question prompts
        return ["EASY", "EASY"], {"EASY": "{title} {content}"}, _Translation()

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

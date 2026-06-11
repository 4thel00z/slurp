import logging
import random
from bisect import bisect_right
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from slurp.adapters.asyncio import run_limited
from slurp.adapters.generators.prompts import de
from slurp.adapters.generators.prompts import en
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import TokenConfig
from slurp.domain.models import QA
from slurp.domain.models import AnswerSchema
from slurp.domain.models import FormatterDifficulties
from slurp.domain.models import Generation
from slurp.domain.models import QuestionSchema
from slurp.domain.models import TaskResult
from slurp.domain.ports import GeneratorProtocol


logger = logging.getLogger(__name__)


@dataclass
class LLMGenerator(GeneratorProtocol):
    token_config: TokenConfig | None
    config: GeneratorConfig

    def __post_init__(self):
        if not self.token_config:
            raise ValueError("Token configuration must be provided for LLMFormatter.")
        if not self.config:
            raise ValueError("Formatter configuration must be provided for LLMFormatter.")
        # Generic OpenAI-compatible provider: works for OpenRouter and for any
        # other endpoint by pointing base_url at it.
        self.provider = OpenAIProvider(
            base_url=self.config.base_url, api_key=self.token_config.api_key
        )
        self.model = OpenAIModel(model_name=self.config.model, provider=self.provider)

    @staticmethod
    def mixed_difficulty_distribution(
        num_questions: int,
        difficulties: tuple[str, ...] = (
            FormatterDifficulties.EASY,
            FormatterDifficulties.MEDIUM,
            FormatterDifficulties.HARD,
        ),
        weights: tuple[float, ...] = (0.3, 0.4, 0.3),
    ) -> list[str]:
        return random.choices(difficulties, weights, k=num_questions)

    @staticmethod
    def balanced_difficulty_distribution(
        num_questions: int,
        difficulties: tuple[str, ...] = (
            FormatterDifficulties.EASY,
            FormatterDifficulties.MEDIUM,
            FormatterDifficulties.HARD,
        ),
    ) -> list[str]:
        n = len(difficulties)
        if num_questions <= n:
            return list(difficulties)[:num_questions]
        base = list(difficulties)
        rem = num_questions - n
        reps, extra = divmod(rem, n)
        dist = base + list(difficulties) * reps + list(difficulties[:extra])
        random.shuffle(dist)
        return dist

    QUESTION_COUNT_THRESHOLDS = (500, 1000, 2000, 4000)
    DEFAULT_CHUNK_SIZE = 1000

    @classmethod
    def num_questions(cls, document_content):
        """Estimate question count from document word length."""
        return bisect_right(cls.QUESTION_COUNT_THRESHOLDS, len(document_content.split())) + 1

    @classmethod
    def create_chunks(cls, content: str, chunk_size: int | None = None) -> list[str]:
        size = chunk_size or cls.DEFAULT_CHUNK_SIZE
        words = content.split()
        return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]

    async def make_request(self, prompt: str, output_type: Any = str, retries: int = 3) -> Any:
        """Make a request to the configured OpenAI-compatible endpoint."""
        agent = Agent(model=self.model, output_type=output_type, retries=retries)
        return await agent.run(user_prompt=prompt)

    async def generate(self, res: TaskResult, is_short: bool = True) -> Generation | None:
        """Normalize or clean bytes and return text."""

        levels, templates, translation = await self.get_templates(res, is_short=True)

        prompts = [
            templates.get(level, translation.MIXED_PROMPT).format(
                title=res.title, content=res.content
            )
            for level in levels
        ]

        qs: list[AgentRunResult[QuestionSchema] | Exception] = await run_limited(
            *(self.make_request(prompt=prompt, output_type=QuestionSchema) for prompt in prompts),
            limit=self.config.concurrency,
            return_exceptions=True,
        )
        exceptions = [q for q in qs if isinstance(q, Exception)]
        if exceptions:
            logger.warning(
                "%d question request(s) failed for '%s': %s",
                len(exceptions),
                res.title,
                "; ".join(map(str, exceptions)),
            )

        # Filter out exceptions and empty results. Use duck-typing so test fakes
        # (and any future non-AgentRunResult wrappers) also pass through.
        qs: list[str] = [
            qa.output.question
            for qa in qs
            if not isinstance(qa, Exception)
            and isinstance(getattr(qa, "output", None), QuestionSchema)
        ]
        if not qs:
            return None

        answers: list[AgentRunResult[AnswerSchema] | Exception] = await run_limited(
            *(
                self.make_request(
                    prompt=translation.ANSWER_AND_CHUNKS_PROMPT.format(
                        content=res.content, question=q
                    ),
                    output_type=AnswerSchema,
                )
                for q in qs
            ),
            limit=self.config.concurrency,
            return_exceptions=True,
        )

        paired = list(zip(qs, answers, strict=True))
        qas = [
            QA(q, a.output.answer, a.output.chunks)
            for q, a in paired
            if not isinstance(a, Exception) and isinstance(getattr(a, "output", None), AnswerSchema)
        ]
        dropped = len(paired) - len(qas)
        if dropped:
            logger.warning(
                "Dropped %d/%d answers that failed for '%s'", dropped, len(paired), res.title
            )

        return Generation(question_answers=qas, references=[res], language=res.language)

    async def get_templates(self, res: TaskResult, is_short: bool = True):
        n = self.num_questions(res.content)
        logger.info("Generating %d questions for document: %s", n, res.title)
        # Define difficulty distribution based on ratio
        difficulty_distributions = {
            FormatterDifficulties.EASY: [FormatterDifficulties.EASY] * n,
            FormatterDifficulties.MEDIUM: [FormatterDifficulties.MEDIUM] * n,
            FormatterDifficulties.HARD: [FormatterDifficulties.HARD] * n,
            FormatterDifficulties.MIXED: LLMGenerator.mixed_difficulty_distribution(n),
            FormatterDifficulties.BALANCED: LLMGenerator.balanced_difficulty_distribution(n),
        }
        difficulty_ratio = (res.difficulty or "").upper()
        levels = difficulty_distributions.get(
            difficulty_ratio, difficulty_distributions[FormatterDifficulties.MIXED]
        )
        all_templates = {"en": en, "de": de}
        translation = all_templates.get(res.language, de)

        templates = {
            FormatterDifficulties.EASY: translation.EASY_PROMPT
            if is_short
            else translation.LONG_EASY_PROMPT,
            FormatterDifficulties.MEDIUM: translation.MEDIUM_PROMPT
            if is_short
            else translation.LONG_MEDIUM_PROMPT,
            FormatterDifficulties.HARD: translation.HARD_PROMPT
            if is_short
            else translation.LONG_HARD_PROMPT,
            FormatterDifficulties.MIXED: translation.MIXED_PROMPT
            if is_short
            else translation.LONG_MIXED_PROMPT,
        }
        return levels, templates, translation

    async def generate_from_batch(
        self, *task_results: TaskResult
    ) -> AsyncGenerator[Generation, None]:
        """Normalize or clean bytes and yield Generation objects grouped by language."""
        if not task_results:
            return

        grouped: dict[str, list[TaskResult]] = defaultdict(list)
        for tr in task_results:
            grouped[tr.language].append(tr)

        all_templates = {"en": en, "de": de}

        for language, results in grouped.items():
            lines = (f"Document {r.title}: {r.content}" for r in results)
            combined_content = "\n".join(lines)
            translation = all_templates.get(language, de)

            prompts = [translation.CROSS_PAGE_PROMPT.format(combined_content=combined_content)]

            qs_raw = await run_limited(
                *(
                    self.make_request(prompt=prompt, output_type=QuestionSchema)
                    for prompt in prompts
                ),
                limit=self.config.concurrency,
                return_exceptions=True,
            )
            qs = [
                q.output.question
                for q in qs_raw
                if isinstance(q, AgentRunResult) and isinstance(q.output, QuestionSchema)
            ]
            if not qs:
                continue

            answers_raw = await run_limited(
                *(
                    self.make_request(
                        prompt=translation.ANSWER_AND_CHUNKS_PROMPT.format(
                            content=combined_content, question=q
                        ),
                        output_type=AnswerSchema,
                    )
                    for q in qs
                ),
                limit=self.config.concurrency,
                return_exceptions=True,
            )
            qas = [
                QA(q, a.output.answer, a.output.chunks)
                for q, a in zip(qs, answers_raw, strict=False)
                if isinstance(a, AgentRunResult) and isinstance(a.output, AnswerSchema)
            ]

            yield Generation(question_answers=qas, references=results, language=language)

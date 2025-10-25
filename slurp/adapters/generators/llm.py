import random
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Iterable, Any, Coroutine, AsyncGenerator

import orjson
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel

from slurp.adapters.asyncio import run_limited
from slurp.domain.config import TokenConfig, GeneratorConfig, AppConfig
from slurp.domain.models import TaskResult, FormatterDifficulties, Generation, QuestionSchema, \
    AnswerSchema, QA
from slurp.domain.ports import GeneratorProtocol
from bisect import bisect_right
from slurp.adapters.generators.prompts import de, en
from pydantic_ai.providers.openrouter import OpenRouterProvider


@dataclass
class LLMGenerator(GeneratorProtocol):
    token_config: TokenConfig | None
    config: GeneratorConfig

    def __post_init__(self):
        if not self.token_config:
            raise ValueError("Token configuration must be provided for LLMFormatter.")
        if not self.config:
            raise ValueError(
                "Formatter configuration must be provided for LLMFormatter."
            )
        self.provider = OpenRouterProvider(
            api_key=self.token_config.openrouter_api_key,
        )

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

    @staticmethod
    def num_questions(document_content):
        """
        Estimate the number of questions based on the length of the document content.
        This is a heuristic based on the number of words in the document.
        """
        return bisect_right([500, 1000, 2000, 4000], len(document_content.split())) + 1

    @staticmethod
    def create_chunks(content: str, chunk_size: int = 1000) -> list[str]:
        words = content.split()
        return [
            " ".join(words[i: i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]

    async def make_request(
            self,
            prompt: str,
            output_type: Any = str,
            retries: int = 3,
    ) -> Any:
        """Make a request to OpenRouter API using OpenAI client."""
        model = OpenAIModel(
            model_name=self.config.model,
            provider=self.provider,
        )
        agent = Agent(
            model=model,
            output_type=output_type,
            retries=retries,
        )
        return await agent.run(user_prompt=prompt)

    async def generate(
            self,
            res: TaskResult,
            is_short: bool = True,
    ) -> Generation | None:
        """Normalize or clean bytes and return text."""

        levels, templates, translation = await self.get_templates(res, is_short=True)

        prompts = [
            templates.get(level, translation.MIXED_PROMPT).format(
                title=res.title, content=res.content,
            ) for level in levels
        ]

        qs: list[AgentRunResult[QuestionSchema] | Exception] = await run_limited(
            *(
                self.make_request(prompt=prompt, output_type=QuestionSchema) for prompt in prompts
            ),
            limit=self.config.concurrency,
            return_exceptions=True,
        )
        exceptions = [q for q in qs if isinstance(q, Exception)]
        if exceptions:
            print(f"⚠️  Some requests failed: {'\n'.join(map(str, exceptions))}")

        # Filter out exceptions and empty results
        qs: list[str] = [qa.output.question for qa in qs if isinstance(qa.output, QuestionSchema)]
        if not qs:
            return None

        answers: list[AgentRunResult[AnswerSchema] | Exception] = await run_limited(
            *(
                self.make_request(prompt=translation.ANSWER_AND_CHUNKS_PROMPT.format(
                    content=res.content,
                    question=q
                ), output_type=AnswerSchema) for q in qs
            ),
            limit=self.config.concurrency,
            return_exceptions=True,
        )

        qas = dict(zip(qs, answers))

        # Filter out exceptions and empty results
        qas = [
            QA(q, a.output.answer, a.output.chunks)
            for q, a in qas.items()
            if
            not isinstance(a, Exception)
            and isinstance(a.output, AnswerSchema)
        ]

        return Generation(
            question_answers=qas,
            references=[res],
            language=res.language,
        )

    async def get_templates(self, res: TaskResult, is_short: bool = True):
        n = self.num_questions(res.content)
        print(f"Generating {n} questions for document: {res.title}")
        # Define difficulty distribution based on ratio
        difficulty_distributions = {
            FormatterDifficulties.EASY: [FormatterDifficulties.EASY] * n,
            FormatterDifficulties.MEDIUM: [FormatterDifficulties.MEDIUM] * n,
            FormatterDifficulties.HARD: [FormatterDifficulties.HARD] * n,
            FormatterDifficulties.MIXED: LLMGenerator.mixed_difficulty_distribution(n),
            FormatterDifficulties.BALANCED: LLMGenerator.balanced_difficulty_distribution(n),
        }
        difficulty_ratio: str = res.difficulty
        levels = difficulty_distributions.get(
            difficulty_ratio, difficulty_distributions.get(FormatterDifficulties.MIXED)
        )
        all_templates = {"en": en, "de": de}
        translation = all_templates.get(res.language, de)

        templates = {
            FormatterDifficulties.EASY: translation.EASY_PxROMPT if is_short else translation.LONG_EASY_PROMPT,
            FormatterDifficulties.MEDIUM: translation.MEDIUM_PROMPT if is_short else translation.LONG_MEDIUM_PROMPT,
            FormatterDifficulties.HARD: translation.HARD_PROMPT if is_short else translation.LONG_HARD_PROMPT,
            FormatterDifficulties.MIXED: translation.MIXED_PROMPT if is_short else translation.LONG_MIXED_PROMPT,
        }
        return levels, templates, translation

    async def generate_from_batch(self, *task_results: TaskResult) -> AsyncGenerator[Generation, None]:
        """Normalize or clean bytes and yield Generation objects grouped by language."""
        if not task_results:
            return

        from collections import defaultdict
        grouped: dict[str, list[TaskResult]] = defaultdict(list)
        for tr in task_results:
            grouped[tr.language].append(tr)

        all_templates = {"en": en, "de": de}

        for language, results in grouped.items():
            lines = (
                f'Document {r.title}: {r.content}'
                for r in results
            )
            combined_content = "\n".join(lines)
            translation = all_templates.get(language, de)

            prompts = [translation.CROSS_PAGE_PROMPT.format(combined_content=combined_content)]

            qs_raw = await run_limited(
                *(self.make_request(prompt=prompt, output_type=QuestionSchema) for prompt in prompts),
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
                            content=combined_content,
                            question=q
                        ),
                        output_type=AnswerSchema
                    )
                    for q in qs
                ),
                limit=self.config.concurrency,
                return_exceptions=True,
            )
            qas = [
                QA(q, a.output.answer, a.output.chunks)
                for q, a in zip(qs, answers_raw)
                if isinstance(a, AgentRunResult) and isinstance(a.output, AnswerSchema)
            ]

            yield Generation(
                question_answers=qas,
                references=results,
                language=language,
            )


if __name__ == '__main__':
    import asyncio
    from slurp.domain.config import TokenConfig, GeneratorConfig
    from slurp.domain.models import TaskResult

    # Example configuration
    token_config = TokenConfig.from_env()
    formatter_config = GeneratorConfig(
        model="google/gemini-2.5-flash-preview-05-20",
        language="en",
        difficulty_ratio=FormatterDifficulties.EASY,
        concurrency=5
    )

    # Create an instance of LLMFormatter
    formatter = LLMGenerator(token_config=token_config, config=formatter_config)

    # Example TaskResult
    sample_result = TaskResult(
        title="Onboarding Overview & Schedule",
        status_code=200,
        headers={"Content-Type": "text/plain"},
        content="""For the overview go to: /wiki/spaces/PNC/pages/456130563

IT-Setup Checklist:

Information: Full Name, Package Type, Adresse / Location, Keyboard Layout, Department, Leadership, Mailing Lists, Department + Extra Tools

• Hardware Package
• MS-Account / Settings
• Zugriffsrechte im MS-Office
• Outlook Email Zugriffsrechte / Settings
• Second: Accounts / Anbindung an SSO/Abteilungs Tools
• VPN-Zugriff (WLAN/Rechenzentrum)
• 2FA / Password Manager Anleitung + Setup

Security-Setup Checklist:

• Identität überprüfen
• Einführung ISMS

• Wiki durchschauen
• Sicherheitsschulung
• Acknowledgement

Administrativ-Setup Checklist:

• Register the new employee with our tax office (Payroll)
• Register the new employee with Collins (Access Card)

Company-Setup Checklist:

• Aleph Alpha SWAG
• Welcome Mail (Team/Hire)
• Meetings with manager

• Welcome / Onboarding
• Role & Responsibility
• (Read section in WORK RULES again)

• Meetings with colleagues

• Buddy Chat
• Coffee Chats

• Internal Luminous Account / Wiki Account Demos
• Email Settings / Signature
• Personal Information (Personio/Tax Office)

Content-Onboarding:

•
People & Operations Welcome-Session → Liza

•
Intro Onboarding

•
Inital ToDo’s (Personio etc.)

•
Intro into the P&O Wiki

•
How to work with your manager (goals, feedback etc.)

•
Benefits & Guidlines

•
Meetings (Learning Thursday, All Hands)

•
Intro Alpha Layer → Holger/Lutz

•
IT-Session (Intro to VDI, SSO or Security)

•
Support System (Ticketing)

•
Intro Tools (Atlassian, Personio, Figma, MS-Suit)

•
Luminous & Research Intro (Research & Engineering) → Samuel (appoints)

•
Usage of Luminous

•
Research Direction

•
Q&A

•
Customer Intro (Customer) → Hanis (appoints)

•
What are our current Customers & Success Stories

•
Go-to-Market Approach (Communication)

•
CEO-Welcome (Mission & Goals) → Jonas

•
Mission & Values

•
History & Success

•
Goals & Focus & Problems

•
Q&A

•
Offline-Tutorials:

•
Branding → (Font, Slide-Sets, Logo’s) → Tim

•
Intro into LLM’s (What are they, Intelligence, Advances & Drawbacks) → Reseacher / Engineer / Customer

Luminous & Research Intro

Time: 45min

• Generic slides and live session vs. Updated slides and self paced

Goal:

•
Get to know the team and faces → stregthens the team, collaboration and areas of responsiblity

•
Get to know and use the product → identify with core value of the business, context

•
Understand the progress of the models → get a feel for the direction of the company

Agenda:

•
Welcome & Intro: 5min

•
Luminouse Intro: 10min

•
Q&A: 5min

•
Research Intro: 10min

•
Q&A: 15min

Topics in the Presentation:

•
Luminous Showcase, Features & Usage

•
Engineering & Research Team Introduction

•
Research: History and Milestones

•
Research: Current Focus & Projects

Customer Intro

Time: 30min

• Generic slides and live session vs. Updated slides and self paced

Goal:

•
Get to know the team and faces → stregthens the team, collaboration and areas of responsiblity

•
Get to know the customer base → identify with the people the business provides value to, context

•
Understand the market → get a feel for the direction of the company

Agenda:

•
Welcome & Intro: 2min

•
Customer Intro: 15min

•
Q&A: 13min

Topics in the Presentation:

•
Who is part of the customer team? (Slide with all the team members)

•
Responsibilities of the customer team?

•
What is our market position?

•
Who are our customers? (Slide with some recent customer logos)

•
Why are they our customers?

•
What value are we providing our customers?

•
Who are our partners? What do they do? What is our partner strategy? → Oli ()

•
What great successes did we achieve? (Slide with one example project)

•
How and when to collaborate with the customer team?

• Joshua → Set up presentation
• Joshua → Get intput Oli for partner topic
• Sascha → Dump content on the customer page (11.08 eod)
• Joshua → get sign off from Hansi

CEO Intro

Time: 45min
Presenter: Jonas

Goal:

•
Get to know Jonas → feeling seen, valued and …, lower the bar for interaction

•
Get to know AA history → identify and become part of the AA story, context

•
Understand Mission & Objectives → spark ambition, get inspired, give direction

•
Understand strategic decisions → making sense of the bigger picture

•
Create a feedback loop → possibility to hear new (outside) perspectives

Agenda:

•
Welcome & Intro & Questions to answer: 10min

•
Customer Intro: 20min

•
Q&A & Interactive Session : 15min

Topics in the Presentation:

•
How did AA became the company it is today?

•
Which strategic turns did AA take and why?

•
Where are we going? What are the core ambitions?

•
What are the current challenges we as a company are facing?

•
What are we currently trying to achieve?""",
        hash="sample-hash",
        url="/spaces/PNC/pages/414220289/Onboarding+Overview+Schedule"
    )

    # Run the formatter and print results
    formatted_result = asyncio.run(formatter.generate(sample_result))
    print(formatted_result)


    async def main():

        async for gen in formatter.generate_from_batch(sample_result, sample_result):
            print(gen)


    formatted_result = asyncio.run(main())
    print(formatted_result)

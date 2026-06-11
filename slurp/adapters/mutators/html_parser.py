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

    @staticmethod
    def parse(html: str) -> str:
        if not html:
            return ""
        doc = SelectolaxHTMLParser(html)
        # remove scripts/styles
        for node in doc.css("script, style"):
            node.decompose()

        # handle ordered lists
        for ol in doc.css("ol"):
            items = [li.text(deep=True).strip() for li in ol.css("li")]
            numbered = " ".join(f"{i + 1}. {item}" for i, item in enumerate(items))
            ol.replace_with(numbered)

        # handle unordered lists
        for ul in doc.css("ul"):
            items = [li.text(deep=True).strip() for li in ul.css("li")]
            bulleted = " ".join(f"• {item}" for item in items)
            ul.replace_with(bulleted)

        # get all text, collapse whitespace
        root = doc.body or doc
        raw = root.text(deep=True)
        return " ".join(raw.split())

import asyncio
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from selectolax.parser import HTMLParser as SelectolaxHTMLParser
from slurp.domain.models import TaskResult
from slurp.domain.ports import TaskResultMutatorProtocol


@dataclass
class HTMLParser(TaskResultMutatorProtocol):
    executor = ProcessPoolExecutor()

    async def __call__(self, result: TaskResult) -> TaskResult:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(
            self.executor,
            self.parse,
            result.content
        )
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


if __name__ == "__main__":

    async def main():
        parser = HTMLParser()

        cases = [
            ("<body><p>Hello <b>world</b></p></body>", "Hello world"),
            ("<ul><li>Item 1</li><li>Item 2</li></ul>", "• Item 1 • Item 2"),
            ("<ol><li>First</li><li>Second</li></ol>", "1. First 2. Second"),
            ("<p>Text with <a href='#'>link</a></p>", "Text with link"),
            ("<div><span>Text in span</span></div>", "Text in span"),
            ("<p>Multiple   spaces    here</p>", "Multiple spaces here"),
            ("", ""),
            (None, ""),
            ("<script>bad()</script><p>Good</p>", "Good"),
        ]

        for html, expected in cases:
            result = TaskResult(
                title="Test",
                status_code=200,
                headers={},
                content=html or "",
                hash="",
                url="http://example.com",
            )
            out = await parser(result)
            content = out.content
            assert expected in content, f"Expected '{expected}' in '{content}'"
            print(f"PASS: {html!r} -> {content!r}")


    asyncio.run(main())

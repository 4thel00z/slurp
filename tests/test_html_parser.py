"""Test HTML parsing functionality."""

import pytest

from slurp.adapters.mutators.html_parser import HTMLParser
from slurp.domain.models import TaskResult


@pytest.fixture
def html_parser():
    """Create HTMLParser instance."""
    return HTMLParser()


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <html>
        <body>
            <h1>Test Document</h1>
            <p>This is a test paragraph with <strong>bold text</strong>.</p>
            <ul>
                <li>First item</li>
                <li>Second item</li>
                <li>Third item</li>
            </ul>
            <ol>
                <li>Step one</li>
                <li>Step two</li>
                <li>Step three</li>
            </ol>
            <script>console.log('remove me');</script>
            <style>.test { color: red; }</style>
        </body>
    </html>
    """


def test_parse_removes_scripts_and_styles(html_parser, sample_html):
    """Test that scripts and styles are removed from HTML."""
    result = html_parser.parse(sample_html)
    assert "console.log" not in result
    assert "color: red" not in result


def test_parse_converts_unordered_lists(html_parser):
    """Test that unordered lists are converted to bullet points."""
    html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
    result = html_parser.parse(html)
    assert "•" in result
    assert "Item 1" in result
    assert "Item 2" in result


def test_parse_converts_ordered_lists(html_parser):
    """Test that ordered lists are converted to numbered items."""
    html = "<ol><li>First</li><li>Second</li></ol>"
    result = html_parser.parse(html)
    assert "1. First" in result
    assert "2. Second" in result


def test_parse_empty_html(html_parser):
    """Test parsing empty HTML returns empty string."""
    assert html_parser.parse("") == ""
    assert html_parser.parse(None) == ""


def test_parse_extracts_text_content(html_parser, sample_html):
    """Test that text content is properly extracted."""
    result = html_parser.parse(sample_html)
    assert "Test Document" in result
    assert "bold text" in result


@pytest.mark.asyncio
async def test_html_parser_mutator(html_parser):
    """Test HTMLParser as a TaskResult mutator."""
    task_result = TaskResult(
        title="Test Page",
        status_code=200,
        headers={"content-type": "text/html"},
        content="<html><body><h1>Title</h1><p>Content</p></body></html>",
        hash="test-hash",
        url="https://example.com",
        language="en",
    )

    mutated = await html_parser(task_result)

    assert mutated.title == task_result.title
    assert mutated.url == task_result.url
    assert "Title" in mutated.content
    assert "Content" in mutated.content
    assert "<html>" not in mutated.content
    assert mutated.hash == task_result.hash

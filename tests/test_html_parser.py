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


def test_parse_nested_lists(html_parser):
    """Test that nested lists are handled correctly."""
    html = "<ul><li>Parent<ul><li>Child 1</li><li>Child 2</li></ul></li></ul>"
    result = html_parser.parse(html)
    assert "Parent" in result
    assert "Child 1" in result
    assert "Child 2" in result


def test_parse_empty_lists(html_parser):
    """Test that empty lists don't break parsing."""
    html = "<p>Before</p><ul></ul><ol></ol><p>After</p>"
    result = html_parser.parse(html)
    assert "Before" in result
    assert "After" in result


def test_parse_whitespace_collapsing(html_parser):
    """Test that multiple whitespaces are collapsed to single space."""
    html = "<p>Multiple   spaces    and\n\nnewlines\there</p>"
    result = html_parser.parse(html)
    assert "Multiple spaces and newlines here" in result
    assert "  " not in result


def test_parse_html_without_body(html_parser):
    """Test parsing HTML fragment without body tag."""
    html = "<div><p>No body tag here</p></div>"
    result = html_parser.parse(html)
    assert "No body tag here" in result


def test_parse_links_extract_text(html_parser):
    """Test that link text is extracted without href."""
    html = "<p>Click <a href='https://example.com'>this link</a> for more</p>"
    result = html_parser.parse(html)
    assert "Click this link for more" in result
    assert "href" not in result
    assert "https" not in result


def test_parse_mixed_content(html_parser):
    """Test complex HTML with scripts, lists, and text mixed together."""
    html = """
    <html>
        <body>
            <script>alert('xss')</script>
            <h1>Title</h1>
            <p>Intro paragraph</p>
            <style>.hidden { display: none; }</style>
            <ul><li>Item A</li><li>Item B</li></ul>
            <p>Middle text</p>
            <ol><li>Step 1</li><li>Step 2</li></ol>
            <script>console.log('removed')</script>
            <p>Final paragraph</p>
        </body>
    </html>
    """
    result = html_parser.parse(html)
    assert "alert" not in result
    assert "console.log" not in result
    assert "display: none" not in result
    assert "Title" in result
    assert "Intro paragraph" in result
    assert "• Item A" in result
    assert "1. Step 1" in result
    assert "Final paragraph" in result


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


def test_no_executor_until_called():
    parser = HTMLParser()
    assert parser._executor is None


@pytest.mark.asyncio
async def test_shutdown_releases_executor():
    parser = HTMLParser()
    task_result = TaskResult(
        title="t", status_code=200, headers={}, content="<p>hi</p>", hash="h", url="u"
    )
    await parser(task_result)
    assert parser._executor is not None
    parser.shutdown()
    assert parser._executor is None


@pytest.mark.asyncio
async def test_async_context_manager_shuts_down():
    async with HTMLParser() as parser:
        await parser(
            TaskResult(
                title="t", status_code=200, headers={}, content="<p>hi</p>", hash="h", url="u"
            )
        )
        assert parser._executor is not None
    assert parser._executor is None

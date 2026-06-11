"""Tests for the bundled slurp skill and its install helper."""

from pathlib import Path

from slurp.usecases.skill import install_skill
from slurp.usecases.skill import skill_text


def test_skill_text_describes_slurp():
    text = skill_text()

    assert len(text) > 200
    lower = text.lower()
    assert "slurp" in lower
    assert "connector" in lower
    assert text.lstrip().startswith("---")  # skill frontmatter


def test_install_writes_skill_under_claude_dir(tmp_path):
    dest = install_skill(base_dir=str(tmp_path))

    expected = Path(tmp_path) / ".claude" / "skills" / "slurp" / "SKILL.md"
    assert Path(dest) == expected
    assert expected.read_text(encoding="utf-8") == skill_text()

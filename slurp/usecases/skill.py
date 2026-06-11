"""The bundled slurp skill (a Claude Code SKILL.md) and its install helper."""

import logging
import sys
from importlib.resources import files
from pathlib import Path


logger = logging.getLogger(__name__)


def skill_text() -> str:
    """Return the bundled SKILL.md content."""
    return files("slurp.skill").joinpath("SKILL.md").read_text(encoding="utf-8")


def install_skill(base_dir: str = ".") -> str:
    """Write the bundled skill to ``<base_dir>/.claude/skills/slurp/SKILL.md``.

    Returns the path written.
    """
    dest = Path(base_dir) / ".claude" / "skills" / "slurp" / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(skill_text(), encoding="utf-8")
    return str(dest)


def run(install: bool, base_dir: str = ".") -> None:
    if install:
        path = install_skill(base_dir)
        logger.info("Installed slurp skill to %s", path)
    else:
        sys.stdout.write(skill_text() + "\n")

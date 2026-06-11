"""The bundled slurp skill (a Claude Code SKILL.md) and its install helper."""

from importlib.resources import files
from pathlib import Path


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
        print(f"Installed slurp skill to {path}")
    else:
        print(skill_text())

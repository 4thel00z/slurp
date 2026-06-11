"""Tests for the live QA render server's data + page building."""

import json
import sqlite3

from slurp.usecases.render import build_page
from slurp.usecases.render import load_generations


def seed_db(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE generations (id VARCHAR PRIMARY KEY, question_answers JSON NOT NULL, "
        '"references" JSON NOT NULL, language VARCHAR NOT NULL)'
    )
    con.execute(
        'INSERT INTO generations (id, question_answers, "references", language) VALUES (?,?,?,?)',
        (
            "g1",
            json.dumps({"Was ist X?": "X ist ein Test."}),
            json.dumps([{"title": "doc.md", "url": "/tmp/doc.md", "content": "hello body"}]),
            "de",
        ),
    )
    con.commit()
    con.close()


def test_load_generations_parses_qa_and_reference(tmp_path):
    db = tmp_path / "g.db"
    seed_db(str(db))

    gens = load_generations(str(db))

    assert len(gens) == 1
    g = gens[0]
    assert g["language"] == "de"
    assert g["qa"] == {"Was ist X?": "X ist ein Test."}
    assert g["title"] == "doc.md"
    assert g["url"] == "/tmp/doc.md"
    assert "hello body" in g["source"]


def test_load_generations_missing_table_returns_empty(tmp_path):
    """Before the worker has written anything, the page should still serve."""
    db = tmp_path / "empty.db"
    sqlite3.connect(str(db)).close()

    assert load_generations(str(db)) == []


def test_build_page_is_live_html():
    """The page shell polls the JSON endpoint so it updates as QA pairs arrive."""
    page = build_page()

    assert "<!DOCTYPE html>" in page
    assert "tailwindcss" in page
    assert "/api/generations" in page

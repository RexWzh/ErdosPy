from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


def create_sample_db(db_path: Path) -> Path:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE problems (
                id INTEGER PRIMARY KEY,
                number TEXT UNIQUE NOT NULL,
                statement TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                prize TEXT DEFAULT 'no',
                formalized INTEGER DEFAULT 0,
                oeis TEXT DEFAULT '[]',
                lean_url TEXT DEFAULT '',
                additional_text TEXT DEFAULT '',
                comments_count INTEGER DEFAULT 0
            );
            CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
            CREATE TABLE problem_tags (problem_id INTEGER NOT NULL, tag_id INTEGER NOT NULL);
            CREATE TABLE contributors (id INTEGER PRIMARY KEY, problem_id INTEGER NOT NULL, name TEXT NOT NULL);
            CREATE TABLE problem_references (id INTEGER PRIMARY KEY, problem_id INTEGER NOT NULL, reference_key TEXT NOT NULL);
            CREATE TABLE related_problems (id INTEGER PRIMARY KEY, problem_id INTEGER NOT NULL, related_number TEXT NOT NULL);
            CREATE TABLE problem_reactions (id INTEGER PRIMARY KEY, problem_id INTEGER NOT NULL, reaction_type TEXT NOT NULL, username TEXT NOT NULL);
            CREATE TABLE comments (id INTEGER PRIMARY KEY, problem_id INTEGER NOT NULL, author TEXT, author_username TEXT, date TEXT, content TEXT, likes INTEGER DEFAULT 0);
            CREATE VIRTUAL TABLE problems_fts USING fts5(statement, content='problems', content_rowid='id');
            """
        )

        conn.execute(
            """
            INSERT INTO problems (id, number, statement, status, prize, formalized, oeis, lean_url, additional_text, comments_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "1",
                "A Sidon set problem statement.",
                "open",
                "yes",
                1,
                json.dumps(["A000001"]),
                "https://lean.example/1",
                "Extra context",
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO problems (id, number, statement, status, prize, formalized, oeis, lean_url, additional_text, comments_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                "42",
                "Another Sidon flavored problem.",
                "open",
                "no",
                0,
                json.dumps([]),
                "",
                "",
                0,
            ),
        )
        conn.execute("INSERT INTO tags (id, name) VALUES (1, 'primes')")
        conn.execute("INSERT INTO problem_tags (problem_id, tag_id) VALUES (1, 1)")
        conn.execute(
            "INSERT INTO contributors (problem_id, name) VALUES (1, 'Terence Tao')"
        )
        conn.execute(
            "INSERT INTO problem_references (problem_id, reference_key) VALUES (1, 'ref-1')"
        )
        conn.execute(
            "INSERT INTO related_problems (problem_id, related_number) VALUES (1, '42')"
        )
        conn.execute(
            "INSERT INTO problem_reactions (problem_id, reaction_type, username) VALUES (1, 'working_on', 'alice')"
        )
        conn.execute(
            "INSERT INTO comments (problem_id, author, author_username, date, content, likes) VALUES (1, 'Alice', 'alice', '2026-04-07', 'Interesting progress', 3)"
        )
        conn.execute(
            "INSERT INTO problems_fts(rowid, statement) VALUES (1, 'A Sidon set problem statement.')"
        )
        conn.execute(
            "INSERT INTO problems_fts(rowid, statement) VALUES (2, 'Another Sidon flavored problem.')"
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    return create_sample_db(tmp_path / "sample.db")


@pytest.fixture
def sample_db_env(sample_db: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ERDOSPY_DB_PATH", str(sample_db))
    return sample_db

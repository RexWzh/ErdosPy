"""SQLite query layer for erdospy."""

from __future__ import annotations

import json
import sqlite3
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from .models import (
    ChangelogEntry,
    Comment,
    ForumThread,
    ForumThreadDetail,
    Problem,
)


def default_db_path() -> Path:
    """Resolve the bundled database path for installed and editable modes."""

    try:
        data_path = files("erdospy") / "data" / "erdos_problems.db"
        with as_file(data_path) as resolved:
            resolved_path = Path(resolved)
            if resolved_path.exists():
                return resolved_path
    except (FileNotFoundError, ModuleNotFoundError):
        pass

    project_root = Path(__file__).resolve().parents[2]
    fallback = project_root / "data" / "erdos_problems.db"
    if fallback.exists():
        return fallback
    raise FileNotFoundError("Could not locate erdospy database snapshot")


class ErdosDB:
    """Query interface for the bundled Erdős problems database."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or default_db_path()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ErdosDB":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _list_column(self, query: str, problem_id: int) -> list[str]:
        cursor = self.conn.execute(query, (problem_id,))
        return [str(row[0]) for row in cursor]

    def _table_columns(self, table_name: str) -> set[str]:
        cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
        return {str(row[1]) for row in cursor.fetchall()}

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        return column_name in self._table_columns(table_name)

    def _ensure_column(
        self, table_name: str, column_name: str, definition: str
    ) -> None:
        if not self._column_exists(table_name, column_name):
            self.conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
            )

    def _get_tags(self, problem_id: int) -> list[str]:
        return self._list_column(
            """
            SELECT t.name FROM tags t
            JOIN problem_tags pt ON t.id = pt.tag_id
            WHERE pt.problem_id = ?
            ORDER BY t.name
            """,
            problem_id,
        )

    def _get_references(self, problem_id: int) -> list[str]:
        return self._list_column(
            "SELECT reference_key FROM problem_references WHERE problem_id = ?",
            problem_id,
        )

    def _get_related(self, problem_id: int) -> list[str]:
        return self._list_column(
            "SELECT related_number FROM related_problems WHERE problem_id = ?",
            problem_id,
        )

    def _get_contributors(self, problem_id: int) -> list[str]:
        return self._list_column(
            "SELECT name FROM contributors WHERE problem_id = ? ORDER BY name",
            problem_id,
        )

    def _get_reactions(self, problem_id: int) -> dict[str, list[str]]:
        cursor = self.conn.execute(
            "SELECT reaction_type, username FROM problem_reactions WHERE problem_id = ?",
            (problem_id,),
        )
        reactions: dict[str, list[str]] = {}
        for row in cursor:
            reaction_type = str(row["reaction_type"])
            reactions.setdefault(reaction_type, []).append(str(row["username"]))
        return dict(sorted(reactions.items()))

    def _row_to_problem(self, row: sqlite3.Row) -> Problem:
        problem_id = int(row["id"])
        oeis = json.loads(row["oeis"]) if row["oeis"] else []
        if oeis == ["N/A"]:
            oeis = []

        return Problem(
            number=str(row["number"]),
            statement=row["statement"] or "",
            status=str(row["status"]),
            prize=str(row["prize"]),
            formalized=bool(row["formalized"]),
            oeis=oeis,
            tags=self._get_tags(problem_id),
            references=self._get_references(problem_id),
            related_problems=self._get_related(problem_id),
            reactions=self._get_reactions(problem_id),
            contributors=self._get_contributors(problem_id),
            lean_url=row["lean_url"] or "",
            additional_text=row["additional_text"] or "",
            comments_count=int(row["comments_count"] or 0),
        )

    def get_problem(self, number: str | int) -> Problem | None:
        cursor = self.conn.execute(
            "SELECT * FROM problems WHERE number = ?", (str(number),)
        )
        row = cursor.fetchone()
        return self._row_to_problem(row) if row else None

    def ensure_tracking_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS forum_threads (
                problem_id INTEGER,
                thread_key TEXT,
                thread_url TEXT,
                category TEXT,
                title TEXT,
                post_count INTEGER,
                last_activity TEXT,
                last_activity_ts TEXT,
                last_author TEXT,
                fetched_at TEXT,
                PRIMARY KEY (problem_id),
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            );

            CREATE TABLE IF NOT EXISTS forum_history (
                id INTEGER PRIMARY KEY,
                problem_id INTEGER,
                post_count INTEGER,
                last_author TEXT,
                recorded_at TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            );

            CREATE TABLE IF NOT EXISTS status_changes (
                id INTEGER PRIMARY KEY,
                problem_id INTEGER,
                old_status TEXT,
                new_status TEXT,
                detected_at TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            );

            CREATE TABLE IF NOT EXISTS changelog (
                id INTEGER PRIMARY KEY,
                change_type TEXT,
                problem_number TEXT,
                description TEXT,
                detected_at TEXT
            );

            CREATE TABLE IF NOT EXISTS forum_thread_details (
                thread_key TEXT PRIMARY KEY,
                problem_id INTEGER,
                problem_number TEXT,
                category TEXT,
                title TEXT,
                thread_url TEXT,
                status_text TEXT,
                statement TEXT,
                tags_json TEXT,
                additional_text TEXT,
                citation_text TEXT,
                comment_count INTEGER,
                formalized_url TEXT,
                problem_reactions_json TEXT,
                fetched_at TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            );

            CREATE TABLE IF NOT EXISTS forum_posts (
                post_id TEXT PRIMARY KEY,
                thread_key TEXT,
                problem_id INTEGER,
                problem_number TEXT,
                depth INTEGER,
                author_name TEXT,
                author_username TEXT,
                created_at TEXT,
                anchor TEXT,
                content_markdown TEXT,
                content_html TEXT,
                reactions_json TEXT,
                fetched_at TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            );
            """
        )

        self._ensure_column("forum_threads", "thread_key", "TEXT")
        self._ensure_column("forum_threads", "thread_url", "TEXT")
        self._ensure_column("forum_threads", "category", "TEXT DEFAULT 'problem'")
        self._ensure_column("forum_threads", "title", "TEXT")

        self.conn.commit()

    def get_problem_id(self, number: str | int) -> int | None:
        cursor = self.conn.execute(
            "SELECT id FROM problems WHERE number = ?", (str(number),)
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None

    def get_forum_thread(self, problem_number: str | int) -> dict[str, Any] | None:
        problem_id = self.get_problem_id(problem_number)
        if problem_id is None:
            return None

        cursor = self.conn.execute(
            """
            SELECT thread_key, thread_url, category, title,
                   post_count, last_activity, last_activity_ts, last_author, fetched_at
            FROM forum_threads WHERE problem_id = ?
            """,
            (problem_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "thread_key": str(row["thread_key"] or ""),
            "thread_url": str(row["thread_url"] or ""),
            "category": str(row["category"] or "problem"),
            "title": str(row["title"] or ""),
            "post_count": int(row["post_count"] or 0),
            "last_activity": str(row["last_activity"] or ""),
            "last_activity_ts": str(row["last_activity_ts"] or ""),
            "last_author": str(row["last_author"] or ""),
            "fetched_at": str(row["fetched_at"] or ""),
        }

    def upsert_forum_thread(self, thread: ForumThread, *, fetched_at: str) -> None:
        problem_id = self.get_problem_id(thread.problem_number)
        if problem_id is None:
            return

        self.conn.execute(
            """
            INSERT INTO forum_threads (
                problem_id, thread_key, thread_url, category, title,
                post_count, last_activity, last_activity_ts, last_author, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(problem_id) DO UPDATE SET
                thread_key = excluded.thread_key,
                thread_url = excluded.thread_url,
                category = excluded.category,
                title = excluded.title,
                post_count = excluded.post_count,
                last_activity = excluded.last_activity,
                last_activity_ts = excluded.last_activity_ts,
                last_author = excluded.last_author,
                fetched_at = excluded.fetched_at
            """,
            (
                problem_id,
                thread.thread_key,
                thread.thread_url,
                thread.category,
                thread.title,
                thread.post_count,
                thread.last_activity,
                thread.last_activity_ts,
                thread.last_author,
                fetched_at,
            ),
        )
        self.conn.execute(
            """
            INSERT INTO forum_history (problem_id, post_count, last_author, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (problem_id, thread.post_count, thread.last_author, fetched_at),
        )
        self.conn.commit()

    def upsert_forum_thread_detail(
        self, detail: ForumThreadDetail, *, fetched_at: str
    ) -> None:
        problem_id = (
            self.get_problem_id(detail.problem_number)
            if detail.problem_number
            else None
        )
        self.conn.execute(
            """
            INSERT INTO forum_thread_details (
                thread_key, problem_id, problem_number, category, title, thread_url,
                status_text, statement, tags_json, additional_text, citation_text,
                comment_count, formalized_url, problem_reactions_json, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_key) DO UPDATE SET
                problem_id = excluded.problem_id,
                problem_number = excluded.problem_number,
                category = excluded.category,
                title = excluded.title,
                thread_url = excluded.thread_url,
                status_text = excluded.status_text,
                statement = excluded.statement,
                tags_json = excluded.tags_json,
                additional_text = excluded.additional_text,
                citation_text = excluded.citation_text,
                comment_count = excluded.comment_count,
                formalized_url = excluded.formalized_url,
                problem_reactions_json = excluded.problem_reactions_json,
                fetched_at = excluded.fetched_at
            """,
            (
                detail.thread_key,
                problem_id,
                detail.problem_number,
                detail.category,
                detail.title,
                detail.thread_url,
                detail.status_text,
                detail.statement,
                json.dumps(detail.tags, ensure_ascii=False),
                detail.additional_text,
                detail.citation_text,
                detail.comment_count,
                detail.formalized_url,
                json.dumps(detail.problem_reactions, ensure_ascii=False),
                fetched_at,
            ),
        )
        self.conn.execute(
            "DELETE FROM forum_posts WHERE thread_key = ?", (detail.thread_key,)
        )
        for post in detail.posts:
            self.conn.execute(
                """
                INSERT INTO forum_posts (
                    post_id, thread_key, problem_id, problem_number, depth,
                    author_name, author_username, created_at, anchor,
                    content_markdown, content_html, reactions_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.post_id,
                    post.thread_key,
                    problem_id,
                    post.problem_number,
                    post.depth,
                    post.author_name,
                    post.author_username,
                    post.created_at,
                    post.anchor,
                    post.content_markdown,
                    post.content_html,
                    json.dumps(
                        [reaction.model_dump() for reaction in post.reactions],
                        ensure_ascii=False,
                    ),
                    fetched_at,
                ),
            )
        self.conn.commit()

    def get_forum_statistics(self) -> dict[str, Any]:
        self.ensure_tracking_schema()
        stats: dict[str, Any] = {}
        stats["problem_threads"] = self.conn.execute(
            "SELECT COUNT(*) FROM forum_threads WHERE category = 'problem'"
        ).fetchone()[0]
        stats["thread_details"] = self.conn.execute(
            "SELECT COUNT(*) FROM forum_thread_details"
        ).fetchone()[0]
        stats["forum_posts"] = self.conn.execute(
            "SELECT COUNT(*) FROM forum_posts"
        ).fetchone()[0]
        stats["distinct_post_authors"] = self.conn.execute(
            "SELECT COUNT(DISTINCT author_username) FROM forum_posts WHERE author_username != ''"
        ).fetchone()[0]
        top_threads = self.conn.execute(
            """
            SELECT problem_number, title, comment_count
            FROM forum_thread_details
            WHERE category = 'problem'
              AND problem_number != ''
            ORDER BY comment_count DESC, thread_key ASC
            LIMIT 10
            """
        )
        stats["top_problem_threads"] = [
            {
                "problem_number": str(row[0] or ""),
                "title": str(row[1] or ""),
                "comment_count": int(row[2] or 0),
            }
            for row in top_threads
        ]
        return stats

    def get_forum_thread_detail(self, thread_key: str) -> dict[str, Any] | None:
        self.ensure_tracking_schema()
        cursor = self.conn.execute(
            """
            SELECT * FROM forum_thread_details WHERE thread_key = ?
            """,
            (thread_key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        posts_cursor = self.conn.execute(
            """
            SELECT post_id, depth, author_name, author_username, created_at, anchor,
                   content_markdown, content_html, reactions_json
            FROM forum_posts
            WHERE thread_key = ?
            ORDER BY created_at ASC, post_id ASC
            """,
            (thread_key,),
        )
        return {
            "thread_key": str(row["thread_key"] or ""),
            "problem_number": str(row["problem_number"] or ""),
            "category": str(row["category"] or ""),
            "title": str(row["title"] or ""),
            "thread_url": str(row["thread_url"] or ""),
            "status_text": str(row["status_text"] or ""),
            "statement": str(row["statement"] or ""),
            "tags": json.loads(row["tags_json"] or "[]"),
            "additional_text": str(row["additional_text"] or ""),
            "citation_text": str(row["citation_text"] or ""),
            "comment_count": int(row["comment_count"] or 0),
            "formalized_url": str(row["formalized_url"] or ""),
            "problem_reactions": json.loads(row["problem_reactions_json"] or "{}"),
            "posts": [
                {
                    "post_id": str(post["post_id"] or ""),
                    "depth": int(post["depth"] or 0),
                    "author_name": str(post["author_name"] or ""),
                    "author_username": str(post["author_username"] or ""),
                    "created_at": str(post["created_at"] or ""),
                    "anchor": str(post["anchor"] or ""),
                    "content_markdown": str(post["content_markdown"] or ""),
                    "content_html": str(post["content_html"] or ""),
                    "reactions": json.loads(post["reactions_json"] or "[]"),
                }
                for post in posts_cursor
            ],
        }

    def get_latest_forum_threads(
        self, *, limit: int = 20, category: str | None = None
    ) -> list[dict[str, Any]]:
        self.ensure_tracking_schema()
        forum_thread_columns = self._table_columns("forum_threads")
        has_problem_number = "problem_number" in forum_thread_columns
        problem_number_expr = (
            "problem_number" if has_problem_number else "'' AS problem_number"
        )
        if category is None:
            cursor = self.conn.execute(
                """
                SELECT thread_key, {problem_number_expr}, category, title, thread_url,
                       post_count, last_activity, last_activity_ts, last_author
                FROM forum_threads
                ORDER BY last_activity_ts DESC, thread_key ASC
                LIMIT ?
                """.format(problem_number_expr=problem_number_expr),
                (limit,),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT thread_key, {problem_number_expr}, category, title, thread_url,
                       post_count, last_activity, last_activity_ts, last_author
                FROM forum_threads
                WHERE category = ?
                ORDER BY last_activity_ts DESC, thread_key ASC
                LIMIT ?
                """.format(problem_number_expr=problem_number_expr),
                (category, limit),
            )
        return [
            {
                "thread_key": str(row[0] or ""),
                "problem_number": (
                    str(row[1] or "")
                    if str(row[1] or "")
                    else (str(row[0] or "") if str(row[2] or "") == "problem" else "")
                ),
                "category": str(row[2] or ""),
                "title": str(row[3] or ""),
                "thread_url": str(row[4] or ""),
                "post_count": int(row[5] or 0),
                "last_activity": str(row[6] or ""),
                "last_activity_ts": str(row[7] or ""),
                "last_author": str(row[8] or ""),
            }
            for row in cursor
        ]

    def get_related_problem_threads(
        self, problem_number: str, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        self.ensure_tracking_schema()
        cursor = self.conn.execute(
            """
            SELECT thread_key, problem_number, category, title, thread_url,
                   comment_count, fetched_at
            FROM forum_thread_details
            WHERE problem_number = ?
            ORDER BY comment_count DESC, fetched_at DESC
            LIMIT ?
            """,
            (str(problem_number), limit),
        )
        return [
            {
                "thread_key": str(row[0] or ""),
                "problem_number": str(row[1] or ""),
                "category": str(row[2] or ""),
                "title": str(row[3] or ""),
                "thread_url": str(row[4] or ""),
                "comment_count": int(row[5] or 0),
                "fetched_at": str(row[6] or ""),
            }
            for row in cursor
        ]

    def search_forum_posts(
        self, query: str, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        self.ensure_tracking_schema()
        like_query = f"%{query}%"
        cursor = self.conn.execute(
            """
            SELECT fp.thread_key, fp.problem_number, fp.post_id, fp.depth,
                   fp.author_name, fp.author_username, fp.created_at,
                   fp.content_markdown, ftd.title, ftd.thread_url
            FROM forum_posts fp
            LEFT JOIN forum_thread_details ftd ON fp.thread_key = ftd.thread_key
            WHERE fp.content_markdown LIKE ? OR ftd.title LIKE ?
            ORDER BY fp.created_at DESC, fp.post_id DESC
            LIMIT ?
            """,
            (like_query, like_query, limit),
        )
        return [
            {
                "thread_key": str(row[0] or ""),
                "problem_number": str(row[1] or ""),
                "post_id": str(row[2] or ""),
                "depth": int(row[3] or 0),
                "author_name": str(row[4] or ""),
                "author_username": str(row[5] or ""),
                "created_at": str(row[6] or ""),
                "content_markdown": str(row[7] or ""),
                "title": str(row[8] or ""),
                "thread_url": str(row[9] or ""),
            }
            for row in cursor
        ]

    def get_problem_progress_summary(
        self, problem_number: str
    ) -> dict[str, Any] | None:
        problem = self.get_problem(problem_number)
        if problem is None:
            return None

        comments = self.get_comments(problem_number)
        related_threads = self.get_related_problem_threads(problem_number, limit=20)
        changelog = self.get_recent_changelog(
            limit=20, problem_number=str(problem_number)
        )
        return {
            "problem": problem.model_dump(),
            "comments": [comment.model_dump() for comment in comments],
            "related_threads": related_threads,
            "recent_changes": [entry.model_dump() for entry in changelog],
        }

    def get_forum_digest(self, *, limit: int = 20) -> dict[str, Any]:
        latest_threads = self.get_latest_forum_threads(limit=limit, category="problem")
        recent_changes = [
            entry.model_dump() for entry in self.get_recent_changelog(limit=limit)
        ]
        active_problems = [
            row
            for row in latest_threads
            if row["problem_number"] or row["thread_key"].isdigit()
        ]
        return {
            "latest_threads": latest_threads,
            "recent_changes": recent_changes,
            "active_problem_count": len(active_problems),
        }

    def insert_changelog_entry(self, entry: ChangelogEntry) -> None:
        self.conn.execute(
            """
            INSERT INTO changelog (change_type, problem_number, description, detected_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                entry.change_type,
                entry.problem_number,
                entry.description,
                entry.detected_at,
            ),
        )
        self.conn.commit()

    def get_recent_changelog(
        self, *, limit: int = 50, problem_number: str | None = None
    ) -> list[ChangelogEntry]:
        if problem_number is None:
            cursor = self.conn.execute(
                """
                SELECT change_type, problem_number, description, detected_at
                FROM changelog
                ORDER BY detected_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT change_type, problem_number, description, detected_at
                FROM changelog
                WHERE problem_number = ?
                ORDER BY detected_at DESC, id DESC
                LIMIT ?
                """,
                (problem_number, limit),
            )
        return [
            ChangelogEntry(
                change_type=str(row["change_type"]),
                problem_number=str(row["problem_number"]),
                description=str(row["description"]),
                detected_at=str(row["detected_at"]),
            )
            for row in cursor
        ]

    def search(
        self,
        *,
        status: str | None = None,
        tag: str | None = None,
        has_prize: bool | None = None,
        formalized: bool | None = None,
        has_lean: bool | None = None,
        text_query: str | None = None,
        has_reactions: bool | None = None,
        reaction_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Problem]:
        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append("p.status = ?")
            params.append(status)

        if tag:
            conditions.append(
                """
                p.id IN (
                    SELECT pt.problem_id FROM problem_tags pt
                    JOIN tags t ON pt.tag_id = t.id
                    WHERE t.name = ?
                )
                """
            )
            params.append(tag)

        if has_prize is not None:
            conditions.append("p.prize != 'no'" if has_prize else "p.prize = 'no'")

        if formalized is not None:
            conditions.append("p.formalized = ?")
            params.append(1 if formalized else 0)

        if has_lean is not None:
            conditions.append(
                "p.lean_url != '' AND p.lean_url IS NOT NULL"
                if has_lean
                else "(p.lean_url = '' OR p.lean_url IS NULL)"
            )

        if text_query:
            conditions.append(
                """
                p.id IN (
                    SELECT rowid FROM problems_fts WHERE problems_fts MATCH ?
                )
                """
            )
            params.append(text_query)

        if has_reactions is not None:
            conditions.append(
                "p.id IN (SELECT DISTINCT problem_id FROM problem_reactions)"
                if has_reactions
                else "p.id NOT IN (SELECT DISTINCT problem_id FROM problem_reactions)"
            )

        if reaction_type:
            conditions.append(
                """
                p.id IN (
                    SELECT problem_id FROM problem_reactions WHERE reaction_type = ?
                )
                """
            )
            params.append(reaction_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        cursor = self.conn.execute(
            f"""
            SELECT * FROM problems p
            WHERE {where_clause}
            ORDER BY CAST(p.number AS INTEGER)
            LIMIT ? OFFSET ?
            """,
            params,
        )
        return [self._row_to_problem(row) for row in cursor]

    def full_text_search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[Problem]:
        cursor = self.conn.execute(
            """
            SELECT p.* FROM problems p
            JOIN problems_fts fts ON p.id = fts.rowid
            WHERE problems_fts MATCH ?
            ORDER BY CAST(p.number AS INTEGER)
            LIMIT ? OFFSET ?
            """,
            (query, limit, offset),
        )
        return [self._row_to_problem(row) for row in cursor]

    def get_comments(self, problem_number: str | int) -> list[Comment]:
        cursor = self.conn.execute(
            """
            SELECT c.* FROM comments c
            JOIN problems p ON c.problem_id = p.id
            WHERE p.number = ?
            ORDER BY c.id
            """,
            (str(problem_number),),
        )
        return [
            Comment(
                author=str(row["author"]),
                author_username=str(row["author_username"]),
                date=str(row["date"]),
                content=str(row["content"]),
                likes=int(row["likes"] or 0),
            )
            for row in cursor
        ]

    def get_all_tags(self) -> list[tuple[str, int]]:
        cursor = self.conn.execute(
            """
            SELECT t.name, COUNT(*) as cnt
            FROM tags t
            JOIN problem_tags pt ON t.id = pt.tag_id
            GROUP BY t.id
            ORDER BY cnt DESC, t.name ASC
            """
        )
        return [(str(row[0]), int(row[1])) for row in cursor]

    def get_statistics(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        stats["total"] = self.conn.execute("SELECT COUNT(*) FROM problems").fetchone()[
            0
        ]
        stats["with_statements"] = self.conn.execute(
            "SELECT COUNT(*) FROM problems WHERE statement != ''"
        ).fetchone()[0]
        stats["by_status"] = {
            str(row[0]): int(row[1])
            for row in self.conn.execute(
                "SELECT status, COUNT(*) FROM problems GROUP BY status"
            )
        }
        stats["formalized"] = self.conn.execute(
            "SELECT COUNT(*) FROM problems WHERE formalized = 1"
        ).fetchone()[0]
        stats["with_lean"] = self.conn.execute(
            "SELECT COUNT(*) FROM problems WHERE lean_url != '' AND lean_url IS NOT NULL"
        ).fetchone()[0]
        stats["with_prizes"] = self.conn.execute(
            "SELECT COUNT(*) FROM problems WHERE prize != 'no'"
        ).fetchone()[0]
        stats["total_reactions"] = self.conn.execute(
            "SELECT COUNT(*) FROM problem_reactions"
        ).fetchone()[0]
        stats["unique_users"] = self.conn.execute(
            "SELECT COUNT(DISTINCT username) FROM problem_reactions"
        ).fetchone()[0]
        stats["total_contributors"] = self.conn.execute(
            "SELECT COUNT(*) FROM contributors"
        ).fetchone()[0]
        stats["total_comments"] = self.conn.execute(
            "SELECT COUNT(*) FROM comments"
        ).fetchone()[0]
        stats["reactions_by_type"] = {
            str(row[0]): int(row[1])
            for row in self.conn.execute(
                "SELECT reaction_type, COUNT(*) FROM problem_reactions GROUP BY reaction_type ORDER BY COUNT(*) DESC"
            )
        }
        return stats

"""SQLite query layer for erdospy."""

from __future__ import annotations

import json
import sqlite3
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from .models import Comment, Problem


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

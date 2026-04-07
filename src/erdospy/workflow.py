"""CLI-oriented workspace and update workflow helpers."""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .db import ErdosDB, default_db_path
from .scraper.incremental import IncrementalUpdater


def default_workspace_db_path() -> Path:
    return Path.cwd() / ".erdospy" / "erdos_problems.db"


def resolve_db_path(db_path: Path | None = None) -> Path:
    return (db_path or default_workspace_db_path()).expanduser().resolve()


def history_path_for_db(db_path: Path) -> Path:
    return db_path.parent / "history.jsonl"


def snapshot_path_for_db(db_path: Path) -> Path:
    return db_path.parent / "snapshot.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ChangeEvent(BaseModel):
    kind: str = "change"
    recorded_at: str
    problem_number: str
    change_type: str
    description: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)


class UpdateRun(BaseModel):
    kind: str = "run"
    recorded_at: str
    mode: str
    pull: bool = False
    quick: bool = False
    comments_only: bool = False
    total_changes: int = 0
    status_changes: int = 0
    comment_changes: int = 0


@dataclass
class UpdateResult:
    db_path: Path
    run: UpdateRun
    changes: list[ChangeEvent]


def initialize_workspace(db_path: Path | None = None, force: bool = False) -> Path:
    resolved = resolve_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    if resolved.exists() and not force:
        return resolved

    shutil.copy2(default_db_path(), resolved)
    with ErdosDB(resolved) as db:
        db.ensure_tracking_schema()

    snapshot = snapshot_problem_index(resolved)
    snapshot_path_for_db(resolved).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    run = UpdateRun(recorded_at=now_iso(), mode="build")
    append_history(resolved, [run])
    return resolved


def snapshot_problem_index(db_path: Path) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT number, status, comments_count FROM problems ORDER BY CAST(number AS INTEGER)"
        )
        return {
            str(number): {
                "status": str(status or ""),
                "comments_count": int(comments_count or 0),
            }
            for number, status, comments_count in cursor.fetchall()
        }
    finally:
        conn.close()


def guess_navigator_root() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[3].parent / "erdos-navigator",
        Path(__file__).resolve().parents[4] / "reference" / "erdos-navigator",
        Path(__file__).resolve().parents[4] / "core" / "erdos-navigator",
        Path.cwd().resolve().parent / "erdos-navigator",
        Path.cwd().resolve() / "erdos-navigator",
    ]
    for candidate in candidates:
        if (candidate / "scrapers" / "update_all.py").exists():
            return candidate
    return None


def format_daily_heading(date: str) -> str:
    return f"Daily Progress for {date}"


def format_record_heading(problem_number: str) -> str:
    return f"Recorded History for Problem #{problem_number}"


def _append_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_history(db_path: Path, records: list[BaseModel]) -> None:
    _append_jsonl(
        history_path_for_db(db_path), [record.model_dump() for record in records]
    )


def read_history(db_path: Path) -> list[dict[str, Any]]:
    path = history_path_for_db(db_path)
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def diff_snapshots(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    *,
    recorded_at: str,
) -> list[ChangeEvent]:
    changes: list[ChangeEvent] = []

    for number, current in after.items():
        previous = before.get(number)
        if not previous:
            changes.append(
                ChangeEvent(
                    recorded_at=recorded_at,
                    problem_number=number,
                    change_type="new_problem",
                    description=f"Problem #{number} appeared in the local snapshot.",
                    before={},
                    after=current,
                )
            )
            continue

        if previous.get("status") != current.get("status"):
            changes.append(
                ChangeEvent(
                    recorded_at=recorded_at,
                    problem_number=number,
                    change_type="status_change",
                    description=(
                        f"Problem #{number} changed status "
                        f"from {previous.get('status')} to {current.get('status')}."
                    ),
                    before=previous,
                    after=current,
                )
            )

        old_comments = int(previous.get("comments_count", 0))
        new_comments = int(current.get("comments_count", 0))
        if old_comments != new_comments:
            direction = "increased" if new_comments > old_comments else "decreased"
            changes.append(
                ChangeEvent(
                    recorded_at=recorded_at,
                    problem_number=number,
                    change_type="comment_delta",
                    description=(
                        f"Problem #{number} comments {direction} "
                        f"from {old_comments} to {new_comments}."
                    ),
                    before=previous,
                    after=current,
                )
            )

    return changes


def update_workspace(
    db_path: Path | None = None,
    *,
    navigator_root: Path | None = None,
    pull: bool = False,
    quick: bool = False,
    comments_only: bool = False,
) -> UpdateResult:
    resolved_db = resolve_db_path(db_path)
    if not resolved_db.exists():
        initialize_workspace(resolved_db)

    before = snapshot_problem_index(resolved_db)
    with IncrementalUpdater(resolved_db) as updater:
        incremental_result = updater.run()
    after = snapshot_problem_index(resolved_db)

    recorded_at = now_iso()
    changes = diff_snapshots(before, after, recorded_at=recorded_at)
    changes.extend(
        ChangeEvent(
            recorded_at=entry.detected_at,
            problem_number=entry.problem_number,
            change_type=entry.change_type,
            description=entry.description,
            before={},
            after={},
        )
        for entry in incremental_result.changelog_entries
    )
    run = UpdateRun(
        recorded_at=recorded_at,
        mode="update",
        pull=pull,
        quick=quick,
        comments_only=comments_only,
        total_changes=len(changes),
        status_changes=sum(change.change_type == "status_change" for change in changes),
        comment_changes=sum(
            change.change_type == "comment_delta" for change in changes
        ),
    )

    append_history(resolved_db, [run, *changes])
    snapshot_path_for_db(resolved_db).write_text(
        json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return UpdateResult(db_path=resolved_db, run=run, changes=changes)


def daily_history(
    db_path: Path | None = None, date: str | None = None
) -> list[dict[str, Any]]:
    resolved_db = resolve_db_path(db_path)
    entries = read_history(resolved_db)
    changelog: list[dict[str, Any]] = []
    try:
        with ErdosDB(resolved_db) as db:
            db.ensure_tracking_schema()
            changelog = [
                entry.model_dump()
                | {"kind": "change", "recorded_at": entry.detected_at}
                for entry in db.get_recent_changelog(limit=500)
            ]
    except sqlite3.DatabaseError:
        changelog = []

    existing_change_keys = {
        (
            entry.get("recorded_at"),
            entry.get("problem_number"),
            entry.get("change_type"),
            entry.get("description"),
        )
        for entry in entries
        if entry.get("kind") == "change"
    }
    for entry in changelog:
        key = (
            entry.get("recorded_at"),
            entry.get("problem_number"),
            entry.get("change_type"),
            entry.get("description"),
        )
        if key not in existing_change_keys:
            entries.append(entry)

    if not entries:
        return []

    effective_date = date
    if effective_date is None:
        effective_date = max(entry["recorded_at"][:10] for entry in entries)

    return [
        entry
        for entry in entries
        if entry.get("recorded_at", "").startswith(effective_date)
    ]


def problem_record(
    problem_number: str,
    db_path: Path | None = None,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    resolved_db = resolve_db_path(db_path)
    entries = read_history(resolved_db)
    changelog_entries: list[dict[str, Any]] = []
    try:
        with ErdosDB(resolved_db) as db:
            db.ensure_tracking_schema()
            changelog_entries = [
                entry.model_dump()
                | {"kind": "change", "recorded_at": entry.detected_at}
                for entry in db.get_recent_changelog(
                    limit=limit, problem_number=str(problem_number)
                )
            ]
    except sqlite3.DatabaseError:
        changelog_entries = []

    existing_change_keys = {
        (
            entry.get("recorded_at"),
            entry.get("problem_number"),
            entry.get("change_type"),
            entry.get("description"),
        )
        for entry in entries
        if entry.get("kind") == "change"
    }
    for entry in changelog_entries:
        key = (
            entry.get("recorded_at"),
            entry.get("problem_number"),
            entry.get("change_type"),
            entry.get("description"),
        )
        if key not in existing_change_keys:
            entries.append(entry)

    filtered = [
        entry
        for entry in entries
        if entry.get("kind") == "change"
        and entry.get("problem_number") == str(problem_number)
    ]
    filtered.sort(key=lambda entry: entry.get("recorded_at", ""), reverse=True)
    return filtered[:limit]

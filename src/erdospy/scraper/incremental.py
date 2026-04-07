"""Native incremental update pipeline for erdospy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from erdospy.db import ErdosDB
from erdospy.models import ChangelogEntry

from .forum import ForumThread, parse_forum_thread_detail, parse_forum_threads

BASE_URL = "https://www.erdosproblems.com"


@dataclass
class IncrementalUpdateResult:
    forum_threads_seen: int
    new_threads: int
    updated_threads: int
    thread_details_fetched: int
    forum_posts_fetched: int
    changelog_entries: list[ChangelogEntry]
    detected_at: str


class IncrementalUpdater:
    """Track forum activity and changelog entries without full re-scrapes."""

    def __init__(self, db_path: Path, client: httpx.Client | None = None):
        self.db_path = db_path
        self.client = client or httpx.Client(
            headers={"User-Agent": "erdospy/0.1 incremental updater"},
            follow_redirects=True,
            timeout=30.0,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "IncrementalUpdater":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_forum_threads(self) -> list[ForumThread]:
        response = self.client.get(f"{BASE_URL}/forum/")
        response.raise_for_status()
        return parse_forum_threads(response.text, now=datetime.now(UTC))

    def fetch_thread_detail(self, thread: ForumThread):
        response = self.client.get(thread.thread_url)
        response.raise_for_status()
        return parse_forum_thread_detail(response.text, thread.thread_url)

    def full_sync(self) -> IncrementalUpdateResult:
        return self.full_sync_limited(limit=None)

    def full_sync_limited(self, limit: int | None = None) -> IncrementalUpdateResult:
        detected_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        threads = self.fetch_forum_threads()
        if limit is not None:
            threads = threads[:limit]
        changelog_entries: list[ChangelogEntry] = []
        details_fetched = 0
        posts_fetched = 0

        with ErdosDB(self.db_path) as db:
            db.ensure_tracking_schema()
            for thread in threads:
                db.upsert_forum_thread(thread, fetched_at=detected_at)
                detail = self.fetch_thread_detail(thread)
                db.upsert_forum_thread_detail(detail, fetched_at=detected_at)
                details_fetched += 1
                posts_fetched += len(detail.posts)

            changelog_entries.append(
                ChangelogEntry(
                    change_type="forum_full_sync",
                    problem_number="",
                    description=(
                        f"Full forum sync captured {len(threads)} threads, "
                        f"{details_fetched} thread pages, and {posts_fetched} posts."
                    ),
                    detected_at=detected_at,
                )
            )
            db.insert_changelog_entry(changelog_entries[0])

        return IncrementalUpdateResult(
            forum_threads_seen=len(threads),
            new_threads=0,
            updated_threads=0,
            thread_details_fetched=details_fetched,
            forum_posts_fetched=posts_fetched,
            changelog_entries=changelog_entries,
            detected_at=detected_at,
        )

    def run(self) -> IncrementalUpdateResult:
        detected_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        threads = self.fetch_forum_threads()
        changelog_entries: list[ChangelogEntry] = []
        new_threads = 0
        updated_threads = 0

        with ErdosDB(self.db_path) as db:
            db.ensure_tracking_schema()
            for thread in threads:
                previous = db.get_forum_thread(thread.problem_number)
                db.upsert_forum_thread(thread, fetched_at=detected_at)

                if previous is None:
                    new_threads += 1
                    entry = ChangelogEntry(
                        change_type="new_thread",
                        problem_number=thread.problem_number,
                        description=(
                            f"Problem #{thread.problem_number} has a tracked forum thread "
                            f"with {thread.post_count} posts by {thread.last_author}."
                        ),
                        detected_at=detected_at,
                    )
                    changelog_entries.append(entry)
                    db.insert_changelog_entry(entry)
                    continue

                if (
                    previous["post_count"] != thread.post_count
                    or previous["last_author"] != thread.last_author
                    or previous["last_activity"] != thread.last_activity
                ):
                    updated_threads += 1
                    entry = ChangelogEntry(
                        change_type="forum_activity",
                        problem_number=thread.problem_number,
                        description=(
                            f"Problem #{thread.problem_number} forum activity moved from "
                            f"{previous['post_count']} to {thread.post_count} posts; "
                            f"latest author is {thread.last_author}."
                        ),
                        detected_at=detected_at,
                    )
                    changelog_entries.append(entry)
                    db.insert_changelog_entry(entry)

        return IncrementalUpdateResult(
            forum_threads_seen=len(threads),
            new_threads=new_threads,
            updated_threads=updated_threads,
            thread_details_fetched=0,
            forum_posts_fetched=0,
            changelog_entries=changelog_entries,
            detected_at=detected_at,
        )

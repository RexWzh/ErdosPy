from __future__ import annotations

import shutil
from pathlib import Path

from erdospy.db import ErdosDB, default_db_path
from erdospy.scraper.incremental import IncrementalUpdater


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, text: str):
        self.text = text

    def get(self, url: str) -> FakeResponse:
        return FakeResponse(self.text)

    def close(self) -> None:
        return None


def test_incremental_updater_writes_forum_tables(tmp_path: Path):
    db_path = tmp_path / "erdos.db"
    shutil.copy2(default_db_path(), db_path)

    html = """
    <html><body>
    <h2>Problem Threads</h2>
    <div>1</div>
    <div>(4 posts)</div>
    <div>an hour ago</div>
    <div>by</div>
    <div>TerenceTao</div>
    </body></html>
    """

    with IncrementalUpdater(db_path, client=FakeClient(html)) as updater:
        result = updater.run()

    assert result.forum_threads_seen == 1
    assert result.new_threads == 1

    with ErdosDB(db_path) as db:
        db.ensure_tracking_schema()
        thread = db.get_forum_thread("1")
        changelog = db.get_recent_changelog(limit=10, problem_number="1")

    assert thread is not None
    assert thread["post_count"] == 4
    assert changelog
    assert changelog[0].change_type == "new_thread"

from __future__ import annotations

import shutil
from pathlib import Path

from erdospy.db import ErdosDB
from erdospy.scraper.incremental import IncrementalUpdater


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, listing_text: str, thread_text: str | None = None):
        self.listing_text = listing_text
        self.thread_text = thread_text or listing_text

    def get(self, url: str) -> FakeResponse:
        if "/forum/thread/" in url:
            return FakeResponse(self.thread_text)
        return FakeResponse(self.listing_text)

    def close(self) -> None:
        return None


def test_incremental_updater_writes_forum_tables(tmp_path: Path, sample_db: Path):
    db_path = tmp_path / "erdos.db"
    shutil.copy2(sample_db, db_path)

    html = """
    <html><body>
      <div class="fancy-line"><span>Problem Threads</span></div>
      <ul>
        <li class="thread-item">
          <a class="thread-title" href="/forum/thread/1">1</a>
          <span class="badge">(4 posts)</span>
          <span class="muted">an hour ago by <a class="user-link" href="/forum/user/TerenceTao">TerenceTao</a></span>
        </li>
      </ul>
    </body></html>
    """

    thread_html = """
    <html>
      <head><title>Erdős Problem #1 - Discussion thread</title></head>
      <body>
        <div id="prize">OPEN</div>
        <div id="content">Statement</div>
        <div class="comment-count"><a href="/forum/discuss/1">4 comments on this problem</a></div>
        <li id="post-11" class="post depth-0 odd">
          <div class="post-body"><p>First post</p></div>
          <div class="post-meta">
            <strong><a href="/forum/user/TerenceTao">TerenceTao</a></strong>
            — <a href="/forum/thread/1#post-11">12:00 on 01 Apr 2026</a>
          </div>
        </li>
      </body>
    </html>
    """

    with IncrementalUpdater(db_path, client=FakeClient(html, thread_html)) as updater:
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


def test_incremental_updater_ignores_general_threads_for_problem_changelog(
    tmp_path: Path,
    sample_db: Path,
):
    db_path = tmp_path / "erdos.db"
    shutil.copy2(sample_db, db_path)

    html = """
    <html><body>
      <div class="fancy-line"><span>General Threads</span></div>
      <ul>
        <li class="thread-item">
          <a class="thread-title" href="/forum/thread/AI%20Contributions">AI Contributions</a>
          <span class="badge">(347 posts)</span>
          <span class="muted">an hour ago by <a class="user-link" href="/forum/user/qrdl">qrdl</a></span>
        </li>
      </ul>
    </body></html>
    """

    with IncrementalUpdater(db_path, client=FakeClient(html)) as updater:
        result = updater.run()

    assert result.forum_threads_seen == 1
    assert result.new_threads == 0
    assert result.updated_threads == 0
    assert result.changelog_entries == []

    with ErdosDB(db_path) as db:
        db.ensure_tracking_schema()
        changelog = db.get_recent_changelog(limit=10)

    assert changelog == []


def test_incremental_full_sync_writes_thread_details_and_posts(
    tmp_path: Path, sample_db: Path
):
    db_path = tmp_path / "erdos.db"
    shutil.copy2(sample_db, db_path)

    listing_html = """
    <html><body>
      <div class="fancy-line"><span>Problem Threads</span></div>
      <ul>
        <li class="thread-item">
          <a class="thread-title" href="/forum/thread/12">12</a>
          <span class="badge">(3 posts)</span>
          <span class="muted">an hour ago by <a class="user-link" href="/forum/user/TerenceTao">TerenceTao</a></span>
        </li>
      </ul>
    </body></html>
    """

    thread_html = """
    <html>
      <head><title>Erdős Problem #12 - Discussion thread</title></head>
      <body>
        <div id="prize">OPEN</div>
        <div id="content">Sample problem statement.</div>
        <div id="tags"><a href="/tags/number theory">number theory</a></div>
        <div class="problem-additional-text">Extra context.</div>
        <div class="citationbox"><div id="content">Citation.</div></div>
        <div class="comment-count"><a href="/forum/discuss/12">3 comments on this problem</a></div>
        <li id="post-101" class="post depth-0 odd">
          <div class="post-body"><p>First post</p></div>
          <div class="post-meta">
            <strong><a href="/forum/user/TerenceTao">TerenceTao</a></strong>
            — <a href="/forum/thread/12#post-101">12:00 on 01 Apr 2026</a>
          </div>
        </li>
      </body>
    </html>
    """

    with IncrementalUpdater(
        db_path, client=FakeClient(listing_html, thread_html)
    ) as updater:
        result = updater.full_sync()

    assert result.thread_details_fetched == 1
    assert result.forum_posts_fetched == 1

    with ErdosDB(db_path) as db:
        stats = db.get_forum_statistics()

    assert stats["problem_threads"] == 1
    assert stats["thread_details"] == 1
    assert stats["forum_posts"] == 1

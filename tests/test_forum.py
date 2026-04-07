from __future__ import annotations

from datetime import UTC, datetime

from erdospy.scraper.forum import parse_forum_threads, parse_relative_time


def test_parse_relative_time_handles_common_units():
    now = datetime(2026, 4, 7, 12, 0, tzinfo=UTC)

    assert parse_relative_time("an hour ago", now=now) == datetime(
        2026, 4, 7, 11, 0, tzinfo=UTC
    )
    assert parse_relative_time("2 days ago", now=now) == datetime(
        2026, 4, 5, 12, 0, tzinfo=UTC
    )
    assert parse_relative_time("a month ago", now=now) == datetime(
        2026, 3, 8, 12, 0, tzinfo=UTC
    )


def test_parse_forum_threads_reads_five_line_groups():
    html = """
    <html><body>
    <h2>Problem Threads</h2>
    <div>749</div>
    <div>(12 posts)</div>
    <div>an hour ago</div>
    <div>by</div>
    <div>TerenceTao</div>
    <div>488</div>
    <div>(2 posts)</div>
    <div>2 days ago</div>
    <div>by</div>
    <div>Alice</div>
    </body></html>
    """

    threads = parse_forum_threads(html, now=datetime(2026, 4, 7, 12, 0, tzinfo=UTC))

    assert len(threads) == 2
    assert threads[0].problem_number == "749"
    assert threads[0].post_count == 12
    assert threads[0].last_author == "TerenceTao"
    assert threads[1].problem_number == "488"

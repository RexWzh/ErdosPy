from __future__ import annotations

from datetime import UTC, datetime

from erdospy.scraper.forum import (
    parse_forum_thread_detail,
    parse_forum_threads,
    parse_relative_time,
)


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
    <div class="fancy-line"><span>Problem Threads</span></div>
    <ul>
      <li class="thread-item">
        <a class="thread-title" href="/forum/thread/749">749</a>
        <span class="badge">(12 posts)</span>
        <span class="muted">an hour ago by <a class="user-link" href="/forum/user/TerenceTao">TerenceTao</a></span>
      </li>
      <li class="thread-item">
        <a class="thread-title" href="/forum/thread/488">488</a>
        <span class="badge">(2 posts)</span>
        <span class="muted">2 days ago by <a class="user-link" href="/forum/user/Alice">Alice</a></span>
      </li>
    </ul>
    </body></html>
    """

    threads = parse_forum_threads(html, now=datetime(2026, 4, 7, 12, 0, tzinfo=UTC))

    assert len(threads) == 2
    assert threads[0].problem_number == "749"
    assert threads[0].post_count == 12
    assert threads[0].last_author == "TerenceTao"
    assert threads[0].thread_url.endswith("/forum/thread/749")
    assert threads[1].problem_number == "488"


def test_parse_forum_thread_detail_extracts_posts_and_problem_metadata():
    html = """
    <html>
      <head><title>Erdős Problem #749 - Discussion thread</title></head>
      <body>
        <div id="prize">OPEN</div>
        <div id="content">A sample statement.</div>
        <div id="tags"><a href="/tags/additive combinatorics">additive combinatorics</a></div>
        <div class="problem-additional-text">Additional problem context.</div>
        <div class="citationbox"><div id="content">Citation text.</div></div>
        <div class="comment-count"><a href="/forum/discuss/749">12 comments on this problem</a></div>
        <table>
          <tr class="problem-reaction-row" data-reaction-type="working_on">
            <td><span class="problem-reaction-users"><a href="/forum/user/Aron">Aron</a></span></td>
          </tr>
        </table>
        <li id="post-100" class="post depth-0 even">
          <div class="post-body"><p>Hello world</p></div>
          <div class="post-meta">
            <strong><a href="/forum/user/Aron">Aron Bhalla</a></strong>
            — <a href="/forum/thread/749#post-100">23:47 on 04 Apr 2026</a>
            <div class="reaction-bar">
              <button class="reaction-btn" data-type="like" title="I like this post.\n\nUsers: natso26">
                <span class="reaction-count">1</span>
              </button>
            </div>
          </div>
        </li>
      </body>
    </html>
    """

    detail = parse_forum_thread_detail(
        html, "https://www.erdosproblems.com/forum/thread/749"
    )

    assert detail.problem_number == "749"
    assert detail.comment_count == 12
    assert detail.tags == ["additive combinatorics"]
    assert detail.problem_reactions["working_on"] == ["Aron"]
    assert len(detail.posts) == 1
    assert detail.posts[0].post_id == "100"
    assert detail.posts[0].author_username == "Aron"
    assert detail.posts[0].reactions[0].reaction_type == "like"

"""Forum parsing utilities."""

from __future__ import annotations

import re
from urllib.parse import urljoin
from datetime import UTC, datetime, timedelta

from bs4 import BeautifulSoup

from erdospy.models import (
    ForumPost,
    ForumReactionSummary,
    ForumThread,
    ForumThreadDetail,
)

BASE_URL = "https://www.erdosproblems.com"


_RELATIVE_TIME_RE = re.compile(
    r"^(?P<count>a|an|\d+)\s+(?P<unit>minute|hour|day|week|month|year)s?\s+ago$",
    re.IGNORECASE,
)


def parse_relative_time(text: str, now: datetime | None = None) -> datetime:
    """Convert relative forum timestamps into UTC datetimes."""

    raw = " ".join(text.strip().split()).lower()
    if not raw:
        raise ValueError("Relative time text is empty")

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    if raw in {"just now", "moments ago"}:
        return current

    match = _RELATIVE_TIME_RE.match(raw)
    if not match:
        raise ValueError(f"Unsupported relative time: {text}")

    count_text = match.group("count")
    count = 1 if count_text in {"a", "an"} else int(count_text)
    unit = match.group("unit")

    if unit == "minute":
        delta = timedelta(minutes=count)
    elif unit == "hour":
        delta = timedelta(hours=count)
    elif unit == "day":
        delta = timedelta(days=count)
    elif unit == "week":
        delta = timedelta(weeks=count)
    elif unit == "month":
        delta = timedelta(days=30 * count)
    elif unit == "year":
        delta = timedelta(days=365 * count)
    else:
        raise ValueError(f"Unsupported relative time unit: {unit}")

    return current - delta


def _extract_forum_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    marker_index = -1
    for index, line in enumerate(lines):
        if line.lower() == "problem threads":
            marker_index = index
            break

    return lines[marker_index + 1 :] if marker_index >= 0 else lines


def parse_forum_threads(html: str, now: datetime | None = None) -> list[ForumThread]:
    """Parse forum thread summaries from the forum listing page."""

    soup = BeautifulSoup(html, "html.parser")
    threads: list[ForumThread] = []
    section_category = None

    for section in soup.select("div.fancy-line > span"):
        heading = section.get_text(" ", strip=True).lower()
        if heading == "problem threads":
            section_category = "problem"
        elif heading == "general threads":
            section_category = "general"
        elif heading == "blog posts":
            section_category = "blog"
        else:
            continue

        thread_list = section.parent.find_next_sibling("ul")
        if thread_list is None:
            continue

        for item in thread_list.select("li.thread-item"):
            link = item.select_one("a.thread-title")
            badge = item.select_one("span.badge")
            user_link = item.select_one("a.user-link")
            muted = item.select_one("span.muted")
            if link is None or badge is None or muted is None:
                continue

            href = link.get("href", "")
            thread_key = href.rsplit("/", 1)[-1]
            title = link.get_text(" ", strip=True)
            problem_number = (
                title if section_category == "problem" and title.isdigit() else ""
            )
            if section_category == "problem" and not problem_number:
                continue

            badge_text = badge.get_text(" ", strip=True)
            posts_match = re.search(r"(\d+)\s+posts?", badge_text, re.IGNORECASE)
            if not posts_match:
                continue

            muted_text = muted.get_text(" ", strip=True)
            last_author = user_link.get_text(" ", strip=True) if user_link else ""
            activity_text = (
                muted_text.split(" by ")[0].strip()
                if " by " in muted_text
                else muted_text
            )
            if not activity_text:
                activity_text = muted_text
            activity_ts = parse_relative_time(activity_text, now=now)

            threads.append(
                ForumThread(
                    problem_number=problem_number,
                    post_count=int(posts_match.group(1)),
                    last_activity=activity_text,
                    last_activity_ts=activity_ts.astimezone(UTC).isoformat(),
                    last_author=last_author,
                    thread_url=urljoin(BASE_URL, href),
                    category=section_category,
                    title=title,
                )
            )

    return threads


def _parse_problem_reactions(soup: BeautifulSoup) -> dict[str, list[str]]:
    reactions: dict[str, list[str]] = {}
    for row in soup.select("tr.problem-reaction-row"):
        reaction_type = row.get("data-reaction-type", "").strip()
        users_cell = row.select_one(".problem-reaction-users")
        if not reaction_type or users_cell is None:
            continue
        users = [link.get_text(" ", strip=True) for link in users_cell.select("a")]
        if not users and users_cell.get_text(" ", strip=True).lower() not in {
            "none",
            "none yet",
        }:
            text = users_cell.get_text(" ", strip=True)
            if text:
                users = [text]
        reactions[reaction_type] = users
    return reactions


def _parse_post_reactions(post_soup: BeautifulSoup) -> list[ForumReactionSummary]:
    items: list[ForumReactionSummary] = []
    for button in post_soup.select(".reaction-bar .reaction-btn"):
        reaction_type = button.get("data-type", "").strip()
        count_node = button.select_one(".reaction-count")
        count = int(count_node.get_text(" ", strip=True) or "0") if count_node else 0
        title = button.get("title", "")
        users_title = (
            title.split("\n\n", 1)[-1].replace("Users:", "").strip() if title else ""
        )
        if reaction_type:
            items.append(
                ForumReactionSummary(
                    reaction_type=reaction_type,
                    count=count,
                    users_title=users_title,
                )
            )
    return items


def parse_forum_thread_detail(html: str, thread_url: str) -> ForumThreadDetail:
    """Parse a full forum thread page including posts and problem metadata."""

    soup = BeautifulSoup(html, "html.parser")
    thread_key = thread_url.rstrip("/").rsplit("/", 1)[-1]
    title_text = soup.title.get_text(" ", strip=True) if soup.title else thread_key
    problem_number = ""
    title = title_text
    category = "general"

    if thread_key.isdigit():
        problem_number = thread_key
        category = "problem"
        title = f"Problem #{thread_key}"
    elif thread_key.startswith("blog:"):
        category = "blog"

    status_text = ""
    statement = ""
    tags = [tag.get_text(" ", strip=True) for tag in soup.select("#tags a")]
    additional_text = ""
    citation_text = ""
    formalized_url = ""
    comment_count = 0

    if category == "problem":
        status_node = soup.select_one("#prize")
        content_node = soup.select_one("#content")
        additional_node = soup.select_one(".problem-additional-text")
        citation_node = soup.select_one(".citationbox #content")
        comment_link = soup.select_one(".comment-count a")
        formalized_link = None
        for link in soup.select("a"):
            if link.get_text(
                " ", strip=True
            ) == "Yes" and "formal-conjectures" in link.get("href", ""):
                formalized_link = link
                break

        status_text = status_node.get_text(" ", strip=True) if status_node else ""
        statement = content_node.get_text("\n", strip=True) if content_node else ""
        additional_text = (
            additional_node.get_text("\n", strip=True) if additional_node else ""
        )
        citation_text = (
            citation_node.get_text("\n", strip=True) if citation_node else ""
        )
        formalized_url = formalized_link.get("href", "") if formalized_link else ""
        if comment_link:
            match = re.search(
                r"(\d+)\s+comments?",
                comment_link.get_text(" ", strip=True),
                re.IGNORECASE,
            )
            if match:
                comment_count = int(match.group(1))

    posts: list[ForumPost] = []
    for item in soup.select("li.post"):
        post_id = item.get("id", "").replace("post-", "")
        classes = item.get("class", [])
        depth = 0
        for class_name in classes:
            if class_name.startswith("depth-"):
                depth = int(class_name.split("-", 1)[1])
                break
        body = item.select_one(".post-body")
        meta = item.select_one(".post-meta")
        author_link = meta.select_one("a[href*='/forum/user/']") if meta else None
        anchor_link = meta.select_one("a[href*='#post-']") if meta else None
        posts.append(
            ForumPost(
                post_id=post_id,
                thread_key=thread_key,
                problem_number=problem_number,
                depth=depth,
                author_name=author_link.get_text(" ", strip=True)
                if author_link
                else "",
                author_username=(
                    author_link.get("href", "").rsplit("/", 1)[-1]
                    if author_link
                    else ""
                ),
                created_at=anchor_link.get_text(" ", strip=True) if anchor_link else "",
                anchor=urljoin(BASE_URL, anchor_link.get("href", ""))
                if anchor_link
                else "",
                content_markdown=body.get_text("\n", strip=True) if body else "",
                content_html=str(body) if body else "",
                reactions=_parse_post_reactions(item),
            )
        )

    return ForumThreadDetail(
        thread_key=thread_key,
        thread_url=thread_url,
        category=category,
        title=title,
        problem_number=problem_number,
        status_text=status_text,
        statement=statement,
        tags=tags,
        additional_text=additional_text,
        citation_text=citation_text,
        comment_count=comment_count,
        formalized_url=formalized_url,
        problem_reactions=_parse_problem_reactions(soup),
        posts=posts,
    )

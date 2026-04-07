"""Forum parsing utilities."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from bs4 import BeautifulSoup
from pydantic import BaseModel


class ForumThread(BaseModel):
    problem_number: str
    post_count: int
    last_activity: str
    last_activity_ts: str
    last_author: str


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

    lines = _extract_forum_lines(html)
    threads: list[ForumThread] = []
    index = 0

    while index + 4 < len(lines):
        number = lines[index]
        posts = lines[index + 1]
        last_activity = lines[index + 2]
        by_marker = lines[index + 3]
        author = lines[index + 4]

        if not number.isdigit() or by_marker.lower() != "by":
            index += 1
            continue

        posts_match = re.search(r"\((\d+)\s+posts?\)", posts, re.IGNORECASE)
        if not posts_match:
            index += 1
            continue

        activity_ts = parse_relative_time(last_activity, now=now)
        threads.append(
            ForumThread(
                problem_number=number,
                post_count=int(posts_match.group(1)),
                last_activity=last_activity,
                last_activity_ts=activity_ts.astimezone(UTC).isoformat(),
                last_author=author,
            )
        )
        index += 5

    return threads

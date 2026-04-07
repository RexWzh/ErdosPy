"""Typed data models for erdospy."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Problem(BaseModel):
    """A single Erdős problem with associated metadata."""

    number: str
    statement: str = ""
    status: str
    prize: str
    formalized: bool = False
    oeis: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    related_problems: list[str] = Field(default_factory=list)
    reactions: dict[str, list[str]] = Field(default_factory=dict)
    contributors: list[str] = Field(default_factory=list)
    lean_url: str = ""
    additional_text: str = ""
    comments_count: int = 0

    @property
    def has_prize(self) -> bool:
        return self.prize != "no"

    @property
    def difficulty_score(self) -> int:
        score = 0
        score += len(self.reactions.get("hard", [])) * 2
        score -= len(self.reactions.get("easy", []))
        return score

    @property
    def interest_score(self) -> int:
        score = self.comments_count
        for reaction_type, users in self.reactions.items():
            if reaction_type == "like":
                score += len(users) * 2
            elif reaction_type in {"collab", "working_on"}:
                score += len(users) * 3
        return score


class Comment(BaseModel):
    """A comment attached to a problem."""

    author: str
    author_username: str
    date: str
    content: str
    likes: int = 0


class ForumThread(BaseModel):
    """A forum thread summary from the forum listing page."""

    thread_key: str = ""
    problem_number: str
    post_count: int
    last_activity: str
    last_activity_ts: str
    last_author: str
    thread_url: str = ""
    category: str = "problem"
    title: str = ""


class ForumReactionSummary(BaseModel):
    """Forum reaction counts for a post or problem thread."""

    reaction_type: str
    count: int = 0
    users_title: str = ""


class ForumPost(BaseModel):
    """A parsed forum post within a thread."""

    post_id: str
    thread_key: str
    problem_number: str = ""
    depth: int = 0
    author_name: str = ""
    author_username: str = ""
    created_at: str = ""
    anchor: str = ""
    content_markdown: str = ""
    content_html: str = ""
    reactions: list[ForumReactionSummary] = Field(default_factory=list)


class ForumThreadDetail(BaseModel):
    """A full forum thread with problem metadata and posts."""

    thread_key: str
    thread_url: str
    category: str
    title: str
    problem_number: str = ""
    status_text: str = ""
    statement: str = ""
    tags: list[str] = Field(default_factory=list)
    additional_text: str = ""
    citation_text: str = ""
    comment_count: int = 0
    formalized_url: str = ""
    problem_reactions: dict[str, list[str]] = Field(default_factory=dict)
    posts: list[ForumPost] = Field(default_factory=list)


class ChangelogEntry(BaseModel):
    """A structured local changelog event."""

    change_type: str
    problem_number: str
    description: str
    detected_at: str

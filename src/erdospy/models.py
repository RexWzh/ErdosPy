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

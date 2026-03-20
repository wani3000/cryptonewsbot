from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Article:
    source_name: str
    source_url: str
    canonical_url: str
    title: str
    published_at: datetime
    summary: str
    content: str
    fingerprint: str
    collected_at: datetime = field(default_factory=utc_now)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class ArticleSummary:
    article_id: str
    title: str
    source_name: str
    canonical_url: str
    key_point: str
    why_it_matters: str
    published_at: datetime
    template_type: str = "incident"
    incident_type: str = "general"
    cluster_size: int = 1
    related_sources: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class WritingStyleVariant:
    name: str
    x_instruction: str = ""
    telegram_instruction: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WritingStyleVariant":
        return cls(
            name=str(payload.get("name", "default")).strip() or "default",
            x_instruction=str(payload.get("x_instruction", "")),
            telegram_instruction=str(payload.get("telegram_instruction", "")),
        )


@dataclass(frozen=True)
class GeneratedPost:
    article_id: str
    headline: str
    body: str
    telegram_body: str = ""
    writing_style_name: str = ""
    x_posted_tweet_id: str = ""
    created_at: datetime = field(default_factory=utc_now)
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class FeedFetchResult:
    url: str
    source_name: str
    status: str
    item_count: int
    error_message: str = ""


@dataclass(frozen=True)
class StyleProfile:
    display_name: str
    tone: str
    audience: str
    output_language: str = "en"
    writing_guidelines: List[str] = field(default_factory=list)
    preferred_cta: str = ""
    focus_topics: List[str] = field(default_factory=list)
    forbidden_phrases: List[str] = field(default_factory=list)
    signature: str = ""
    hashtags: List[str] = field(default_factory=list)
    writing_style_variants: List[WritingStyleVariant] = field(default_factory=list)
    max_posts: int = 5
    max_post_length: int = 280

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StyleProfile":
        return cls(
            display_name=str(payload.get("display_name", "Default Analyst")),
            tone=str(payload.get("tone", "concise, analytical")),
            audience=str(payload.get("audience", "crypto readers")),
            output_language=str(payload.get("output_language", "en")),
            writing_guidelines=[str(item) for item in payload.get("writing_guidelines", [])],
            preferred_cta=str(payload.get("preferred_cta", "")),
            focus_topics=[str(item) for item in payload.get("focus_topics", [])],
            forbidden_phrases=[str(item) for item in payload.get("forbidden_phrases", [])],
            signature=str(payload.get("signature", "")),
            hashtags=[str(item) for item in payload.get("hashtags", [])],
            writing_style_variants=[
                WritingStyleVariant.from_dict(item) for item in payload.get("writing_style_variants", [])
            ],
            max_posts=max(int(payload.get("max_posts", 5)), 1),
            max_post_length=max(int(payload.get("max_post_length", 280)), 80),
        )


@dataclass(frozen=True)
class RunResult:
    run_id: str
    articles: List[Article]
    summaries: List[ArticleSummary]
    posts: List[GeneratedPost]
    telegram_delivered: bool
    x_delivered: bool
    feed_results: List[FeedFetchResult]

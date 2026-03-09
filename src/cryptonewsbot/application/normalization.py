from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cryptonewsbot.domain.models import Article


WHITESPACE_RE = re.compile(r"\s+")
DROP_QUERY_PREFIXES = ("utm_", "fbclid", "gclid")


def normalize_article(raw_item: Dict[str, str], source_url: str) -> Article:
    title = compact_text(raw_item.get("title", "Untitled"))
    summary = compact_text(raw_item.get("summary", ""))
    content = compact_text(raw_item.get("content", summary))
    canonical_url = canonicalize_url(raw_item.get("url", source_url))
    published_at = raw_item.get("published_at")
    if not isinstance(published_at, datetime):
        published_at = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    fingerprint = make_fingerprint(title=title, canonical_url=canonical_url, summary=summary)
    return Article(
        source_name=compact_text(raw_item.get("source_name", source_url)),
        source_url=source_url,
        canonical_url=canonical_url,
        title=title,
        published_at=published_at.astimezone(timezone.utc),
        summary=summary,
        content=content,
        fingerprint=fingerprint,
    )


def compact_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value or "").strip()


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.startswith(DROP_QUERY_PREFIXES)
    ]
    normalized_path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), normalized_path, urlencode(filtered_query), ""))


def make_fingerprint(title: str, canonical_url: str, summary: str) -> str:
    base = "|".join(
        [
            title.lower(),
            canonical_url.lower(),
            compact_text(summary).lower()[:280],
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

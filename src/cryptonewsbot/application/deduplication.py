from __future__ import annotations

from typing import Iterable, List, Set

from cryptonewsbot.domain.models import Article


def deduplicate_articles(
    articles: Iterable[Article],
    known_fingerprints: Set[str],
    known_urls: Set[str] | None = None,
) -> List[Article]:
    seen_fingerprints = set(known_fingerprints)
    seen_urls = set(known_urls or set())
    unique_articles = []
    for article in sorted(articles, key=lambda item: item.published_at, reverse=True):
        if article.fingerprint in seen_fingerprints:
            continue
        if article.canonical_url in seen_urls:
            continue
        seen_fingerprints.add(article.fingerprint)
        seen_urls.add(article.canonical_url)
        unique_articles.append(article)
    return unique_articles

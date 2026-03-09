from __future__ import annotations

from typing import Iterable, List, Set

from cryptonewsbot.domain.models import Article


def deduplicate_articles(articles: Iterable[Article], known_fingerprints: Set[str]) -> List[Article]:
    seen_fingerprints = set(known_fingerprints)
    unique_articles = []
    for article in sorted(articles, key=lambda item: item.published_at, reverse=True):
        if article.fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(article.fingerprint)
        unique_articles.append(article)
    return unique_articles

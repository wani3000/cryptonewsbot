from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Set

from cryptonewsbot.domain.models import Article


TOKEN_RE = re.compile(r"\w+", re.UNICODE)
TITLE_SOURCE_SPLIT_RE = re.compile(r"\s+(?:[-|:])\s+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "bitcoin",
    "blockchain",
    "by",
    "coindesk",
    "cointelegraph",
    "crypto",
    "cryptocurrency",
    "decrypt",
    "ethereum",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "report",
    "says",
    "the",
    "this",
    "to",
    "uses",
    "using",
    "with",
}
STORY_CLUSTER_THRESHOLD = 0.68


@dataclass(frozen=True)
class StoryCluster:
    representative: Article
    articles: List[Article]

    @property
    def size(self) -> int:
        return len(self.articles)

    @property
    def source_names(self) -> List[str]:
        seen = set()
        names: List[str] = []
        for article in self.articles:
            if article.source_name in seen:
                continue
            seen.add(article.source_name)
            names.append(article.source_name)
        return names


def cluster_articles(articles: Iterable[Article], source_priorities: Dict[str, int] | None = None) -> List[StoryCluster]:
    source_priorities = source_priorities or {}
    sorted_articles = sorted(
        articles,
        key=lambda article: (source_priorities.get(article.source_url, 0), article.published_at),
        reverse=True,
    )
    clusters: List[StoryCluster] = []
    for article in sorted_articles:
        best_index = -1
        best_score = 0.0
        for index, cluster in enumerate(clusters):
            score = article_similarity(article, cluster.representative)
            if score > best_score:
                best_score = score
                best_index = index
        if best_index >= 0 and best_score >= STORY_CLUSTER_THRESHOLD:
            existing = clusters[best_index]
            combined = existing.articles + [article]
            representative = select_representative(combined, source_priorities)
            clusters[best_index] = StoryCluster(representative=representative, articles=combined)
            continue
        clusters.append(StoryCluster(representative=article, articles=[article]))
    return clusters


def article_similarity(left: Article, right: Article) -> float:
    left_title = normalized_title(left.title)
    right_title = normalized_title(right.title)
    title_ratio = SequenceMatcher(None, left_title, right_title).ratio()
    title_overlap = overlap_score(tokenize(left_title), tokenize(right_title))
    content_overlap = overlap_score(story_tokens(left), story_tokens(right))
    return max(title_ratio, title_overlap, content_overlap)


def select_representative(articles: List[Article], source_priorities: Dict[str, int]) -> Article:
    return max(
        articles,
        key=lambda article: (
            source_priorities.get(article.source_url, 0),
            len(story_tokens(article)),
            article.published_at,
        ),
    )


def normalized_title(value: str) -> str:
    base = TITLE_SOURCE_SPLIT_RE.split(value.strip(), 1)[0]
    return " ".join(tokenize(base))


def story_tokens(article: Article) -> Set[str]:
    return tokenize(f"{normalized_title(article.title)} {article.summary}")


def tokenize(value: str) -> Set[str]:
    return {
        token
        for token in TOKEN_RE.findall(value.lower())
        if len(token) > 2 and token not in STOPWORDS and not token.isdigit()
    }


def overlap_score(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = len(left & right)
    return overlap / max(1, min(len(left), len(right)))

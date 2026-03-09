from __future__ import annotations

from typing import Iterable, List

from cryptonewsbot.domain.models import Article, StyleProfile


SECURITY_KEYWORDS = [
    "hack",
    "hacked",
    "scam",
    "scammer",
    "fraud",
    "phishing",
    "exploit",
    "breach",
    "drain",
    "drainer",
    "wallet",
    "stolen",
    "launder",
    "money laundering",
    "seized",
    "freeze",
    "forensics",
    "investigation",
    "sanction",
    "pig butchering",
    "ransomware",
    "theft",
    "attacker",
    "malware",
    "approval",
    "mev",
]

MARKET_ONLY_KEYWORDS = [
    "etf inflow",
    "price slips",
    "price surge",
    "price rises",
    "bull market",
    "bear market",
    "stock futures",
    "oil futures",
    "reserve asset",
    "treasury valued",
]


def select_relevant_articles(
    articles: Iterable[Article], style_profile: StyleProfile, limit: int
) -> List[Article]:
    focus_topics = [topic.lower() for topic in style_profile.focus_topics]
    candidate_articles = [article for article in articles if is_security_relevant(article, focus_topics)]
    scored = sorted(
        candidate_articles,
        key=lambda article: (_score_article(article, focus_topics), article.published_at),
        reverse=True,
    )
    if any(_score_article(article, focus_topics) > 0 for article in scored):
        scored = [article for article in scored if _score_article(article, focus_topics) > 0]
    return scored[:limit]


def _score_article(article: Article, focus_topics: List[str]) -> int:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    topic_score = sum(2 for topic in focus_topics if topic in haystack)
    security_score = sum(3 for keyword in SECURITY_KEYWORDS if keyword in haystack)
    return topic_score + security_score


def is_security_relevant(article: Article, focus_topics: List[str]) -> bool:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    has_security_signal = any(keyword in haystack for keyword in SECURITY_KEYWORDS)
    has_focus_signal = any(topic in haystack for topic in focus_topics)
    market_only_signal = any(keyword in haystack for keyword in MARKET_ONLY_KEYWORDS)
    if has_security_signal:
        return True
    if has_focus_signal and not market_only_signal:
        return True
    return False

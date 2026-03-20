from __future__ import annotations

from typing import Dict, Iterable, List

from cryptonewsbot.domain.models import Article, StyleProfile


ENGLISH_SECURITY_KEYWORDS = [
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

KOREAN_SECURITY_KEYWORDS = [
    "해킹",
    "사기",
    "피싱",
    "탈취",
    "자금세탁",
    "세탁",
    "제재",
    "압수",
    "동결",
    "조사",
    "수사",
    "지갑",
    "악성코드",
    "랜섬웨어",
    "취약점",
]

JAPANESE_SECURITY_KEYWORDS = [
    "ハッキング",
    "詐欺",
    "フィッシング",
    "流出",
    "盗難",
    "マネロン",
    "資金洗浄",
    "制裁",
    "押収",
    "凍結",
    "調査",
    "捜査",
    "ウォレット",
    "マルウェア",
    "脆弱性",
]

CHINESE_SECURITY_KEYWORDS = [
    "黑客",
    "诈骗",
    "钓鱼",
    "洗钱",
    "监管",
    "冻结",
    "扣押",
    "盗窃",
    "钱包",
    "恶意软件",
    "勒索软件",
    "漏洞",
    "调查",
]

SECURITY_KEYWORDS = (
    ENGLISH_SECURITY_KEYWORDS
    + KOREAN_SECURITY_KEYWORDS
    + JAPANESE_SECURITY_KEYWORDS
    + CHINESE_SECURITY_KEYWORDS
)

ENGLISH_MARKET_ONLY_KEYWORDS = [
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

KOREAN_MARKET_ONLY_KEYWORDS = [
    "가격 상승",
    "가격 하락",
    "강세장",
    "약세장",
    "현물 etf",
]

JAPANESE_MARKET_ONLY_KEYWORDS = [
    "価格上昇",
    "価格下落",
    "強気相場",
    "弱気相場",
    "現物etf",
]

CHINESE_MARKET_ONLY_KEYWORDS = [
    "价格上涨",
    "价格下跌",
    "牛市",
    "熊市",
    "现货etf",
]

MARKET_ONLY_KEYWORDS = (
    ENGLISH_MARKET_ONLY_KEYWORDS
    + KOREAN_MARKET_ONLY_KEYWORDS
    + JAPANESE_MARKET_ONLY_KEYWORDS
    + CHINESE_MARKET_ONLY_KEYWORDS
)

PROMOTIONAL_NOISE_KEYWORDS = [
    "best crypto to buy",
    "best coin to buy",
    "top crypto to buy",
    "price prediction",
    "bull run picks",
    "presale",
    "pre-sale",
    "token launch",
    "launches on",
    "launch date",
    "airdrop guide",
    "sponsored",
    "partner content",
    "how to buy",
    "buy now",
    "march launch",
    "april launch",
    "this week launch",
    "launches this",
    "ico",
]

LOW_SIGNAL_TITLE_KEYWORDS = [
    "market outlook",
    "analyst says",
    "price outlook",
    "could soar",
    "could explode",
    "next bitcoin",
]

SEARCH_AGGREGATED_HOST_HINTS = [
    "news.google.com",
]


def select_relevant_articles(
    articles: Iterable[Article],
    style_profile: StyleProfile,
    limit: int,
    source_priorities: Dict[str, int] | None = None,
) -> List[Article]:
    focus_topics = [topic.lower() for topic in style_profile.focus_topics]
    source_priorities = source_priorities or {}
    candidate_articles = [article for article in articles if is_security_relevant(article, focus_topics)]
    scored = sorted(
        candidate_articles,
        key=lambda article: (
            _score_article(article, focus_topics, source_priorities),
            article.published_at,
        ),
        reverse=True,
    )
    if any(_content_score(article, focus_topics) > 0 for article in scored):
        scored = [article for article in scored if _content_score(article, focus_topics) > 0]
    return scored[:limit]


def _score_article(article: Article, focus_topics: List[str], source_priorities: Dict[str, int]) -> int:
    return _content_score(article, focus_topics) + source_priorities.get(article.source_url, 0)


def _content_score(article: Article, focus_topics: List[str]) -> int:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    topic_score = sum(2 for topic in focus_topics if topic in haystack)
    security_score = sum(3 for keyword in SECURITY_KEYWORDS if keyword in haystack)
    return topic_score + security_score


def is_security_relevant(article: Article, focus_topics: List[str]) -> bool:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    title = article.title.lower()
    if is_low_quality_article(article):
        return False
    has_security_signal = any(keyword in haystack for keyword in SECURITY_KEYWORDS)
    has_focus_signal = any(topic in haystack for topic in focus_topics)
    market_only_signal = any(keyword in haystack for keyword in MARKET_ONLY_KEYWORDS)
    if _is_search_aggregated(article) and not _has_strong_search_signal(haystack, title, focus_topics):
        return False
    if has_security_signal:
        return True
    if has_focus_signal and not market_only_signal:
        return True
    return False


def is_low_quality_article(article: Article) -> bool:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    title = article.title.lower()
    if any(keyword in title for keyword in PROMOTIONAL_NOISE_KEYWORDS):
        return True
    if any(keyword in haystack for keyword in PROMOTIONAL_NOISE_KEYWORDS):
        return True
    if _is_search_aggregated(article) and any(keyword in title for keyword in LOW_SIGNAL_TITLE_KEYWORDS):
        return True
    return False


def _is_search_aggregated(article: Article) -> bool:
    source_url = article.source_url.lower()
    source_name = article.source_name.lower()
    return any(host in source_url for host in SEARCH_AGGREGATED_HOST_HINTS) or "google news" in source_name


def _has_strong_search_signal(haystack: str, title: str, focus_topics: List[str]) -> bool:
    security_hits = sum(1 for keyword in SECURITY_KEYWORDS if keyword in haystack)
    focus_hits = sum(1 for topic in focus_topics if topic in haystack)
    title_security_hits = sum(1 for keyword in SECURITY_KEYWORDS if keyword in title)
    if title_security_hits >= 1 and (security_hits + focus_hits) >= 2:
        return True
    if security_hits >= 2:
        return True
    return False

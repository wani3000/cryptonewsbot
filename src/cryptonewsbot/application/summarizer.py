from __future__ import annotations

import re
from typing import Iterable, List

from cryptonewsbot.domain.models import Article, ArticleSummary, StyleProfile


PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?%")
NUMBER_HINT_RE = re.compile(r"\b\d+(?:\.\d+)?(?:m|b|k)?\b", re.IGNORECASE)
INCIDENT_PATTERNS = [
    (
        "bridge_hack",
        [
            "bridge hack",
            "bridge exploit",
            "cross-chain bridge",
            "bridge drained",
            "validator compromise",
        ],
    ),
    (
        "drainer",
        [
            "drainer",
            "wallet drain",
            "wallet drained",
            "approval scam",
            "approval phishing",
        ],
    ),
    (
        "phishing",
        [
            "phishing",
            "spoofed",
            "fake website",
            "fake support",
            "seed phrase",
            "social engineering",
        ],
    ),
    (
        "sanction_seizure",
        [
            "seized",
            "seizure",
            "freeze suspicious funds",
            "frozen funds",
            "sanction",
            "treasury",
            "doj",
            "law enforcement",
        ],
    ),
    (
        "pyramid_scam",
        [
            "pyramid scheme",
            "ponzi",
            "pig butchering",
            "romance scam",
            "investment scam",
            "high yield",
            "guaranteed return",
        ],
    ),
]


def summarize_articles(articles: Iterable[Article], style_profile: StyleProfile) -> List[ArticleSummary]:
    focus_text = ", ".join(style_profile.focus_topics[:4]) or "crypto market structure"
    summaries = []
    for article in articles:
        summary_text = article.summary or article.content or article.title
        key_point = trim_text(summary_text, 180)
        template_type = classify_template(article)
        incident_type = classify_incident_type(article)
        why_it_matters = build_why_it_matters(
            template_type,
            incident_type,
            style_profile.audience,
            focus_text,
        )
        summaries.append(
            ArticleSummary(
                article_id=article.id,
                title=article.title,
                source_name=article.source_name,
                canonical_url=article.canonical_url,
                key_point=key_point,
                why_it_matters=why_it_matters,
                published_at=article.published_at,
                template_type=template_type,
                incident_type=incident_type,
            )
        )
    return summaries


def classify_template(article: Article) -> str:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    if any(keyword in haystack for keyword in ["what do you think", "mystery", "unclear", "community", "discussion"]):
        return "discussion"
    if PERCENT_RE.search(haystack) or (
        any(keyword in haystack for keyword in ["statistics", "stats", "year-over-year", "month-over-month"])
        and NUMBER_HINT_RE.search(haystack)
    ):
        return "statistical"
    return "incident"


def classify_incident_type(article: Article) -> str:
    haystack = " ".join([article.title, article.summary, article.content]).lower()
    for incident_type, keywords in INCIDENT_PATTERNS:
        if any(keyword in haystack for keyword in keywords):
            return incident_type
    return "general"


def build_why_it_matters(template_type: str, incident_type: str, audience: str, focus_text: str) -> str:
    if template_type == "statistical":
        return (
            f"From a ChainBounty view, the data matters because it shows where attacker behavior, losses, "
            f"and defensive pressure are moving for {audience}."
        )
    if template_type == "discussion":
        return (
            f"From a ChainBounty view, the facts are still incomplete, and the community may surface threat "
            f"patterns tied to {focus_text}."
        )
    if incident_type == "drainer":
        return (
            "From a ChainBounty view, drainer cases reveal where approval abuse, wallet hygiene failures, "
            "and rapid fund movement still beat user defenses."
        )
    if incident_type == "phishing":
        return (
            "From a ChainBounty view, phishing cases show how fake interfaces, spoofed identities, and user-trust "
            "gaps still convert into onchain losses."
        )
    if incident_type == "bridge_hack":
        return (
            "From a ChainBounty view, bridge hacks expose validator, custody, and cross-chain trust failures that "
            "can scale losses fast."
        )
    if incident_type == "sanction_seizure":
        return (
            "From a ChainBounty view, seizure and sanction stories reveal where laundering routes, exchange controls, "
            "and legal intervention are tightening."
        )
    if incident_type == "pyramid_scam":
        return (
            "From a ChainBounty view, pyramid and investment scam cases show how social engineering, false returns, "
            "and victim funnel design still drive losses."
        )
    return (
        f"From a ChainBounty view, this matters because it can reveal attacker methods, weak controls, "
        f"or new risk around {focus_text}."
    )


def trim_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."

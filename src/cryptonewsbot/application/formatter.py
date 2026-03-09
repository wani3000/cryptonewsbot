from __future__ import annotations

from typing import Iterable, List

from cryptonewsbot.domain.models import ArticleSummary, FeedFetchResult, GeneratedPost


def format_digest(posts: Iterable[GeneratedPost], feed_results: Iterable[FeedFetchResult]) -> str:
    posts = list(posts)
    feed_results = list(feed_results)
    if not posts:
        message = "No new crypto news matched the current rules in the last 24 hours."
        errors = [result for result in feed_results if result.status != "ok"]
        if errors:
            message = (
                f"{message}\n\nFeed issues: "
                + "; ".join(f"{result.source_name} ({result.error_message})" for result in errors[:3])
            )
        return message

    lines = ["cryptonewsbot daily digest", ""]
    for index, post in enumerate(posts, start=1):
        lines.append(f"{index}. {post.headline}")
        lines.append(post.body)
        lines.append("")
    ok_count = len([result for result in feed_results if result.status == "ok"])
    error_count = len(feed_results) - ok_count
    lines.append(f"Feeds checked: {len(feed_results)} | OK: {ok_count} | Errors: {error_count}")
    return "\n".join(lines).strip()


def format_telegram_message_pairs(
    summaries: Iterable[ArticleSummary],
    posts: Iterable[GeneratedPost],
    feed_results: Iterable[FeedFetchResult],
) -> List[str]:
    summaries = list(summaries)
    posts = list(posts)
    feed_results = list(feed_results)
    if not posts:
        return [format_digest(posts, feed_results)]

    summary_by_article = {summary.article_id: summary for summary in summaries}
    messages = []
    for index, post in enumerate(posts, start=1):
        summary = summary_by_article.get(post.article_id)
        if summary is None:
            continue
        messages.append(build_news_message(index, summary))
        messages.append(build_post_message(index, post))

    ok_count = len([result for result in feed_results if result.status == "ok"])
    error_count = len(feed_results) - ok_count
    messages.append(f"Feeds checked: {len(feed_results)} | OK: {ok_count} | Errors: {error_count}")
    return messages


def build_news_message(index: int, summary: ArticleSummary) -> str:
    title = {
        "incident": "News",
        "statistical": "Stats",
        "discussion": "Discussion",
    }.get(summary.template_type, "News")
    emoji = select_message_emoji(summary)
    return (
        f"[{index}] {title}\n"
        f"Title: {emoji} {summary.title}\n"
        f"Summary: {summary.key_point}\n"
        f"Why it matters: {summary.why_it_matters}\n"
        f"Source: {summary.canonical_url}"
    )


def build_post_message(index: int, post: GeneratedPost) -> str:
    body = post.telegram_body or post.body
    return body


def select_message_emoji(summary: ArticleSummary) -> str:
    if summary.template_type == "statistical":
        return "📉"
    if summary.template_type == "discussion":
        return "🔍"
    if summary.incident_type == "drainer":
        return "🚨"
    if summary.incident_type == "phishing":
        return "🎣"
    if summary.incident_type == "bridge_hack":
        return "🌉"
    if summary.incident_type == "sanction_seizure":
        return "🔒"
    if summary.incident_type == "pyramid_scam":
        return "⚠️"
    return "📊"

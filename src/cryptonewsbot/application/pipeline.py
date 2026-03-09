from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptonewsbot.application.deduplication import deduplicate_articles
from cryptonewsbot.application.filtering import select_relevant_articles
from cryptonewsbot.application.formatter import format_digest, format_telegram_message_pairs
from cryptonewsbot.application.normalization import normalize_article
from cryptonewsbot.application.post_generation import generate_posts
from cryptonewsbot.application.summarizer import summarize_articles
from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import RunResult
from cryptonewsbot.infrastructure.rss import RSSCollector
from cryptonewsbot.infrastructure.storage import SQLiteRepository
from cryptonewsbot.infrastructure.telegram import TelegramClient


@dataclass
class PipelineOutput:
    run_result: RunResult
    digest_text: str
    telegram_messages: list[str]


def run_daily_digest(config: AppConfig) -> PipelineOutput:
    config.validate()
    style_profile = config.load_style_profile()
    repository = SQLiteRepository(config.database_path)
    repository.initialize()

    collector = RSSCollector()
    telegram_client = TelegramClient(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        dry_run=config.dry_run,
    )

    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    collection_result = collector.collect_since(config.resolved_feed_urls, window_start)
    normalized_articles = [
        normalize_article(item, source_url=item["source_url"]) for item in collection_result.items
    ]
    unique_articles = deduplicate_articles(
        normalized_articles,
        known_fingerprints=set(),
    )
    selected_articles = select_relevant_articles(unique_articles, style_profile, config.max_articles)
    summaries = summarize_articles(selected_articles, style_profile)
    posts = generate_posts(summaries, style_profile, config)
    digest_text = format_digest(posts, collection_result.feed_results)
    telegram_messages = format_telegram_message_pairs(summaries, posts, collection_result.feed_results)
    delivered = telegram_client.send_messages(telegram_messages)

    run_id = str(uuid4())
    repository.save_run(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        articles=selected_articles,
        posts=posts,
        feed_results=collection_result.feed_results,
        delivered_to_telegram=delivered,
    )
    return PipelineOutput(
        run_result=RunResult(
            run_id=run_id,
            articles=selected_articles,
            summaries=summaries,
            posts=posts,
            telegram_delivered=delivered,
            feed_results=collection_result.feed_results,
        ),
        digest_text=digest_text,
        telegram_messages=telegram_messages,
    )

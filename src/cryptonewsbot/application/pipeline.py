from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptonewsbot.application.clustering import cluster_articles
from cryptonewsbot.application.deduplication import deduplicate_articles
from cryptonewsbot.application.filtering import select_relevant_articles
from cryptonewsbot.application.formatter import format_digest, format_telegram_message_pairs
from cryptonewsbot.application.normalization import normalize_article
from cryptonewsbot.application.post_generation import (
    generate_posts,
    resolve_next_writing_style_start_index,
    resolve_writing_style_variants,
)
from cryptonewsbot.application.summarizer import summarize_articles
from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import RunResult
from cryptonewsbot.infrastructure.rss import RSSCollector
from cryptonewsbot.infrastructure.storage import SQLiteRepository
from cryptonewsbot.infrastructure.telegram import TelegramClient
from cryptonewsbot.infrastructure.x import XClient


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
    x_client = XClient.from_config(config)

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    delivered_since = now - timedelta(hours=config.repeat_suppression_hours)
    known_fingerprints, known_urls = repository.get_recent_delivered_article_keys(delivered_since)
    collection_result = collector.collect_since(config.resolved_feed_urls, window_start)
    normalized_articles = [
        normalize_article(item, source_url=item["source_url"]) for item in collection_result.items
    ]
    unique_articles = deduplicate_articles(
        normalized_articles,
        known_fingerprints=known_fingerprints,
        known_urls=known_urls,
    )
    story_clusters = cluster_articles(unique_articles, source_priorities=config.feed_source_priorities)
    clustered_articles = [cluster.representative for cluster in story_clusters]
    cluster_metadata = {
        cluster.representative.id: {
            "cluster_size": cluster.size,
            "related_sources": cluster.source_names,
        }
        for cluster in story_clusters
    }
    selected_articles = select_relevant_articles(
        clustered_articles,
        style_profile,
        config.max_articles,
        source_priorities=config.feed_source_priorities,
    )
    summaries = summarize_articles(selected_articles, style_profile, cluster_metadata=cluster_metadata)
    style_variants = resolve_writing_style_variants(style_profile)
    writing_style_start_index = resolve_next_writing_style_start_index(
        style_variants,
        repository.get_last_writing_style_name(),
    )
    posts = generate_posts(
        summaries,
        style_profile,
        config,
        writing_style_rotation_seed=writing_style_start_index,
    )
    article_by_id = {article.id: article for article in selected_articles}
    digest_text = format_digest(posts, collection_result.feed_results)
    telegram_messages = format_telegram_message_pairs(summaries, posts, collection_result.feed_results)
    delivered = telegram_client.send_messages(telegram_messages)
    x_known_fingerprints, x_known_urls = repository.get_recent_x_delivered_article_keys(delivered_since)
    x_eligible_posts = [
        post
        for post in posts
        if post.article_id in article_by_id
        and article_by_id[post.article_id].fingerprint not in x_known_fingerprints
        and article_by_id[post.article_id].canonical_url not in x_known_urls
    ]
    x_posted_tweet_ids = x_client.post_generated_posts(x_eligible_posts, config.x_max_posts)
    posts = [
        replace(post, x_posted_tweet_id=x_posted_tweet_ids.get(post.article_id, ""))
        for post in posts
    ]
    delivered_to_x = bool(x_posted_tweet_ids)

    run_id = str(uuid4())
    repository.save_run(
        run_id=run_id,
        started_at=now,
        articles=selected_articles,
        posts=posts,
        feed_results=collection_result.feed_results,
        delivered_to_telegram=delivered,
        delivered_to_x=delivered_to_x,
    )
    return PipelineOutput(
        run_result=RunResult(
            run_id=run_id,
            articles=selected_articles,
            summaries=summaries,
            posts=posts,
            telegram_delivered=delivered,
            x_delivered=delivered_to_x,
            feed_results=collection_result.feed_results,
        ),
        digest_text=digest_text,
        telegram_messages=telegram_messages,
    )

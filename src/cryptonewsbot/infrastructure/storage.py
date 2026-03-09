from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Set

from cryptonewsbot.database import connect
from cryptonewsbot.domain.models import Article, FeedFetchResult, GeneratedPost


class SQLiteRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        connection = connect(self._database_path)
        connection.close()

    def get_known_fingerprints(self) -> Set[str]:
        connection = connect(self._database_path)
        try:
            rows = connection.execute("SELECT fingerprint FROM articles").fetchall()
            return {row["fingerprint"] for row in rows}
        finally:
            connection.close()

    def save_run(
        self,
        run_id: str,
        started_at: datetime,
        articles: Iterable[Article],
        posts: Iterable[GeneratedPost],
        feed_results: Iterable[FeedFetchResult],
        delivered_to_telegram: bool,
    ) -> None:
        connection = connect(self._database_path)
        try:
            article_list = list(articles)
            post_list = list(posts)
            feed_result_list = list(feed_results)
            for article in article_list:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO articles (
                        id, source_name, source_url, canonical_url, title, published_at,
                        summary, content, fingerprint, collected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article.id,
                        article.source_name,
                        article.source_url,
                        article.canonical_url,
                        article.title,
                        article.published_at.isoformat(),
                        article.summary,
                        article.content,
                        article.fingerprint,
                        article.collected_at.isoformat(),
                    ),
                )
            connection.execute(
                """
                INSERT INTO runs (id, started_at, article_count, post_count, delivered_to_telegram, feed_error_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    started_at.isoformat(),
                    len(article_list),
                    len(post_list),
                    1 if delivered_to_telegram else 0,
                    len([result for result in feed_result_list if result.status != "ok"]),
                ),
            )
            for result in feed_result_list:
                connection.execute(
                    """
                    INSERT INTO feed_fetch_results (
                        run_id, url, source_name, status, item_count, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        result.url,
                        result.source_name,
                        result.status,
                        result.item_count,
                        result.error_message,
                    ),
                )
            for post in post_list:
                connection.execute(
                    """
                    INSERT INTO generated_posts (id, run_id, article_id, headline, body, telegram_body, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post.id,
                        run_id,
                        post.article_id,
                        post.headline,
                        post.body,
                        post.telegram_body,
                        post.created_at.isoformat(),
                    ),
                )
            connection.commit()
        finally:
            connection.close()

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Set, Tuple

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

    def get_recent_delivered_article_keys(self, since: datetime) -> Tuple[Set[str], Set[str]]:
        connection = connect(self._database_path)
        try:
            rows = connection.execute(
                """
                SELECT fingerprint, canonical_url
                FROM delivered_articles
                WHERE delivered_at >= ?
                """,
                (since.isoformat(),),
            ).fetchall()
            fingerprints = {row["fingerprint"] for row in rows}
            canonical_urls = {row["canonical_url"] for row in rows}
            return fingerprints, canonical_urls
        finally:
            connection.close()

    def get_recent_x_delivered_article_keys(self, since: datetime) -> Tuple[Set[str], Set[str]]:
        connection = connect(self._database_path)
        try:
            rows = connection.execute(
                """
                SELECT fingerprint, canonical_url
                FROM delivered_x_posts
                WHERE delivered_at >= ?
                """,
                (since.isoformat(),),
            ).fetchall()
            fingerprints = {row["fingerprint"] for row in rows}
            canonical_urls = {row["canonical_url"] for row in rows}
            return fingerprints, canonical_urls
        finally:
            connection.close()

    def get_last_writing_style_name(self) -> str:
        connection = connect(self._database_path)
        try:
            row = connection.execute(
                """
                SELECT writing_style_name
                FROM generated_posts
                WHERE writing_style_name != ''
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return ""
            return str(row["writing_style_name"] or "")
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
        delivered_to_x: bool,
    ) -> None:
        connection = connect(self._database_path)
        try:
            article_list = list(articles)
            post_list = list(posts)
            feed_result_list = list(feed_results)
            persisted_article_ids: dict[str, str] = {}
            for article in article_list:
                existing = connection.execute(
                    "SELECT id FROM articles WHERE fingerprint = ?",
                    (article.fingerprint,),
                ).fetchone()
                if existing is not None:
                    persisted_article_ids[article.id] = existing["id"]
                    continue
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
                persisted_article_ids[article.id] = article.id
            connection.execute(
                """
                INSERT INTO runs (
                    id, started_at, article_count, post_count, delivered_to_telegram, delivered_to_x, feed_error_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    started_at.isoformat(),
                    len(article_list),
                    len(post_list),
                    1 if delivered_to_telegram else 0,
                    1 if delivered_to_x else 0,
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
                    INSERT INTO generated_posts (
                        id, run_id, article_id, headline, body, telegram_body, writing_style_name, x_posted_tweet_id, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post.id,
                        run_id,
                        persisted_article_ids.get(post.article_id, post.article_id),
                        post.headline,
                        post.body,
                        post.telegram_body,
                        post.writing_style_name,
                        post.x_posted_tweet_id,
                        post.created_at.isoformat(),
                    ),
                )
            if delivered_to_telegram:
                for article in article_list:
                    connection.execute(
                        """
                        INSERT INTO delivered_articles (run_id, fingerprint, canonical_url, title, delivered_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            article.fingerprint,
                            article.canonical_url,
                            article.title,
                            started_at.isoformat(),
                        ),
                    )
            if delivered_to_x:
                article_by_id = {article.id: article for article in article_list}
                for post in post_list:
                    if not post.x_posted_tweet_id:
                        continue
                    article = article_by_id.get(post.article_id)
                    if article is None:
                        continue
                    connection.execute(
                        """
                        INSERT INTO delivered_x_posts (run_id, fingerprint, canonical_url, title, tweet_id, delivered_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            article.fingerprint,
                            article.canonical_url,
                            article.title,
                            post.x_posted_tweet_id,
                            started_at.isoformat(),
                        ),
                    )
            connection.commit()
        finally:
            connection.close()

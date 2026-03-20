import os
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from cryptonewsbot.application.pipeline import run_daily_digest
from cryptonewsbot.config import AppConfig


def build_rss_fixture(now: Optional[datetime] = None) -> str:
    current_time = now or datetime.now(timezone.utc)
    article_time = format_datetime(current_time - timedelta(hours=2), usegmt=True)
    filtered_time = format_datetime(current_time - timedelta(hours=1), usegmt=True)
    return textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0">
          <channel>
            <title>Crypto Feed</title>
            <item>
              <title>Wallet drainer exploits phishing page and steals user funds</title>
              <link>https://example.com/articles/wallet-drainer?utm_source=test</link>
              <description>Attackers used a phishing page to drain wallets after malicious approvals.</description>
              <pubDate>{article_time}</pubDate>
            </item>
            <item>
              <title>Sports headline</title>
              <link>https://example.com/articles/sports</link>
              <description>This item should be filtered out by crypto focus topics.</description>
              <pubDate>{filtered_time}</pubDate>
            </item>
          </channel>
        </rss>
        """
    )


class PipelineTests(unittest.TestCase):
    def test_run_daily_digest_clusters_similar_story_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            now = datetime.now(timezone.utc)
            first_pub_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
            second_pub_date = now.replace(minute=(now.minute + 1) % 60).strftime("%a, %d %b %Y %H:%M:%S GMT")
            feed_path.write_text(
                textwrap.dedent(
                    f"""\
                    <?xml version="1.0" encoding="UTF-8" ?>
                    <rss version="2.0">
                      <channel>
                        <title>Crypto Feed</title>
                        <item>
                          <title>OpenClaw developers targeted in GitHub phishing scam offering fake token airdrops</title>
                          <link>https://example.com/articles/openclaw-1</link>
                          <description>Attackers impersonated OpenClaw and pushed developers into wallet approvals.</description>
                          <pubDate>{first_pub_date}</pubDate>
                        </item>
                        <item>
                          <title>OpenClaw GitHub phishing scam uses fake token airdrops to gain wallet access</title>
                          <link>https://example.com/articles/openclaw-2</link>
                          <description>The same phishing campaign used cloned repositories and fake giveaways to target wallets.</description>
                          <pubDate>{second_pub_date}</pubDate>
                        </item>
                      </channel>
                    </rss>
                    """
                ),
                encoding="utf-8",
            )
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "output_language": "en",
                      "writing_guidelines": ["Keep it factual"],
                      "preferred_cta": "Verify before acting.",
                      "focus_topics": ["phishing", "wallet"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=root / "feeds.json",
                feed_urls=[feed_path.resolve().as_uri()],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=True,
            )

            output = run_daily_digest(config)

            self.assertEqual(len(output.run_result.articles), 1)
            self.assertEqual(output.run_result.summaries[0].cluster_size, 2)
            self.assertIn("across 2 reports", output.run_result.summaries[0].why_it_matters)

    def test_run_daily_digest_collects_filters_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(build_rss_fixture(), encoding="utf-8")
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "focus_topics": ["drainer", "phishing"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=root / "feeds.json",
                feed_urls=[feed_path.resolve().as_uri()],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=True,
            )

            output = run_daily_digest(config)

            self.assertEqual(len(output.run_result.articles), 1)
            self.assertIn("Wallet drainer exploits phishing page", output.digest_text)
            self.assertFalse(output.run_result.telegram_delivered)
            self.assertEqual(len(output.run_result.feed_results), 1)
            self.assertEqual(output.run_result.feed_results[0].status, "ok")
            self.assertEqual(len(output.telegram_messages), 3)
            self.assertIn("[1] News", output.telegram_messages[0])
            self.assertNotIn("ChainBounty Post", output.telegram_messages[1])

    def test_run_daily_digest_can_generate_same_recent_article_on_repeated_dry_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(build_rss_fixture(), encoding="utf-8")
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "output_language": "en",
                      "writing_guidelines": ["Keep it factual"],
                      "preferred_cta": "Verify before acting.",
                      "focus_topics": ["drainer", "phishing"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=root / "feeds.json",
                feed_urls=[feed_path.resolve().as_uri()],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=True,
            )

            first_output = run_daily_digest(config)
            second_output = run_daily_digest(config)

            self.assertEqual(len(first_output.run_result.posts), 1)
            self.assertEqual(len(second_output.run_result.posts), 1)

    def test_run_daily_digest_suppresses_recently_delivered_articles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(build_rss_fixture(), encoding="utf-8")
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "output_language": "en",
                      "writing_guidelines": ["Keep it factual"],
                      "preferred_cta": "Verify before acting.",
                      "focus_topics": ["drainer", "phishing"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=root / "feeds.json",
                feed_urls=[feed_path.resolve().as_uri()],
                telegram_bot_token="token",
                telegram_chat_id="chat",
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=False,
            )

            with patch("cryptonewsbot.application.pipeline.TelegramClient.send_messages", return_value=True):
                first_output = run_daily_digest(config)
                second_output = run_daily_digest(config)

            self.assertEqual(len(first_output.run_result.posts), 1)
            self.assertEqual(len(second_output.run_result.posts), 0)
            self.assertIn("No new crypto news matched", second_output.digest_text)

    def test_run_daily_digest_can_post_to_x_and_persist_tweet_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(build_rss_fixture(), encoding="utf-8")
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "output_language": "en",
                      "writing_guidelines": ["Keep it factual"],
                      "preferred_cta": "Verify before acting.",
                      "focus_topics": ["bitcoin", "etf"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=root / "feeds.json",
                feed_urls=[feed_path.resolve().as_uri()],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=True,
                enable_x_posting=True,
                x_dry_run=False,
                x_max_posts=1,
                twitter_api_key="key",
                twitter_api_secret="secret",
                twitter_access_token="token",
                twitter_access_token_secret="token-secret",
            )

            with patch(
                "cryptonewsbot.application.pipeline.XClient.post_generated_posts",
                side_effect=lambda posts, max_posts: {posts[0].article_id: "tweet-1"} if posts else {},
            ):
                output = run_daily_digest(config)

            self.assertTrue(output.run_result.x_delivered)
            self.assertEqual(output.run_result.posts[0].x_posted_tweet_id, "tweet-1")

            import sqlite3

            connection = sqlite3.connect(root / "app.db")
            try:
                run_row = connection.execute(
                    "SELECT delivered_to_x FROM runs ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
                x_row = connection.execute(
                    "SELECT tweet_id FROM delivered_x_posts ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
            finally:
                connection.close()

            self.assertEqual(run_row[0], 1)
            self.assertEqual(x_row[0], "tweet-1")

    def test_run_daily_digest_continues_from_last_writing_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(build_rss_fixture(), encoding="utf-8")
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "output_language": "en",
                      "writing_guidelines": ["Keep it factual"],
                      "preferred_cta": "Verify before acting.",
                      "focus_topics": ["bitcoin", "etf"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "writing_style_variants": [
                        {"name": "incident_briefing"},
                        {"name": "operator_alert"},
                        {"name": "casefile_note"}
                      ],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=root / "feeds.json",
                feed_urls=[feed_path.resolve().as_uri()],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=0,
                dry_run=True,
            )

            first_output = run_daily_digest(config)
            second_output = run_daily_digest(config)

            style_order = ["incident_briefing", "operator_alert", "casefile_note"]
            first_style = first_output.run_result.posts[0].writing_style_name
            expected_second_style = style_order[(style_order.index(first_style) + 1) % len(style_order)]

            self.assertEqual(second_output.run_result.posts[0].writing_style_name, expected_second_style)

    def test_config_can_load_default_feed_urls_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_config_path = root / "feeds.json"
            feed_config_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "sources": [
                        {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss", "enabled": true},
                        {"name": "Disabled", "url": "https://example.com/disabled.xml", "enabled": false}
                      ]
                    }
                    """
                ),
                encoding="utf-8",
            )
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
                      "focus_topics": ["bitcoin"],
                      "forbidden_phrases": [],
                      "signature": "Tracked",
                      "hashtags": ["#btc"],
                      "max_posts": 3,
                      "max_post_length": 280
                    }
                    """
                ),
                encoding="utf-8",
            )
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_path,
                feed_config_path=feed_config_path,
                feed_urls=[],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=True,
            )

            self.assertEqual(
                config.resolved_feed_urls,
                ["https://www.coindesk.com/arc/outboundfeeds/rss"],
            )


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from cryptonewsbot.application.pipeline import run_daily_digest
from cryptonewsbot.config import AppConfig


RSS_FIXTURE = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>Crypto Feed</title>
        <item>
          <title>Bitcoin ETF flows keep rising</title>
          <link>https://example.com/articles/bitcoin-etf?utm_source=test</link>
          <description>Institutional bitcoin ETF demand continued through the session.</description>
          <pubDate>Mon, 09 Mar 2026 01:00:00 GMT</pubDate>
        </item>
        <item>
          <title>Sports headline</title>
          <link>https://example.com/articles/sports</link>
          <description>This item should be filtered out by crypto focus topics.</description>
          <pubDate>Mon, 09 Mar 2026 02:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
)


class PipelineTests(unittest.TestCase):
    def test_run_daily_digest_collects_filters_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(RSS_FIXTURE, encoding="utf-8")
            style_path = root / "style.json"
            style_path.write_text(
                textwrap.dedent(
                    """\
                    {
                      "display_name": "Analyst",
                      "tone": "concise",
                      "audience": "operators",
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
                dry_run=True,
            )

            output = run_daily_digest(config)

            self.assertEqual(len(output.run_result.articles), 1)
            self.assertIn("Bitcoin ETF flows keep rising", output.digest_text)
            self.assertFalse(output.run_result.telegram_delivered)
            self.assertEqual(len(output.run_result.feed_results), 1)
            self.assertEqual(output.run_result.feed_results[0].status, "ok")
            self.assertEqual(len(output.telegram_messages), 3)
            self.assertIn("[1] News", output.telegram_messages[0])
            self.assertNotIn("ChainBounty Post", output.telegram_messages[1])

    def test_run_daily_digest_can_generate_same_recent_article_on_repeated_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_path = root / "feed.xml"
            feed_path.write_text(RSS_FIXTURE, encoding="utf-8")
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
                dry_run=True,
            )

            first_output = run_daily_digest(config)
            second_output = run_daily_digest(config)

            self.assertEqual(len(first_output.run_result.posts), 1)
            self.assertEqual(len(second_output.run_result.posts), 1)

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
                dry_run=True,
            )

            self.assertEqual(
                config.resolved_feed_urls,
                ["https://www.coindesk.com/arc/outboundfeeds/rss"],
            )


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path

from cryptonewsbot.config import AppConfig, load_dotenv


class ConfigTests(unittest.TestCase):
    def test_load_dotenv_sets_default_values_without_overwriting_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN=from-file\nCRYPTO_NEWSBOT_DRY_RUN=false\n",
                encoding="utf-8",
            )
            os.environ["CRYPTO_NEWSBOT_DRY_RUN"] = "true"
            try:
                load_dotenv(env_path)
                self.assertEqual(os.environ.get("CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN"), "from-file")
                self.assertEqual(os.environ.get("CRYPTO_NEWSBOT_DRY_RUN"), "true")
            finally:
                os.environ.pop("CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN", None)
                os.environ.pop("CRYPTO_NEWSBOT_DRY_RUN", None)

    def test_from_env_loads_optional_x_posting_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            root = Path(tmpdir)
            env_path = root / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "CRYPTO_NEWSBOT_ENABLE_X_POSTING=true",
                        "CRYPTO_NEWSBOT_X_DRY_RUN=false",
                        "CRYPTO_NEWSBOT_X_MAX_POSTS=2",
                        "TWITTER_API_KEY=key",
                        "TWITTER_API_SECRET=secret",
                        "TWITTER_ACCESS_TOKEN=token",
                        "TWITTER_ACCESS_TOKEN_SECRET=token-secret",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                os.chdir(root)
                config = AppConfig.from_env()
                self.assertTrue(config.enable_x_posting)
                self.assertFalse(config.x_dry_run)
                self.assertEqual(config.x_max_posts, 2)
                self.assertEqual(config.twitter_api_key, "key")
                self.assertEqual(config.twitter_access_token_secret, "token-secret")
            finally:
                os.chdir(original_cwd)
                for key in [
                    "CRYPTO_NEWSBOT_ENABLE_X_POSTING",
                    "CRYPTO_NEWSBOT_X_DRY_RUN",
                    "CRYPTO_NEWSBOT_X_MAX_POSTS",
                    "TWITTER_API_KEY",
                    "TWITTER_API_SECRET",
                    "TWITTER_ACCESS_TOKEN",
                    "TWITTER_ACCESS_TOKEN_SECRET",
                ]:
                    os.environ.pop(key, None)

    def test_load_feed_sources_from_file_preserves_metadata_and_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            feed_config_path = root / "feeds.json"
            style_profile_path = root / "style.json"
            feed_config_path.write_text(
                "\n".join(
                    [
                        "{",
                        '  "sources": [',
                        '    {"name": "FCA News", "url": "https://www.fca.org.uk/news/rss.xml", "enabled": true, "region": "EU", "category": "regulator", "tier": "core"},',
                        '    {"name": "Google News", "url": "https://news.google.com/rss/search?q=crypto", "enabled": true, "region": "EU", "category": "search-aggregated", "tier": "extended"}',
                        "  ]",
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            style_profile_path.write_text('{"display_name":"Analyst","tone":"concise","audience":"operators"}\n', encoding="utf-8")
            config = AppConfig(
                database_path=root / "app.db",
                style_profile_path=style_profile_path,
                feed_config_path=feed_config_path,
                feed_urls=[],
                telegram_bot_token=None,
                telegram_chat_id=None,
                max_articles=5,
                repeat_suppression_hours=24,
                dry_run=True,
            )

            sources = config.resolved_feed_sources

            self.assertEqual(len(sources), 2)
            self.assertEqual(sources[0].category, "regulator")
            self.assertEqual(sources[1].category, "search-aggregated")
            self.assertEqual(sources[0].tier, "core")
            self.assertEqual(sources[1].tier, "extended")
            self.assertEqual(config.feed_source_priorities["https://www.fca.org.uk/news/rss.xml"], 6)
            self.assertEqual(config.feed_source_priorities["https://news.google.com/rss/search?q=crypto"], 2)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from cryptonewsbot.application.post_generation import generate_posts, split_x_thread
from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import ArticleSummary, StyleProfile


class PostGenerationTests(unittest.TestCase):
    def test_generate_posts_respects_length_limit_and_profile_rules(self) -> None:
        summary = ArticleSummary(
            article_id="article-1",
            title="Bitcoin ETF flows rise again",
            source_name="Feed",
            canonical_url="https://example.com/article-1",
            key_point="Institutional demand increased for a second straight day.",
            why_it_matters="This affects ETF momentum and market structure.",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
        )
        profile = StyleProfile(
            display_name="Analyst",
            tone="concise",
            audience="operators",
            focus_topics=["bitcoin"],
            forbidden_phrases=["momentum"],
            signature="Tracked",
            hashtags=["#btc"],
            max_posts=3,
            max_post_length=140,
        )

        posts = generate_posts([summary], profile)

        self.assertEqual(len(posts), 1)
        self.assertGreater(len(posts[0].body), 140)
        self.assertGreaterEqual(len(posts[0].telegram_body), len(posts[0].body))
        self.assertNotIn("momentum", posts[0].body.lower())
        self.assertTrue(posts[0].body.startswith("📉") or posts[0].body.startswith("📊"))
        self.assertIn("Source:", posts[0].body)

    def test_generate_posts_uses_llm_when_configured(self) -> None:
        summary = ArticleSummary(
            article_id="article-1",
            title="Bitcoin ETF flows rise again",
            source_name="Feed",
            canonical_url="https://example.com/article-1",
            key_point="Institutional demand increased.",
            why_it_matters="This affects ETF flows.",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
        )
        profile = StyleProfile(
            display_name="Analyst",
            tone="concise",
            audience="operators",
            output_language="ko",
            writing_guidelines=["핵심만 쓴다"],
            preferred_cta="흐름을 체크하세요.",
            focus_topics=["bitcoin"],
            forbidden_phrases=[],
            signature="Tracked",
            hashtags=["#btc"],
            max_posts=3,
            max_post_length=140,
        )
        config = AppConfig(
            database_path=None,  # type: ignore[arg-type]
            style_profile_path=None,  # type: ignore[arg-type]
            feed_config_path=None,  # type: ignore[arg-type]
            feed_urls=[],
            telegram_bot_token=None,
            telegram_chat_id=None,
            max_articles=5,
            repeat_suppression_hours=24,
            dry_run=True,
            llm_provider="openai",
            llm_api_key="key",
            llm_model="model",
        )

        with patch(
            "cryptonewsbot.application.post_generation.try_rewrite_post",
            return_value={"headline": "LLM headline", "body": "LLM body", "telegram_body": "LLM telegram body"},
        ):
            posts = generate_posts([summary], profile, config)

        self.assertEqual(posts[0].headline, "LLM headline")
        self.assertEqual(posts[0].body, "LLM body")
        self.assertEqual(posts[0].telegram_body, "LLM telegram body")

    def test_generate_posts_uses_incident_specific_protection_measures(self) -> None:
        summary = ArticleSummary(
            article_id="article-1",
            title="Wallet drainer steals funds",
            source_name="Feed",
            canonical_url="https://example.com/article-1",
            key_point="A drainer emptied multiple wallets after malicious approvals.",
            why_it_matters="Drainer campaigns still exploit wallet approval flows.",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            template_type="incident",
            incident_type="drainer",
        )
        profile = StyleProfile(
            display_name="Analyst",
            tone="professional",
            audience="operators",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["hack"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=3,
            max_post_length=280,
        )

        posts = generate_posts([summary], profile)

        self.assertIn("Revoke risky approvals", posts[0].body)

    def test_split_x_thread_splits_long_body_into_thread_sized_chunks(self) -> None:
        body = "Paragraph one with enough text to exceed the limit.\n\n" * 8

        chunks = split_x_thread(body, limit=80)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 80 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()

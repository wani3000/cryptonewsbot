import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from cryptonewsbot.application.post_generation import (
    assign_writing_style_variants,
    build_system_prompt,
    build_user_prompt,
    generate_posts,
    resolve_next_writing_style_start_index,
    resolve_writing_style_variants,
    split_x_thread,
)
from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import ArticleSummary, StyleProfile, WritingStyleVariant


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
        self.assertNotIn("**", posts[0].body)
        self.assertNotIn("**", posts[0].telegram_body)

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
            writing_style_variants=[WritingStyleVariant(name="operator_alert")],
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
            return_value={
                "headline": "**LLM headline**",
                "body": "🚨 **LLM body**",
                "telegram_body": "🚨 **LLM telegram body**",
            },
        ):
            posts = generate_posts([summary], profile, config)

        self.assertEqual(posts[0].headline, "LLM headline")
        self.assertEqual(posts[0].body, "🚨 LLM body")
        self.assertEqual(posts[0].telegram_body, "🚨 LLM telegram body")

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
        self.assertTrue(posts[0].writing_style_name)

    def test_generate_posts_builds_richer_fallback_telegram_body_for_bridge_hack(self) -> None:
        summary = ArticleSummary(
            article_id="article-1",
            title="Bridge exploit drains cross-chain liquidity",
            source_name="Feed",
            canonical_url="https://example.com/bridge",
            key_point="A bridge exploit moved funds across multiple chains within minutes.",
            why_it_matters="Cross-chain incidents can spread before validators and exchanges react.",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            template_type="incident",
            incident_type="bridge_hack",
        )
        profile = StyleProfile(
            display_name="Analyst",
            tone="professional",
            audience="operators",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["bridge exploit"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=3,
            max_post_length=280,
        )

        posts = generate_posts([summary], profile)

        self.assertNotEqual(posts[0].telegram_body, posts[0].body)
        self.assertIn("bridge validator, relayer, and signer updates", posts[0].telegram_body)
        self.assertGreater(len(posts[0].telegram_body), len(posts[0].body))

    def test_generate_posts_does_not_truncate_telegram_body_with_ellipsis(self) -> None:
        summary = ArticleSummary(
            article_id="article-1",
            title="Wallet phishing campaign expands",
            source_name="Feed",
            canonical_url="https://example.com/phishing",
            key_point=(
                "Attackers reused a fake support flow, copied brand assets, and pushed victims into repeated wallet approval prompts "
                "across chat groups and cloned landing pages."
            ),
            why_it_matters=(
                "The pattern matters because it shows repeated trust hijacking, reusable domains, and wallet approval abuse that can spread "
                "quickly before exchanges or victims react."
            ),
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            template_type="incident",
            incident_type="phishing",
        )
        profile = StyleProfile(
            display_name="Analyst",
            tone="professional",
            audience="operators",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["phishing"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=3,
            max_post_length=280,
        )

        posts = generate_posts([summary], profile)

        self.assertIn("Operational watchpoints:", posts[0].telegram_body)
        self.assertNotIn("...", posts[0].telegram_body)

    def test_llm_prompts_include_subtype_specific_style_and_depth_guidance(self) -> None:
        summary = ArticleSummary(
            article_id="article-1",
            title="Wallet drainer steals funds",
            source_name="Feed",
            canonical_url="https://example.com/drainer",
            key_point="A drainer emptied wallets after malicious approvals.",
            why_it_matters="Attackers reused approval flows and destination clusters.",
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
        )
        style_variant = WritingStyleVariant(name="casefile_note", x_instruction="Use casefile tone.")

        system_prompt = build_system_prompt(summary, profile, style_variant)
        user_prompt = build_user_prompt(summary, profile, style_variant)

        self.assertIn("community-powered crypto crime investigation platform", system_prompt)
        self.assertIn("Write from ChainBounty's company perspective", system_prompt)
        self.assertIn("Assigned writing style: casefile_note", system_prompt)
        self.assertIn("malicious approvals and rapid wallet emptying", system_prompt)
        self.assertIn("what wallet operators should audit next", system_prompt)
        self.assertIn("Assigned writing style: casefile_note", user_prompt)
        self.assertIn("Cluster size: 1", user_prompt)
        self.assertIn("approval abuse, drain speed, infrastructure reuse", user_prompt)
        self.assertIn("Template guidance: Use an incident-report structure", user_prompt)

    def test_split_x_thread_splits_long_body_into_thread_sized_chunks(self) -> None:
        body = "Paragraph one with enough text to exceed the limit.\n\n" * 8

        chunks = split_x_thread(body, limit=80)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 80 for chunk in chunks))

    def test_assign_writing_style_variants_rotates_without_immediate_repetition(self) -> None:
        summaries = [
            ArticleSummary(
                article_id=f"article-{index}",
                title=f"Story {index}",
                source_name="Feed",
                canonical_url=f"https://example.com/{index}",
                key_point="Key point",
                why_it_matters="Why it matters",
                published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            )
            for index in range(5)
        ]
        variants = [
            WritingStyleVariant(name="incident_briefing"),
            WritingStyleVariant(name="operator_alert"),
            WritingStyleVariant(name="casefile_note"),
        ]

        assigned = assign_writing_style_variants(summaries, variants, rotation_seed=7)

        self.assertEqual([variant.name for variant in assigned], [
            "operator_alert",
            "casefile_note",
            "incident_briefing",
            "operator_alert",
            "casefile_note",
        ])

    def test_generate_posts_uses_multiple_writing_styles_across_batch(self) -> None:
        summaries = [
            ArticleSummary(
                article_id=f"article-{index}",
                title=f"Wallet incident {index}",
                source_name="Feed",
                canonical_url=f"https://example.com/{index}",
                key_point="Attackers moved funds through suspicious wallets.",
                why_it_matters="The pattern matters for tracing and defense.",
                published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
                template_type="incident",
                incident_type="general",
            )
            for index in range(4)
        ]
        profile = StyleProfile(
            display_name="Analyst",
            tone="professional",
            audience="operators",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            writing_style_variants=resolve_writing_style_variants(
                StyleProfile(display_name="x", tone="y", audience="z")
            ),
            max_posts=4,
            max_post_length=280,
        )

        posts = generate_posts(summaries, profile, writing_style_rotation_seed=1)

        self.assertGreater(len({post.writing_style_name for post in posts}), 1)
        self.assertEqual(posts[0].writing_style_name, "operator_alert")
        self.assertEqual(posts[1].writing_style_name, "casefile_note")
        self.assertIn("Operator alert:", posts[0].body)
        self.assertIn("Case note:", posts[1].body)

    def test_resolve_next_writing_style_start_index_advances_from_last_style(self) -> None:
        variants = [
            WritingStyleVariant(name="incident_briefing"),
            WritingStyleVariant(name="operator_alert"),
            WritingStyleVariant(name="casefile_note"),
        ]

        start_index = resolve_next_writing_style_start_index(variants, "operator_alert")

        self.assertEqual(start_index, 2)


if __name__ == "__main__":
    unittest.main()

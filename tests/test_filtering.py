import unittest
from datetime import datetime, timezone

from cryptonewsbot.application.filtering import select_relevant_articles
from cryptonewsbot.application.summarizer import classify_incident_type
from cryptonewsbot.domain.models import Article, StyleProfile


class FilteringTests(unittest.TestCase):
    def test_security_story_is_selected_even_without_market_keyword_match(self) -> None:
        article = Article(
            source_name="Feed",
            source_url="https://example.com/feed.xml",
            canonical_url="https://example.com/phishing",
            title="Wallet drainer steals funds in phishing campaign",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            summary="Attackers used a phishing approval flow to drain wallets.",
            content="The scam targeted users through fake support links.",
            fingerprint="fp-1",
        )
        profile = StyleProfile(
            display_name="ChainBounty",
            tone="professional",
            audience="crypto users",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Verify before acting.",
            focus_topics=["bitcoin", "ethereum"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=5,
            max_post_length=280,
        )

        selected = select_relevant_articles([article], profile, 5)

        self.assertEqual(len(selected), 1)

    def test_market_story_without_security_angle_is_filtered_out(self) -> None:
        article = Article(
            source_name="Feed",
            source_url="https://example.com/feed.xml",
            canonical_url="https://example.com/market",
            title="Bitcoin ETF inflows rise for second week",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            summary="Institutional demand increased again as ETF inflows improved.",
            content="The market reacted to macro positioning and stronger ETF demand.",
            fingerprint="fp-2",
        )
        profile = StyleProfile(
            display_name="ChainBounty",
            tone="professional",
            audience="crypto users",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["hack", "scam", "fraud", "investigation"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=5,
            max_post_length=280,
        )

        selected = select_relevant_articles([article], profile, 5)

        self.assertEqual(len(selected), 0)

    def test_classify_incident_type_detects_subtypes(self) -> None:
        cases = {
            "drainer": "Wallet drainer campaign drained users after malicious approvals.",
            "phishing": "Users lost funds after entering seed phrases on a fake support page.",
            "bridge_hack": "A cross-chain bridge exploit drained funds after validator compromise.",
            "sanction_seizure": "DOJ seized crypto tied to laundering and froze suspicious funds.",
            "pyramid_scam": "The investment scheme promised guaranteed returns in a Ponzi structure.",
        }

        for expected, text in cases.items():
            article = Article(
                source_name="Feed",
                source_url="https://example.com/feed.xml",
                canonical_url=f"https://example.com/{expected}",
                title=text,
                published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
                summary=text,
                content=text,
                fingerprint=expected,
            )
            self.assertEqual(classify_incident_type(article), expected)


if __name__ == "__main__":
    unittest.main()

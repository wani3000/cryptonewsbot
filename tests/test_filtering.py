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

    def test_multilingual_security_keywords_are_selected(self) -> None:
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

        cases = [
            (
                "kr-1",
                "거래소 지갑 해킹으로 가상자산 탈취 발생",
                "공격자가 피싱 수법으로 사용자 지갑을 탈취했다.",
            ),
            (
                "jp-1",
                "暗号資産ウォレットでフィッシング被害が拡大",
                "詐欺サイトを通じて資金流出が確認された。",
            ),
            (
                "cn-1",
                "加密货币诈骗团伙因洗钱调查被冻结资产",
                "监管部门正在调查相关钱包和资金流向。",
            ),
        ]

        for fingerprint, title, body in cases:
            article = Article(
                source_name="Feed",
                source_url="https://example.com/feed.xml",
                canonical_url=f"https://example.com/{fingerprint}",
                title=title,
                published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
                summary=body,
                content=body,
                fingerprint=fingerprint,
            )

            with self.subTest(fingerprint=fingerprint):
                selected = select_relevant_articles([article], profile, 5)
                self.assertEqual(len(selected), 1)

    def test_source_priority_prefers_direct_regulator_over_search_feed(self) -> None:
        profile = StyleProfile(
            display_name="ChainBounty",
            tone="professional",
            audience="crypto users",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["sanction", "investigation"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=5,
            max_post_length=280,
        )
        search_article = Article(
            source_name="Google News",
            source_url="https://news.google.com/rss/search?q=crypto",
            canonical_url="https://news.google.com/rss/articles/abc",
            title="Regulator investigates laundering routes tied to crypto wallets",
            published_at=datetime(2026, 3, 9, 11, tzinfo=timezone.utc),
            summary="The case led to asset freezes and a wider fraud investigation.",
            content="Officials are tracking wallets and laundering patterns.",
            fingerprint="search-1",
        )
        regulator_article = Article(
            source_name="FCA",
            source_url="https://www.fca.org.uk/news/rss.xml",
            canonical_url="https://www.fca.org.uk/news/crypto-case",
            title="Regulator investigates laundering routes tied to crypto wallets",
            published_at=datetime(2026, 3, 9, 10, tzinfo=timezone.utc),
            summary="The case led to asset freezes and a wider fraud investigation.",
            content="Officials are tracking wallets and laundering patterns.",
            fingerprint="regulator-1",
        )

        selected = select_relevant_articles(
            [search_article, regulator_article],
            profile,
            1,
            source_priorities={
                "https://news.google.com/rss/search?q=crypto": 1,
                "https://www.fca.org.uk/news/rss.xml": 4,
            },
        )

        self.assertEqual(selected[0].source_name, "FCA")

    def test_search_aggregated_promotional_story_is_filtered_out(self) -> None:
        article = Article(
            source_name="Google News",
            source_url="https://news.google.com/rss/search?q=crypto",
            canonical_url="https://news.google.com/rss/articles/promo",
            title="'Best Crypto to Buy Now for 2026': GitHub Phishing Scams Rise as Token Launch Nears",
            published_at=datetime(2026, 3, 9, 10, tzinfo=timezone.utc),
            summary="The article mixes a phishing mention with a launch-driven token promotion.",
            content="This piece promotes a token launch while loosely mentioning phishing risk.",
            fingerprint="promo-1",
        )
        profile = StyleProfile(
            display_name="ChainBounty",
            tone="professional",
            audience="crypto users",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["phishing", "hack", "fraud"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=5,
            max_post_length=280,
        )

        selected = select_relevant_articles([article], profile, 5)

        self.assertEqual(selected, [])

    def test_search_aggregated_story_requires_stronger_security_signal(self) -> None:
        article = Article(
            source_name="Google News",
            source_url="https://news.google.com/rss/search?q=crypto",
            canonical_url="https://news.google.com/rss/articles/weak",
            title="Crypto market outlook mentions security concerns",
            published_at=datetime(2026, 3, 9, 10, tzinfo=timezone.utc),
            summary="A broad market story mentions investigation risk without describing a concrete incident.",
            content="Analysts discussed market direction and briefly referenced fraud concerns.",
            fingerprint="weak-1",
        )
        profile = StyleProfile(
            display_name="ChainBounty",
            tone="professional",
            audience="crypto users",
            output_language="en",
            writing_guidelines=["Keep it factual"],
            preferred_cta="Join the discussion on ChainBounty Community: https://community.chainbounty.io/",
            focus_topics=["fraud", "investigation"],
            forbidden_phrases=[],
            signature="ChainBounty",
            hashtags=["#ChainBounty"],
            max_posts=5,
            max_post_length=280,
        )

        selected = select_relevant_articles([article], profile, 5)

        self.assertEqual(selected, [])

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

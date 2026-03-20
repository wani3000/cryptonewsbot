import unittest
from datetime import datetime, timezone

from cryptonewsbot.application.clustering import cluster_articles
from cryptonewsbot.domain.models import Article


class ClusteringTests(unittest.TestCase):
    def test_cluster_articles_groups_similar_incident_reports_and_prefers_direct_source(self) -> None:
        articles = [
            Article(
                source_name="Google News",
                source_url="https://news.google.com/rss/search?q=crypto",
                canonical_url="https://news.google.com/rss/articles/1",
                title="OpenClaw developers targeted in GitHub phishing scam offering fake token airdrops",
                published_at=datetime(2026, 3, 19, 12, tzinfo=timezone.utc),
                summary="Attackers impersonated OpenClaw and pushed developers into wallet approvals.",
                content="Attackers impersonated OpenClaw and pushed developers into wallet approvals.",
                fingerprint="google-1",
            ),
            Article(
                source_name="CoinDesk",
                source_url="https://www.coindesk.com/arc/outboundfeeds/rss",
                canonical_url="https://www.coindesk.com/openclaw-phishing",
                title="OpenClaw GitHub phishing scam uses fake token airdrops to gain wallet access",
                published_at=datetime(2026, 3, 19, 11, tzinfo=timezone.utc),
                summary="The campaign used cloned repositories and fake giveaways to target wallets.",
                content="The campaign used cloned repositories and fake giveaways to target wallets.",
                fingerprint="coindesk-1",
            ),
        ]

        clusters = cluster_articles(
            articles,
            source_priorities={
                "https://news.google.com/rss/search?q=crypto": 1,
                "https://www.coindesk.com/arc/outboundfeeds/rss": 2,
            },
        )

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].size, 2)
        self.assertEqual(clusters[0].representative.source_name, "CoinDesk")


if __name__ == "__main__":
    unittest.main()

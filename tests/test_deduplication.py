import unittest
from datetime import datetime, timezone

from cryptonewsbot.application.deduplication import deduplicate_articles
from cryptonewsbot.domain.models import Article


def make_article(title: str, fingerprint: str) -> Article:
    return Article(
        source_name="Feed",
        source_url="https://example.com/feed.xml",
        canonical_url=f"https://example.com/{fingerprint}",
        title=title,
        published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
        summary="Summary",
        content="Content",
        fingerprint=fingerprint,
    )


class DeduplicationTests(unittest.TestCase):
    def test_deduplicate_articles_removes_known_and_repeated_items(self) -> None:
        article_a = make_article("A", "fingerprint-a")
        article_b = make_article("B", "fingerprint-b")
        duplicate_b = make_article("B2", "fingerprint-b")

        unique_articles = deduplicate_articles(
            [article_a, article_b, duplicate_b],
            known_fingerprints={"fingerprint-a"},
        )

        self.assertEqual([article.fingerprint for article in unique_articles], ["fingerprint-b"])


if __name__ == "__main__":
    unittest.main()

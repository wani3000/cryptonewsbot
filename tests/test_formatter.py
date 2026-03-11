import unittest
from datetime import datetime, timezone

from cryptonewsbot.application.formatter import format_telegram_message_pairs
from cryptonewsbot.domain.models import ArticleSummary, FeedFetchResult, GeneratedPost


class FormatterTests(unittest.TestCase):
    def test_format_telegram_message_pairs_builds_news_and_post_sequence(self) -> None:
        summary = ArticleSummary(
            article_id="a1",
            title="Trader loses funds in exploit",
            source_name="Feed",
            canonical_url="https://example.com/a1",
            key_point="A wallet was drained after a phishing approval.",
            why_it_matters="For users, this matters because approval risk remains high.",
            published_at=datetime(2026, 3, 9, tzinfo=timezone.utc),
            template_type="incident",
        )
        post = GeneratedPost(
            article_id="a1",
            headline="Headline",
            body="🚨 Headline\n\nBody",
            telegram_body="🚨 Headline\n\nWhat happened:\nLonger telegram body",
        )
        feed_result = FeedFetchResult(url="https://example.com/feed", source_name="Feed", status="ok", item_count=1)

        messages = format_telegram_message_pairs([summary], [post], [feed_result])

        self.assertEqual(len(messages), 3)
        self.assertIn("[1] News", messages[0])
        self.assertIn("Title: 📊 Trader loses funds in exploit", messages[0])
        self.assertIn("Longer telegram body", messages[1])
        self.assertIn("Feeds checked", messages[2])


if __name__ == "__main__":
    unittest.main()

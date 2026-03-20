import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cryptonewsbot.domain.models import GeneratedPost
from cryptonewsbot.infrastructure.x import XClient


class FakeTweepyClient:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.calls = []
        self._next_id = 100

    def create_tweet(self, **payload):
        self.calls.append(payload)
        tweet_id = str(self._next_id)
        self._next_id += 1
        return SimpleNamespace(data={"id": tweet_id})


class XClientTests(unittest.TestCase):
    def test_post_generated_posts_splits_long_body_into_thread_and_returns_root_id(self) -> None:
        fake_client = FakeTweepyClient()
        fake_tweepy = SimpleNamespace(Client=lambda **kwargs: fake_client)
        client = XClient(
            api_key="key",
            api_secret="secret",
            access_token="token",
            access_token_secret="token-secret",
            bearer_token="bearer",
            enabled=True,
            dry_run=False,
        )
        post = GeneratedPost(
            article_id="article-1",
            headline="Headline",
            body=("Paragraph one with enough text to exceed the post limit.\n\n" * 10).strip(),
        )

        with patch("cryptonewsbot.infrastructure.x.import_module", return_value=fake_tweepy):
            result = client.post_generated_posts([post], max_posts=1)

        self.assertEqual(result, {"article-1": "100"})
        self.assertGreater(len(fake_client.calls), 1)
        self.assertNotIn("in_reply_to_tweet_id", fake_client.calls[0])
        self.assertEqual(fake_client.calls[1]["in_reply_to_tweet_id"], "100")

    def test_send_test_message_raises_when_x_not_configured(self) -> None:
        client = XClient(
            api_key=None,
            api_secret=None,
            access_token=None,
            access_token_secret=None,
            bearer_token=None,
            enabled=False,
            dry_run=False,
        )

        with self.assertRaises(ValueError):
            client.send_test_message("hello")

    def test_send_test_message_returns_false_when_post_fails(self) -> None:
        client = XClient(
            api_key="key",
            api_secret="secret",
            access_token="token",
            access_token_secret="token-secret",
            bearer_token="bearer",
            enabled=True,
            dry_run=False,
        )

        with patch.object(client, "_post_thread", side_effect=RuntimeError("boom")):
            self.assertFalse(client.send_test_message("hello"))


if __name__ == "__main__":
    unittest.main()

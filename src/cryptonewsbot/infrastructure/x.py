from __future__ import annotations

from importlib import import_module
from typing import Iterable

from cryptonewsbot.application.post_generation import split_x_thread
from cryptonewsbot.config import AppConfig
from cryptonewsbot.domain.models import GeneratedPost


class XClient:
    def __init__(
        self,
        api_key: str | None,
        api_secret: str | None,
        access_token: str | None,
        access_token_secret: str | None,
        bearer_token: str | None,
        enabled: bool,
        dry_run: bool,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._access_token_secret = access_token_secret
        self._bearer_token = bearer_token
        self._enabled = enabled
        self._dry_run = dry_run
        self._client = None

    @classmethod
    def from_config(
        cls,
        config: AppConfig,
        *,
        force_enable: bool = False,
        force_dry_run: bool | None = None,
    ) -> "XClient":
        return cls(
            api_key=config.twitter_api_key,
            api_secret=config.twitter_api_secret,
            access_token=config.twitter_access_token,
            access_token_secret=config.twitter_access_token_secret,
            bearer_token=config.twitter_bearer_token,
            enabled=config.enable_x_posting or force_enable,
            dry_run=config.x_dry_run if force_dry_run is None else force_dry_run,
        )

    @property
    def enabled(self) -> bool:
        return self._enabled and all(
            [
                self._api_key,
                self._api_secret,
                self._access_token,
                self._access_token_secret,
            ]
        )

    def send_test_message(self, message: str) -> bool:
        if not self.enabled:
            raise ValueError("X posting is not configured.")
        try:
            tweet_id = self._post_thread(split_x_thread(message))
        except Exception:
            return False
        return bool(tweet_id)

    def post_generated_posts(self, posts: Iterable[GeneratedPost], max_posts: int) -> dict[str, str]:
        if not self.enabled:
            return {}
        posted: dict[str, str] = {}
        for post in list(posts)[:max_posts]:
            try:
                tweet_id = self._post_thread(split_x_thread(post.body))
            except Exception:
                continue
            if tweet_id:
                posted[post.article_id] = tweet_id
        return posted

    def _post_thread(self, chunks: list[str]) -> str:
        if not chunks:
            return ""
        if self._dry_run:
            return ""

        reply_to_tweet_id: str | None = None
        root_tweet_id = ""
        for chunk in chunks:
            payload = {"text": chunk}
            if reply_to_tweet_id:
                payload["in_reply_to_tweet_id"] = reply_to_tweet_id
            response = self._get_client().create_tweet(**payload)
            tweet_id = str(response.data["id"])
            if not root_tweet_id:
                root_tweet_id = tweet_id
            reply_to_tweet_id = tweet_id
        return root_tweet_id

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            tweepy = import_module("tweepy")
        except ModuleNotFoundError as exc:
            raise ValueError("tweepy is required for X posting but is not installed.") from exc
        self._client = tweepy.Client(
            bearer_token=self._bearer_token,
            consumer_key=self._api_key,
            consumer_secret=self._api_secret,
            access_token=self._access_token,
            access_token_secret=self._access_token_secret,
            wait_on_rate_limit=True,
        )
        return self._client

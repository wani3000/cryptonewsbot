from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from cryptonewsbot.domain.models import StyleProfile


class ConfigError(ValueError):
    """Raised when the runtime configuration is invalid."""


SOURCE_CATEGORY_PRIORITIES = {
    "regulator": 4,
    "security-intel": 3,
    "media": 2,
    "custom": 2,
    "search-aggregated": 1,
}
SOURCE_TIER_PRIORITIES = {
    "core": 2,
    "extended": 1,
    "watch": 0,
}


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    enabled: bool = True
    region: str = "Global"
    category: str = "media"
    tier: str = "core"
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "FeedSource":
        return cls(
            name=str(payload.get("name", "Unnamed Feed")),
            url=str(payload.get("url", "")).strip(),
            enabled=bool(payload.get("enabled", True)),
            region=str(payload.get("region", "Global")),
            category=str(payload.get("category", "media")).strip().lower(),
            tier=str(payload.get("tier", "core")).strip().lower(),
            notes=str(payload.get("notes", "")),
        )

    @property
    def priority(self) -> int:
        return SOURCE_CATEGORY_PRIORITIES.get(self.category, 0) + SOURCE_TIER_PRIORITIES.get(self.tier, 0)


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    style_profile_path: Path
    feed_config_path: Path
    feed_urls: List[str]
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    max_articles: int
    repeat_suppression_hours: int
    dry_run: bool
    enable_x_posting: bool = False
    x_dry_run: bool = True
    x_max_posts: int = 1
    twitter_api_key: str | None = None
    twitter_api_secret: str | None = None
    twitter_access_token: str | None = None
    twitter_access_token_secret: str | None = None
    twitter_bearer_token: str | None = None
    llm_provider: str = "disabled"
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str = "https://api.openai.com/v1/chat/completions"

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv(Path(".env"))
        raw_feed_urls = os.getenv("CRYPTO_NEWSBOT_FEED_URLS", "")
        feed_urls = [item.strip() for item in raw_feed_urls.split(",") if item.strip()]
        max_articles = int(os.getenv("CRYPTO_NEWSBOT_MAX_ARTICLES", "10"))
        repeat_suppression_hours = int(os.getenv("CRYPTO_NEWSBOT_REPEAT_SUPPRESSION_HOURS", "24"))
        x_max_posts = int(os.getenv("CRYPTO_NEWSBOT_X_MAX_POSTS", "1"))
        return cls(
            database_path=Path(os.getenv("CRYPTO_NEWSBOT_DATABASE_PATH", "./cryptonewsbot.db")),
            style_profile_path=Path(
                os.getenv("CRYPTO_NEWSBOT_STYLE_PROFILE_PATH", "./config/style_profile.example.json")
            ),
            feed_config_path=Path(
                os.getenv("CRYPTO_NEWSBOT_FEED_CONFIG_PATH", "./config/feeds/crypto_sources.json")
            ),
            feed_urls=feed_urls,
            telegram_bot_token=_optional_env("CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_optional_env("CRYPTO_NEWSBOT_TELEGRAM_CHAT_ID"),
            max_articles=max_articles,
            repeat_suppression_hours=max(repeat_suppression_hours, 0),
            dry_run=os.getenv("CRYPTO_NEWSBOT_DRY_RUN", "true").lower() == "true",
            enable_x_posting=os.getenv("CRYPTO_NEWSBOT_ENABLE_X_POSTING", "false").lower() == "true",
            x_dry_run=os.getenv("CRYPTO_NEWSBOT_X_DRY_RUN", "true").lower() == "true",
            x_max_posts=max(x_max_posts, 1),
            twitter_api_key=_optional_env("TWITTER_API_KEY"),
            twitter_api_secret=_optional_env("TWITTER_API_SECRET"),
            twitter_access_token=_optional_env("TWITTER_ACCESS_TOKEN"),
            twitter_access_token_secret=_optional_env("TWITTER_ACCESS_TOKEN_SECRET"),
            twitter_bearer_token=_optional_env("TWITTER_BEARER_TOKEN"),
            llm_provider=os.getenv("CRYPTO_NEWSBOT_LLM_PROVIDER", "disabled").strip().lower(),
            llm_api_key=_optional_env("CRYPTO_NEWSBOT_LLM_API_KEY")
            or _optional_env("CRYPTO_NEWSBOT_GEMINI_API_KEY"),
            llm_model=_optional_env("CRYPTO_NEWSBOT_LLM_MODEL")
            or _optional_env("CRYPTO_NEWSBOT_GEMINI_MODEL"),
            llm_base_url=os.getenv(
                "CRYPTO_NEWSBOT_LLM_BASE_URL",
                "https://api.openai.com/v1/chat/completions",
            ).strip(),
        )

    def validate(self) -> None:
        if not self.resolved_feed_urls:
            raise ConfigError("CRYPTO_NEWSBOT_FEED_URLS must contain at least one RSS feed URL.")
        if self.max_articles < 1:
            raise ConfigError("CRYPTO_NEWSBOT_MAX_ARTICLES must be greater than 0.")
        if self.repeat_suppression_hours < 0:
            raise ConfigError("CRYPTO_NEWSBOT_REPEAT_SUPPRESSION_HOURS must be 0 or greater.")
        if self.x_max_posts < 1:
            raise ConfigError("CRYPTO_NEWSBOT_X_MAX_POSTS must be greater than 0.")
        if not self.style_profile_path.exists():
            raise ConfigError(f"Style profile file not found: {self.style_profile_path}")
        if self.enable_x_posting:
            missing_x_vars = [
                name
                for name, value in [
                    ("TWITTER_API_KEY", self.twitter_api_key),
                    ("TWITTER_API_SECRET", self.twitter_api_secret),
                    ("TWITTER_ACCESS_TOKEN", self.twitter_access_token),
                    ("TWITTER_ACCESS_TOKEN_SECRET", self.twitter_access_token_secret),
                ]
                if not value
            ]
            if missing_x_vars:
                raise ConfigError(
                    "X posting is enabled but missing required credentials: "
                    + ", ".join(missing_x_vars)
                )

    def load_style_profile(self) -> StyleProfile:
        payload = json.loads(self.style_profile_path.read_text(encoding="utf-8"))
        return StyleProfile.from_dict(payload)

    @property
    def resolved_feed_urls(self) -> List[str]:
        return [source.url for source in self.resolved_feed_sources]

    @property
    def resolved_feed_sources(self) -> List[FeedSource]:
        if self.feed_urls:
            return [
                FeedSource(
                    name=f"Custom Feed {index + 1}",
                    url=url,
                    enabled=True,
                    category="custom",
                )
                for index, url in enumerate(self.feed_urls)
            ]
        return self.load_feed_sources_from_file()

    @property
    def feed_source_priorities(self) -> Dict[str, int]:
        return {source.url: source.priority for source in self.resolved_feed_sources}

    def load_feed_urls_from_file(self) -> List[str]:
        return [source.url for source in self.load_feed_sources_from_file()]

    def load_feed_sources_from_file(self) -> List[FeedSource]:
        if not self.feed_config_path.exists():
            return []
        payload = json.loads(self.feed_config_path.read_text(encoding="utf-8"))
        sources: List[FeedSource] = []
        for raw_source in payload.get("sources", []):
            source = FeedSource.from_dict(raw_source)
            if not source.enabled or not source.url:
                continue
            sources.append(source)
        return sources


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)

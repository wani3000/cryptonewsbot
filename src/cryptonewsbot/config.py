from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from cryptonewsbot.domain.models import StyleProfile


class ConfigError(ValueError):
    """Raised when the runtime configuration is invalid."""


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    style_profile_path: Path
    feed_config_path: Path
    feed_urls: List[str]
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    max_articles: int
    dry_run: bool
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
            dry_run=os.getenv("CRYPTO_NEWSBOT_DRY_RUN", "true").lower() == "true",
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
        if not self.style_profile_path.exists():
            raise ConfigError(f"Style profile file not found: {self.style_profile_path}")

    def load_style_profile(self) -> StyleProfile:
        payload = json.loads(self.style_profile_path.read_text(encoding="utf-8"))
        return StyleProfile.from_dict(payload)

    @property
    def resolved_feed_urls(self) -> List[str]:
        if self.feed_urls:
            return self.feed_urls
        return self.load_feed_urls_from_file()

    def load_feed_urls_from_file(self) -> List[str]:
        if not self.feed_config_path.exists():
            return []
        payload = json.loads(self.feed_config_path.read_text(encoding="utf-8"))
        urls = []
        for source in payload.get("sources", []):
            if not source.get("enabled", True):
                continue
            url = str(source.get("url", "")).strip()
            if url:
                urls.append(url)
        return urls


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

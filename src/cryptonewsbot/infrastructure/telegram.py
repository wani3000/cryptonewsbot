from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.request import Request, urlopen


class TelegramClient:
    def __init__(self, bot_token: str | None, chat_id: str | None, dry_run: bool) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._dry_run = dry_run

    def send_message(self, text: str) -> bool:
        return self.send_messages([text])

    def send_messages(self, messages: List[str]) -> bool:
        if self._dry_run:
            return False
        if not self._bot_token or not self._chat_id:
            raise ValueError("Telegram bot token and chat id are required when dry run is disabled.")
        all_sent = True
        for message in messages:
            for chunk in split_message(message):
                payload = json.dumps({"chat_id": self._chat_id, "text": chunk}).encode("utf-8")
                request = Request(
                    f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=20) as response:
                    all_sent = all_sent and response.status == 200
        return all_sent

    def get_updates(self) -> Dict[str, Any]:
        if not self._bot_token:
            raise ValueError("Telegram bot token is required.")
        request = Request(
            f"https://api.telegram.org/bot{self._bot_token}/getUpdates",
            headers={"User-Agent": "cryptonewsbot/0.1"},
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))


def split_message(text: str, limit: int = 4096) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return chunks

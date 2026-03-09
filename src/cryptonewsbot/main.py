from __future__ import annotations

import sys

from cryptonewsbot.application.pipeline import run_daily_digest
from cryptonewsbot.config import AppConfig, ConfigError
from cryptonewsbot.infrastructure.telegram import TelegramClient
from cryptonewsbot.interfaces.cli import build_parser


def _print_telegram_updates(config: AppConfig) -> int:
    client = TelegramClient(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        dry_run=config.dry_run,
    )
    payload = client.get_updates()
    print(payload)
    return 0


def _send_telegram_test(config: AppConfig, message: str) -> int:
    client = TelegramClient(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        dry_run=False,
    )
    sent = client.send_message(message)
    print("sent" if sent else "not sent")
    return 0 if sent else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        config = AppConfig.from_env()
        if args.command == "telegram-get-updates":
            return _print_telegram_updates(config)
        if args.command == "telegram-send-test":
            return _send_telegram_test(config, args.message)
        output = run_daily_digest(config)
    except ConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"Runtime error: {error}", file=sys.stderr)
        return 3
    print(output.digest_text)
    print("")
    print(
        f"Saved run {output.run_result.run_id} with "
        f"{len(output.run_result.articles)} articles and {len(output.run_result.posts)} posts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

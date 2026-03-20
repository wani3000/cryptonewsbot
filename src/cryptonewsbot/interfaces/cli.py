from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="cryptonewsbot daily digest runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "telegram-get-updates", "telegram-send-test", "x-send-test"],
        help="Command to execute",
    )
    parser.add_argument(
        "--message",
        default="cryptonewsbot test message",
        help="Message used by telegram-send-test",
    )
    return parser

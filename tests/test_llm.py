import json
import unittest
from unittest.mock import patch

from cryptonewsbot.config import AppConfig
from cryptonewsbot.infrastructure.llm import LLMRewriter


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status = 200

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LLMTests(unittest.TestCase):
    def test_gemini_rewriter_parses_json_response(self) -> None:
        config = AppConfig(
            database_path=None,  # type: ignore[arg-type]
            style_profile_path=None,  # type: ignore[arg-type]
            feed_config_path=None,  # type: ignore[arg-type]
            feed_urls=[],
            telegram_bot_token=None,
            telegram_chat_id=None,
            max_articles=5,
            dry_run=True,
            llm_provider="gemini",
            llm_api_key="key",
            llm_model="gemini-2.0-flash",
            llm_base_url="https://generativelanguage.googleapis.com/v1beta/models",
        )
        rewriter = LLMRewriter(config)

        with patch(
            "cryptonewsbot.infrastructure.llm.urlopen",
            return_value=FakeResponse(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "{\"headline\":\"Gemini headline\",\"body\":\"Gemini body\",\"telegram_body\":\"Gemini telegram body\"}"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ),
        ):
            result = rewriter.rewrite("system", "user")

        self.assertEqual(result["headline"], "Gemini headline")
        self.assertEqual(result["body"], "Gemini body")
        self.assertEqual(result["telegram_body"], "Gemini telegram body")


if __name__ == "__main__":
    unittest.main()

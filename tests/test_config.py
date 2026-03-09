import os
import tempfile
import unittest
from pathlib import Path

from cryptonewsbot.config import load_dotenv


class ConfigTests(unittest.TestCase):
    def test_load_dotenv_sets_default_values_without_overwriting_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN=from-file\nCRYPTO_NEWSBOT_DRY_RUN=false\n",
                encoding="utf-8",
            )
            os.environ["CRYPTO_NEWSBOT_DRY_RUN"] = "true"
            try:
                load_dotenv(env_path)
                self.assertEqual(os.environ.get("CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN"), "from-file")
                self.assertEqual(os.environ.get("CRYPTO_NEWSBOT_DRY_RUN"), "true")
            finally:
                os.environ.pop("CRYPTO_NEWSBOT_TELEGRAM_BOT_TOKEN", None)
                os.environ.pop("CRYPTO_NEWSBOT_DRY_RUN", None)


if __name__ == "__main__":
    unittest.main()

import textwrap
import unittest
from datetime import datetime, timezone
from xml.etree import ElementTree

from cryptonewsbot.infrastructure.rss import RSSCollector


ATOM_FIXTURE = textwrap.dedent(
    """\
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Atom Crypto Feed</title>
      <entry>
        <title>Ethereum bridge hack exposes validator compromise</title>
        <link rel="alternate" href="https://example.com/eth-upgrade?utm_source=test" />
        <updated>2026-03-09T01:00:00Z</updated>
        <summary>&lt;p&gt;Investigators linked the exploit to a validator compromise.&lt;/p&gt;</summary>
      </entry>
      <entry>
        <title>Ethereum protocol upgrade</title>
        <link rel="alternate" href="https://example.com/eth-upgrade-2?utm_source=test" />
        <updated>2026-03-09T02:00:00Z</updated>
        <summary>&lt;p&gt;Upgrade improves throughput.&lt;/p&gt;</summary>
      </entry>
    </feed>
    """
)


class RSSTests(unittest.TestCase):
    def test_collect_atom_feed_supports_namespaces(self) -> None:
        root = ElementTree.fromstring(ATOM_FIXTURE)
        collector = RSSCollector()

        items, source_name = collector._collect_atom_feed(
            root,
            "https://example.com/feed.atom",
            datetime(2026, 3, 8, tzinfo=timezone.utc),
        )

        self.assertEqual(source_name, "Atom Crypto Feed")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Ethereum bridge hack exposes validator compromise")
        self.assertEqual(items[0]["url"], "https://example.com/eth-upgrade?utm_source=test")
        self.assertEqual(items[0]["summary"], "Investigators linked the exploit to a validator compromise.")

    def test_collect_atom_feed_filters_non_security_entries_at_collection_time(self) -> None:
        root = ElementTree.fromstring(ATOM_FIXTURE)
        collector = RSSCollector()

        items, _ = collector._collect_atom_feed(
            root,
            "https://example.com/feed.atom",
            datetime(2026, 3, 8, tzinfo=timezone.utc),
        )

        self.assertEqual(len(items), 1)
        self.assertNotIn("Ethereum protocol upgrade", [item["title"] for item in items])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Tuple
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from cryptonewsbot.domain.models import FeedFetchResult


CONTENT_TAGS = [
    "description",
    "{http://purl.org/rss/1.0/modules/content/}encoded",
    "{http://www.w3.org/2005/Atom}summary",
    "{http://www.w3.org/2005/Atom}content",
]
DATE_TAGS = [
    "pubDate",
    "{http://www.w3.org/2005/Atom}updated",
    "{http://www.w3.org/2005/Atom}published",
]
TITLE_TAGS = ["title", "{http://www.w3.org/2005/Atom}title"]
TAG_RE = re.compile(r"<[^>]+>")
COLLECTION_SECURITY_KEYWORDS = [
    "exploit",
    "hack",
    "scam",
    "phishing",
    "drain",
    "vulnerability",
    "breach",
    "compromise",
]
FALLBACK_DATE_FORMATS = [
    "%A, %B %d, %Y - %H:%M",
]


class RSSCollectionResult:
    def __init__(self, items: List[Dict[str, object]], feed_results: List[FeedFetchResult]) -> None:
        self.items = items
        self.feed_results = feed_results


class RSSCollector:
    def collect_since(self, feed_urls: List[str], since: datetime) -> RSSCollectionResult:
        items = []
        feed_results = []
        for feed_url in feed_urls:
            feed_items, feed_result = self._collect_feed(feed_url, since)
            items.extend(feed_items)
            feed_results.append(feed_result)
        return RSSCollectionResult(items=items, feed_results=feed_results)

    def _collect_feed(self, feed_url: str, since: datetime) -> Tuple[List[Dict[str, object]], FeedFetchResult]:
        request = Request(feed_url, headers={"User-Agent": "cryptonewsbot/0.1"})
        try:
            with urlopen(request, timeout=20) as response:
                xml_bytes = response.read()
            root = ElementTree.fromstring(xml_bytes)
            if _strip_namespace(root.tag) == "feed":
                items, source_name = self._collect_atom_feed(root, feed_url, since)
            else:
                items, source_name = self._collect_rss_feed(root, feed_url, since)
            return items, FeedFetchResult(
                url=feed_url,
                source_name=source_name,
                status="ok",
                item_count=len(items),
            )
        except Exception as exc:
            return [], FeedFetchResult(
                url=feed_url,
                source_name=feed_url,
                status="error",
                item_count=0,
                error_message=str(exc),
            )

    def _collect_rss_feed(
        self, root: ElementTree.Element, feed_url: str, since: datetime
    ) -> Tuple[List[Dict[str, object]], str]:
        channel = root.find("channel")
        if channel is None:
            return [], feed_url

        feed_title = _safe_text(channel.findtext("title")) or feed_url
        items = []
        for item_node in channel.findall("item"):
            published_at = parse_pub_date(_find_first_text(item_node, DATE_TAGS))
            if published_at < since:
                continue
            item = {
                "source_name": feed_title,
                "source_url": feed_url,
                "title": _find_first_text(item_node, TITLE_TAGS),
                "url": _find_rss_link(item_node),
                "summary": _find_first_text(item_node, CONTENT_TAGS),
                "content": _find_first_text(item_node, CONTENT_TAGS),
                "published_at": published_at,
            }
            if not _has_collection_security_keyword(item):
                continue
            items.append(item)
        return items, feed_title

    def _collect_atom_feed(
        self, root: ElementTree.Element, feed_url: str, since: datetime
    ) -> Tuple[List[Dict[str, object]], str]:
        feed_title = _find_first_text(root, TITLE_TAGS) or feed_url
        items = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            published_at = parse_pub_date(_find_first_text(entry, DATE_TAGS))
            if published_at < since:
                continue
            item = {
                "source_name": feed_title,
                "source_url": feed_url,
                "title": _find_first_text(entry, TITLE_TAGS),
                "url": _find_atom_link(entry),
                "summary": _find_first_text(entry, CONTENT_TAGS),
                "content": _find_first_text(entry, CONTENT_TAGS),
                "published_at": published_at,
            }
            if not _has_collection_security_keyword(item):
                continue
            items.append(item)
        return items, feed_title


def parse_pub_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        parsed = _parse_fallback_date(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_text(value: str | None) -> str:
    normalized = html.unescape(TAG_RE.sub(" ", value or ""))
    return " ".join(normalized.split()).strip()


def _find_first_text(node: ElementTree.Element, tags: List[str]) -> str:
    for tag in tags:
        value = node.findtext(tag)
        if value:
            return _safe_text(value)
    return ""


def _find_rss_link(node: ElementTree.Element) -> str:
    link_text = node.findtext("link")
    if link_text:
        return _safe_text(link_text)
    return ""


def _find_atom_link(node: ElementTree.Element) -> str:
    for link in node.findall("{http://www.w3.org/2005/Atom}link"):
        href = link.attrib.get("href")
        rel = link.attrib.get("rel", "alternate")
        if href and rel == "alternate":
            return _safe_text(href)
    return ""


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_fallback_date(value: str) -> datetime:
    for pattern in FALLBACK_DATE_FORMATS:
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _has_collection_security_keyword(item: Dict[str, object]) -> bool:
    haystack = " ".join(
        str(item.get(field, "")) for field in ("title", "summary", "content")
    ).lower()
    return any(keyword in haystack for keyword in COLLECTION_SECURITY_KEYWORDS)

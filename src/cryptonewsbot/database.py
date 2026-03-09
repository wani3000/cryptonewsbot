from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    fingerprint TEXT NOT NULL UNIQUE,
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    article_count INTEGER NOT NULL,
    post_count INTEGER NOT NULL,
    delivered_to_telegram INTEGER NOT NULL,
    feed_error_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS generated_posts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    headline TEXT NOT NULL,
    body TEXT NOT NULL,
    telegram_body TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(article_id) REFERENCES articles(id)
);

CREATE TABLE IF NOT EXISTS feed_fetch_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    source_name TEXT NOT NULL,
    status TEXT NOT NULL,
    item_count INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS delivered_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    delivered_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    try:
        connection.execute("ALTER TABLE generated_posts ADD COLUMN telegram_body TEXT NOT NULL DEFAULT ''")
        connection.commit()
    except sqlite3.OperationalError:
        pass
    return connection

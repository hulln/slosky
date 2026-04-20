from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CorpusStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS posts (
              uri TEXT PRIMARY KEY,
              author_did TEXT NOT NULL,
              created_at TEXT NOT NULL,
              text TEXT NOT NULL,
              langs_json TEXT NOT NULL,
              reply_flag INTEGER NOT NULL,
              quote_flag INTEGER NOT NULL,
              embed_kind TEXT,
              facet_count INTEGER NOT NULL,
              link_domains_json TEXT NOT NULL,
              source_dataset TEXT NOT NULL,
              first_seen_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              last_event_seq INTEGER,
              deleted INTEGER NOT NULL DEFAULT 0,
              deleted_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_did);
            CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
            CREATE INDEX IF NOT EXISTS idx_posts_deleted ON posts(deleted);

            CREATE TABLE IF NOT EXISTS repo_backfill (
              did TEXT PRIMARY KEY,
              posts_seen INTEGER NOT NULL DEFAULT 0,
              rows_retained INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS state (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.conn.execute("BEGIN")
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_state(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_state(self, key: str, value: str) -> None:
        self.conn.execute(
            """
            INSERT INTO state(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.conn.commit()

    def ensure_setting(self, key: str, expected_value: str) -> None:
        current = self.get_state(key)
        if current is None:
            self.set_state(key, expected_value)
            return
        if current != expected_value:
            raise ValueError(f"State mismatch for {key!r}: expected {expected_value!r}, found {current!r}")

    def _serialize_row(self, row: dict) -> tuple:
        return (
            row["uri"],
            row["author_did"],
            row["created_at"],
            row["text"],
            json.dumps(row["langs"], ensure_ascii=False),
            int(bool(row["reply_flag"])),
            int(bool(row["quote_flag"])),
            row["embed_kind"],
            int(row["facet_count"]),
            json.dumps(row["link_domains"], ensure_ascii=False),
            row["source_dataset"],
        )

    def upsert_post(
        self,
        row: dict,
        *,
        seen_at: str | None = None,
        last_event_seq: int | None = None,
    ) -> None:
        seen_at = seen_at or utcnow_iso()
        self.conn.execute(
            """
            INSERT INTO posts(
              uri, author_did, created_at, text, langs_json, reply_flag, quote_flag,
              embed_kind, facet_count, link_domains_json, source_dataset,
              first_seen_at, updated_at, last_event_seq, deleted, deleted_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            ON CONFLICT(uri) DO UPDATE SET
              author_did = excluded.author_did,
              created_at = excluded.created_at,
              text = excluded.text,
              langs_json = excluded.langs_json,
              reply_flag = excluded.reply_flag,
              quote_flag = excluded.quote_flag,
              embed_kind = excluded.embed_kind,
              facet_count = excluded.facet_count,
              link_domains_json = excluded.link_domains_json,
              source_dataset = excluded.source_dataset,
              updated_at = excluded.updated_at,
              last_event_seq = excluded.last_event_seq,
              deleted = 0,
              deleted_at = NULL
            """,
            self._serialize_row(row) + (seen_at, seen_at, last_event_seq),
        )

    def mark_deleted(
        self,
        uri: str,
        *,
        deleted_at: str | None = None,
        last_event_seq: int | None = None,
    ) -> int:
        deleted_at = deleted_at or utcnow_iso()
        cursor = self.conn.execute(
            """
            UPDATE posts
            SET deleted = 1,
                deleted_at = ?,
                updated_at = ?,
                last_event_seq = COALESCE(?, last_event_seq)
            WHERE uri = ?
            """,
            (deleted_at, deleted_at, last_event_seq, uri),
        )
        return cursor.rowcount

    def mark_author_deleted(
        self,
        author_did: str,
        *,
        deleted_at: str | None = None,
        last_event_seq: int | None = None,
    ) -> int:
        deleted_at = deleted_at or utcnow_iso()
        cursor = self.conn.execute(
            """
            UPDATE posts
            SET deleted = 1,
                deleted_at = ?,
                updated_at = ?,
                last_event_seq = COALESCE(?, last_event_seq)
            WHERE author_did = ? AND deleted = 0
            """,
            (deleted_at, deleted_at, last_event_seq, author_did),
        )
        return cursor.rowcount

    def replace_author_scope(
        self,
        author_did: str,
        rows: Iterable[dict],
        *,
        seen_at: str | None = None,
        last_event_seq: int | None = None,
    ) -> int:
        seen_at = seen_at or utcnow_iso()
        kept_uris: set[str] = set()
        retained = 0
        for row in rows:
            self.upsert_post(row, seen_at=seen_at, last_event_seq=last_event_seq)
            kept_uris.add(row["uri"])
            retained += 1

        if kept_uris:
            placeholders = ",".join("?" for _ in kept_uris)
            params = [seen_at, seen_at, last_event_seq, author_did, *sorted(kept_uris)]
            self.conn.execute(
                f"""
                UPDATE posts
                SET deleted = 1,
                    deleted_at = ?,
                    updated_at = ?,
                    last_event_seq = COALESCE(?, last_event_seq)
                WHERE author_did = ? AND deleted = 0 AND uri NOT IN ({placeholders})
                """,
                params,
            )
        else:
            self.mark_author_deleted(author_did, deleted_at=seen_at, last_event_seq=last_event_seq)

        self.conn.commit()
        return retained

    def record_repo_backfill(
        self,
        did: str,
        *,
        posts_seen: int,
        rows_retained: int,
        status: str,
        last_error: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO repo_backfill(did, posts_seen, rows_retained, status, updated_at, last_error)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(did) DO UPDATE SET
              posts_seen = excluded.posts_seen,
              rows_retained = excluded.rows_retained,
              status = excluded.status,
              updated_at = excluded.updated_at,
              last_error = excluded.last_error
            """,
            (did, posts_seen, rows_retained, status, utcnow_iso(), last_error),
        )
        self.conn.commit()

    def get_repo_backfill_status(self, did: str) -> tuple[str, str | None] | None:
        row = self.conn.execute(
            "SELECT status, last_error FROM repo_backfill WHERE did = ?",
            (did,),
        ).fetchone()
        if row is None:
            return None
        return str(row["status"]), row["last_error"]

    def iter_posts(
        self,
        *,
        include_deleted: bool = False,
        start_created_at: str | None = None,
        end_created_at: str | None = None,
        order_by: str | None = None,
    ) -> Iterator[dict]:
        conditions: list[str] = []
        params: list[str] = []
        if not include_deleted:
            conditions.append("deleted = 0")
        if start_created_at:
            conditions.append("created_at >= ?")
            params.append(start_created_at)
        if end_created_at:
            conditions.append("created_at <= ?")
            params.append(end_created_at)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        order_clause = ""
        if order_by == "created_at":
            order_clause = "ORDER BY created_at ASC, uri ASC"
        elif order_by == "rowid":
            order_clause = "ORDER BY rowid ASC"
        elif order_by is not None:
            raise ValueError(f"Unsupported order_by value: {order_by}")

        query = f"""
            SELECT
              uri, author_did, created_at, text, langs_json, reply_flag, quote_flag,
              embed_kind, facet_count, link_domains_json, source_dataset, deleted, deleted_at
            FROM posts
            {where_clause}
            {order_clause}
        """
        for row in self.conn.execute(query, params):
            yield {
                "uri": row["uri"],
                "author_did": row["author_did"],
                "created_at": row["created_at"],
                "text": row["text"],
                "langs": json.loads(row["langs_json"]),
                "reply_flag": bool(row["reply_flag"]),
                "quote_flag": bool(row["quote_flag"]),
                "embed_kind": row["embed_kind"],
                "facet_count": row["facet_count"],
                "link_domains": json.loads(row["link_domains_json"]),
                "source_dataset": row["source_dataset"],
                "deleted": bool(row["deleted"]),
                "deleted_at": row["deleted_at"],
            }

    def summary(self) -> dict[str, int | str | None]:
        row = self.conn.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE deleted = 0) AS active_posts,
              COUNT(*) FILTER (WHERE deleted = 1) AS deleted_posts,
              COUNT(DISTINCT author_did) FILTER (WHERE deleted = 0) AS active_authors,
              MIN(created_at) FILTER (WHERE deleted = 0) AS earliest_created_at,
              MAX(created_at) FILTER (WHERE deleted = 0) AS latest_created_at
            FROM posts
            """
        ).fetchone()
        return {
            "active_posts": row["active_posts"],
            "deleted_posts": row["deleted_posts"],
            "active_authors": row["active_authors"],
            "earliest_created_at": row["earliest_created_at"],
            "latest_created_at": row["latest_created_at"],
        }

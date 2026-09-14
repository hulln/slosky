from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.sqlite_store import CorpusStore


ROW_A = {
    "uri": "at://did:plc:test/app.bsky.feed.post/a",
    "author_did": "did:plc:test",
    "created_at": "2025-01-01T10:00:00.000Z",
    "text": "Pozdravljen svet",
    "langs": ["sl"],
    "reply_flag": False,
    "quote_flag": False,
    "embed_kind": None,
    "facet_count": 0,
    "link_domains": [],
    "source_dataset": "atproto:test",
}

ROW_B = {
    **ROW_A,
    "uri": "at://did:plc:test/app.bsky.feed.post/b",
    "created_at": "2025-01-02T10:00:00.000Z",
    "text": "Druga objava",
}


class CorpusStoreTests(unittest.TestCase):
    def test_replace_scope_marks_missing_rows_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = CorpusStore(Path(temp_dir) / "corpus.sqlite")
            retained = store.replace_author_scope("did:plc:test", [ROW_A, ROW_B], seen_at="2025-02-01T00:00:00Z")
            self.assertEqual(retained, 2)
            retained = store.replace_author_scope("did:plc:test", [ROW_A], seen_at="2025-02-02T00:00:00Z")
            self.assertEqual(retained, 1)
            active = list(store.iter_posts())
            self.assertEqual([row["uri"] for row in active], [ROW_A["uri"]])
            store.close()

    def test_mark_deleted_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = CorpusStore(Path(temp_dir) / "corpus.sqlite")
            store.upsert_post(ROW_A, seen_at="2025-02-01T00:00:00Z")
            store.mark_deleted(ROW_A["uri"], deleted_at="2025-02-03T00:00:00Z")
            summary = store.summary()
            self.assertEqual(summary["active_posts"], 0)
            self.assertEqual(summary["deleted_posts"], 1)
            store.close()

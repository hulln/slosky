from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.normalize import (
    alpha_char_count,
    contains_emoji,
    extract_link_domains,
    is_tagged_sl,
    normalize_export_row,
    strip_urls_and_mentions,
)


class NormalizeTests(unittest.TestCase):
    def test_extract_link_domains_from_facets_and_embed(self) -> None:
        record = {
            "facets": [
                {
                    "features": [
                        {
                            "$type": "app.bsky.richtext.facet#link",
                            "uri": "https://example.com/a",
                        }
                    ]
                }
            ],
            "embed": {
                "$type": "app.bsky.embed.recordWithMedia",
                "media": {
                    "$type": "app.bsky.embed.external",
                    "external": {"uri": "https://www.rtvslo.si/news"},
                },
            },
        }
        self.assertEqual(extract_link_domains(record), ["example.com", "rtvslo.si"])

    def test_normalize_export_row(self) -> None:
        row = {
            "uri": "at://did:plc:test/app.bsky.feed.post/abc",
            "author_did": "did:plc:test",
            "bluesky_ts": "2025-01-01 10:00:00.000000",
            "record_json": """
            {
              "$type": "app.bsky.feed.post",
              "createdAt": "2025-01-01T10:00:00.000Z",
              "langs": ["sl", "en"],
              "text": "Pozdravljen svet #test https://example.com",
              "reply": {"root": {"uri": "at://did:plc:other/app.bsky.feed.post/root"}},
              "facets": []
            }
            """,
        }
        normalized = normalize_export_row(row, source_dataset="clickhouse:test")
        self.assertEqual(normalized["langs"], ["sl", "en"])
        self.assertTrue(normalized["reply_flag"])
        self.assertFalse(normalized["quote_flag"])
        self.assertEqual(normalized["source_dataset"], "clickhouse:test")

    def test_strip_urls_and_mentions(self) -> None:
        text = "Pozdrav @nekdo glej https://example.com zdaj"
        cleaned = strip_urls_and_mentions(text)
        self.assertEqual(cleaned, "Pozdrav glej zdaj")
        self.assertGreaterEqual(alpha_char_count(cleaned), 10)

    def test_language_and_emoji_helpers(self) -> None:
        self.assertTrue(is_tagged_sl(["en", "sl"]))
        self.assertFalse(is_tagged_sl(["hr", "en"]))
        self.assertTrue(contains_emoji("Test 😀"))


if __name__ == "__main__":
    unittest.main()

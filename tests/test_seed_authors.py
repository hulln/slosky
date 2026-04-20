from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import write_jsonl
from slosky.seed_authors import collect_seed_author_counts, read_seed_author_csv, write_seed_author_csv


class SeedAuthorTests(unittest.TestCase):
    def test_collect_and_write_seed_authors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            jsonl_path = Path(temp_dir) / "seed.jsonl"
            output_csv = Path(temp_dir) / "seed_authors.csv"
            write_jsonl(
                jsonl_path,
                [
                    {"author_did": "did:plc:a"},
                    {"author_did": "did:plc:a"},
                    {"author_did": "did:plc:b"},
                ],
            )
            counts, sources = collect_seed_author_counts(jsonl_paths=[jsonl_path], store_paths=[])
            written = write_seed_author_csv(output_csv, counts=counts, sources=sources, min_posts=2)
            self.assertEqual(written, 1)
            rows = read_seed_author_csv(output_csv, min_posts=1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["author_did"], "did:plc:a")
            self.assertEqual(rows[0]["tagged_post_count"], 2)


if __name__ == "__main__":
    unittest.main()

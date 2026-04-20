#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert corpus JSONL to a readable CSV.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "created_at",
                "author_did",
                "langs",
                "text",
                "reply_flag",
                "quote_flag",
                "embed_kind",
                "facet_count",
                "link_domains",
                "uri",
            ],
        )
        writer.writeheader()
        for row in iter_jsonl(args.input):
            writer.writerow(
                {
                    "created_at": row["created_at"],
                    "author_did": row["author_did"],
                    "langs": "|".join(row["langs"]),
                    "text": flatten_text(row["text"]),
                    "reply_flag": row["reply_flag"],
                    "quote_flag": row["quote_flag"],
                    "embed_kind": row["embed_kind"] or "",
                    "facet_count": row["facet_count"],
                    "link_domains": "|".join(row["link_domains"]),
                    "uri": row["uri"],
                }
            )

    print(f"Wrote CSV to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

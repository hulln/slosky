#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.sqlite_store import CorpusStore


CSV_COLUMNS = [
    "uri",
    "author_did",
    "created_at",
    "text",
    "langs",
    "reply_flag",
    "quote_flag",
    "embed_kind",
    "facet_count",
    "link_domains",
    "source_dataset",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a snapshot of the ATProto corpus store.")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--include-deleted", action="store_true")
    parser.add_argument("--start-created-at")
    parser.add_argument("--end-created-at")
    args = parser.parse_args()

    store = CorpusStore(args.db)
    rows = list(
        store.iter_posts(
            include_deleted=args.include_deleted,
            start_created_at=args.start_created_at,
            end_created_at=args.end_created_at,
            order_by="rowid",
        )
    )

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({k: v for k, v in row.items() if k not in {"deleted", "deleted_at"}}, ensure_ascii=False) + "\n")

    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "uri": row["uri"],
                        "author_did": row["author_did"],
                        "created_at": row["created_at"],
                        "text": row["text"].replace("\n", " ").strip(),
                        "langs": json.dumps(row["langs"], ensure_ascii=False),
                        "reply_flag": int(bool(row["reply_flag"])),
                        "quote_flag": int(bool(row["quote_flag"])),
                        "embed_kind": row["embed_kind"] or "",
                        "facet_count": row["facet_count"],
                        "link_domains": json.dumps(row["link_domains"], ensure_ascii=False),
                        "source_dataset": row["source_dataset"],
                    }
                )

    metadata = store.summary()
    metadata["rows_exported"] = len(rows)
    meta_path = args.output_jsonl.with_suffix(args.output_jsonl.suffix + ".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

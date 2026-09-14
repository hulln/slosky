#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.sqlite_store import CorpusStore


STATE_KEYS = [
    "collector_kind",
    "collection",
    "filter_mode",
    "sync_api_base",
    "repo_api_base",
    "firehose_base",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge one or more ATProto SQLite stores into a target store.")
    parser.add_argument("--target-db", type=Path, required=True)
    parser.add_argument("--source-db", type=Path, action="append", required=True)
    args = parser.parse_args()

    target = CorpusStore(args.target_db)
    merged = {
        "sources": [],
        "upserts": 0,
        "deletes": 0,
    }

    for source_path in args.source_db:
        source = CorpusStore(source_path)
        for key in STATE_KEYS:
            value = source.get_state(key)
            if value is not None:
                current = target.get_state(key)
                if current is None:
                    target.set_state(key, value)
                elif current != value:
                    raise ValueError(f"State mismatch for {key!r}: {current!r} vs {value!r}")
        for row in source.iter_posts(include_deleted=True):
            if row["deleted"]:
                target.mark_deleted(row["uri"], deleted_at=row["deleted_at"])
                merged["deletes"] += 1
            else:
                payload = {key: value for key, value in row.items() if key not in {"deleted", "deleted_at"}}
                target.upsert_post(payload)
                merged["upserts"] += 1
        merged["sources"].append(str(source_path))
        source.close()

    target.conn.commit()
    merged["target_summary"] = target.summary()
    print(json.dumps(merged, indent=2, ensure_ascii=False))
    target.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

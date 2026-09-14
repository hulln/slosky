#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.sqlite_store import CorpusStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the current ATProto SQLite corpus store.")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--public-safe", action="store_true", help="Omit cursors and exact timestamps.")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    store = CorpusStore(args.db)
    summary = store.summary()
    if args.public_safe:
        summary = {
            "stage": "expanded seed-author collection store before language filtering",
            "collection": store.get_state("collection"),
            "filter_mode": store.get_state("filter_mode"),
            "active_posts": summary["active_posts"],
            "active_authors": summary["active_authors"],
            "date_range": {
                "earliest_month": str(summary["earliest_created_at"])[:7],
                "latest_month": str(summary["latest_created_at"])[:7],
                "precision": "month",
            },
            "collection_scripts": [
                "scripts/backfill_seed_authors.py",
                "scripts/merge_atproto_stores.py",
            ],
            "audit_script": "scripts/audit_atproto_store.py",
            "underlying_store_status": "restricted",
        }
    else:
        summary["filter_mode"] = store.get_state("filter_mode")
        summary["sync_api_base"] = store.get_state("sync_api_base")
        summary["repo_api_base"] = store.get_state("repo_api_base")
        summary["firehose_base"] = store.get_state("firehose_base")
        summary["backfill_cursor"] = store.get_state("atproto_backfill_repo_cursor")
        summary["live_cursor_seq"] = store.get_state("atproto_live_cursor_seq")
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

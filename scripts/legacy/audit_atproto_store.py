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
    args = parser.parse_args()

    store = CorpusStore(args.db)
    summary = store.summary()
    summary["filter_mode"] = store.get_state("filter_mode")
    summary["sync_api_base"] = store.get_state("sync_api_base")
    summary["repo_api_base"] = store.get_state("repo_api_base")
    summary["firehose_base"] = store.get_state("firehose_base")
    summary["backfill_cursor"] = store.get_state("atproto_backfill_repo_cursor")
    summary["live_cursor_seq"] = store.get_state("atproto_live_cursor_seq")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

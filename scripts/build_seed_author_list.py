#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.seed_authors import collect_seed_author_counts, write_seed_author_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a seed-author list from tagged-Slovene corpora and stores."
    )
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--jsonl-source", type=Path, action="append", default=[])
    parser.add_argument("--store-source", type=Path, action="append", default=[])
    parser.add_argument("--min-posts", type=int, default=1)
    args = parser.parse_args()

    counts, sources = collect_seed_author_counts(
        jsonl_paths=args.jsonl_source,
        store_paths=args.store_source,
    )
    kept = write_seed_author_csv(
        args.output_csv,
        counts=counts,
        sources=sources,
        min_posts=args.min_posts,
    )
    summary = {
        "authors_total": len(counts),
        "authors_written": kept,
        "jsonl_sources": [str(path) for path in args.jsonl_source],
        "store_sources": [str(path) for path in args.store_source],
        "min_posts": args.min_posts,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

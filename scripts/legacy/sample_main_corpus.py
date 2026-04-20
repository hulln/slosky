#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl, reservoir_sample


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an annotation sample from the corpus.")
    parser.add_argument("--input", type=Path, required=True, help="Corpus JSONL path")
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--size", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260310)
    args = parser.parse_args()

    sample = reservoir_sample(iter_jsonl(args.input), size=args.size, seed=args.seed)
    sample.sort(key=lambda row: row["created_at"])

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id",
                "uri",
                "author_did",
                "created_at",
                "text",
                "langs",
                "label",
                "notes",
            ],
        )
        writer.writeheader()
        for index, row in enumerate(sample, start=1):
            writer.writerow(
                {
                    "sample_id": f"precision-{index:03d}",
                    "uri": row["uri"],
                    "author_did": row["author_did"],
                    "created_at": row["created_at"],
                    "text": flatten_text(row["text"]),
                    "langs": "|".join(row["langs"]),
                    "label": "",
                    "notes": "",
                }
            )

    print(f"Wrote {len(sample)} rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

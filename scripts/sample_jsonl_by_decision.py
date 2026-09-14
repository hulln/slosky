#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from pathlib import Path


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def reservoir_sample(items, size: int, seed: int):
    random.seed(seed)
    sample = []
    for idx, item in enumerate(items):
        if idx < size:
            sample.append(item)
            continue
        j = random.randint(0, idx)
        if j < size:
            sample[j] = item
    return sample


def iter_matching_rows(path: Path, decision: str):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("decision") == decision:
                yield row


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample JSONL rows for one decision bucket.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260311)
    args = parser.parse_args()

    sample = reservoir_sample(iter_matching_rows(args.input, args.decision), args.size, args.seed)
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
                "decision",
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
                    "sample_id": f"{args.decision}-{index:03d}",
                    "uri": row["uri"],
                    "author_did": row["author_did"],
                    "created_at": row["created_at"],
                    "decision": row["decision"],
                    "text": flatten_text(row["text"]),
                    "langs": "|".join(row.get("langs", [])),
                    "label": "",
                    "notes": "",
                }
            )

    print(f"Wrote {len(sample)} rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

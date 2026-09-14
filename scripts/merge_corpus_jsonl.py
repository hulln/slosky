#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


CSV_FIELDNAMES = [
    "uri",
    "author_did",
    "created_at",
    "text",
    "langs",
    "decision",
    "signals",
    "langid_label",
    "langid_score",
    "langdetect_sl_prob",
]


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_csv_row(writer: csv.DictWriter, row: dict) -> None:
    writer.writerow(
        {
            "uri": row.get("uri", ""),
            "author_did": row.get("author_did", ""),
            "created_at": row.get("created_at", ""),
            "text": flatten_text(str(row.get("text", ""))),
            "langs": "|".join(row.get("langs", [])),
            "decision": row.get("decision", ""),
            "signals": row.get("signals", ""),
            "langid_label": row.get("langid_label", ""),
            "langid_score": row.get("langid_score"),
            "langdetect_sl_prob": row.get("langdetect_sl_prob"),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge JSONL corpora by URI, keeping first occurrence.")
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path)
    args = parser.parse_args()

    seen: set[str] = set()
    written = 0
    duplicates_skipped = 0
    earliest_created_at = None
    latest_created_at = None
    decision_counts: dict[str, int] = {}

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    csv_handle = None
    writer = None

    with args.output_jsonl.open("w", encoding="utf-8") as jsonl_handle:
        if args.output_csv:
            args.output_csv.parent.mkdir(parents=True, exist_ok=True)
            csv_handle = args.output_csv.open("w", encoding="utf-8", newline="")
            writer = csv.DictWriter(csv_handle, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()

        try:
            for path in args.input:
                for row in iter_jsonl(path):
                    uri = str(row.get("uri") or "")
                    if not uri:
                        continue
                    if uri in seen:
                        duplicates_skipped += 1
                        continue
                    seen.add(uri)
                    jsonl_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    if writer is not None:
                        write_csv_row(writer, row)
                    written += 1

                    created_at = row.get("created_at")
                    if created_at:
                        earliest_created_at = (
                            created_at
                            if earliest_created_at is None or created_at < earliest_created_at
                            else earliest_created_at
                        )
                        latest_created_at = (
                            created_at
                            if latest_created_at is None or created_at > latest_created_at
                            else latest_created_at
                        )
                    decision = str(row.get("decision") or "")
                    if decision:
                        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        finally:
            if csv_handle is not None:
                csv_handle.close()

    summary = {
        "inputs": [str(path) for path in args.input],
        "rows_written": written,
        "duplicates_skipped": duplicates_skipped,
        "earliest_created_at": earliest_created_at,
        "latest_created_at": latest_created_at,
        "decision_counts": decision_counts,
        "output_jsonl": str(args.output_jsonl),
    }
    args.output_jsonl.with_suffix(args.output_jsonl.suffix + ".meta.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

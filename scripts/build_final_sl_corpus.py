#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


DEFAULT_INCLUDED_DECISIONS = [
    "core_tag_supported",
    "review_model_consensus_only",
    "review_langid_only",
    "review_langdetect_only",
]


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(handle, row: dict) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_csv_writer(handle) -> csv.DictWriter:
    fieldnames = [
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
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    return writer


def write_csv(writer: csv.DictWriter, row: dict) -> None:
    writer.writerow(
        {
            "uri": row["uri"],
            "author_did": row["author_did"],
            "created_at": row["created_at"],
            "text": flatten_text(row["text"]),
            "langs": "|".join(row.get("langs", [])),
            "decision": row.get("decision", ""),
            "signals": row.get("signals", ""),
            "langid_label": row.get("langid_label", ""),
            "langid_score": row.get("langid_score"),
            "langdetect_sl_prob": row.get("langdetect_sl_prob"),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the final Slovene corpus from the strict core and selected review decisions."
    )
    parser.add_argument("--core-jsonl", type=Path, required=True)
    parser.add_argument("--review-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument(
        "--include-review-decision",
        action="append",
        default=[],
        help="Review decision type to include. Can be provided multiple times.",
    )
    args = parser.parse_args()

    included_review_decisions = args.include_review_decision or DEFAULT_INCLUDED_DECISIONS[1:]
    included_decisions = {"core_tag_supported", *included_review_decisions}

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    csv_handle = None
    writer = None

    written = 0
    decision_counts: dict[str, int] = {}

    with args.output_jsonl.open("w", encoding="utf-8") as jsonl_handle:
        if args.output_csv:
            args.output_csv.parent.mkdir(parents=True, exist_ok=True)
            csv_handle = args.output_csv.open("w", encoding="utf-8", newline="")
            writer = build_csv_writer(csv_handle)

        try:
            for row in iter_jsonl(args.core_jsonl):
                decision = row.get("decision", "")
                if decision not in included_decisions:
                    continue
                write_jsonl(jsonl_handle, row)
                if writer is not None:
                    write_csv(writer, row)
                written += 1
                decision_counts[decision] = decision_counts.get(decision, 0) + 1

            for row in iter_jsonl(args.review_jsonl):
                decision = row.get("decision", "")
                if decision not in included_decisions:
                    continue
                write_jsonl(jsonl_handle, row)
                if writer is not None:
                    write_csv(writer, row)
                written += 1
                decision_counts[decision] = decision_counts.get(decision, 0) + 1
        finally:
            if csv_handle is not None:
                csv_handle.close()

    summary = {
        "final_posts": written,
        "included_decisions": sorted(included_decisions),
        "decision_counts": decision_counts,
        "source_core_jsonl": str(args.core_jsonl),
        "source_review_jsonl": str(args.review_jsonl),
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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ACCEPTABLE_LABELS = {"Slovene-dominant", "Mixed-with-Slovene"}


def load_annotations(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_source_lookup(path: Path) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            uri = row.get("uri")
            if uri:
                lookup[uri] = row
    return lookup


def build_summary(
    annotations: list[dict[str, str]],
    source_lookup: dict[str, dict] | None = None,
) -> dict:
    label_counts = Counter()
    decision_counts = Counter()
    decision_label_counts = Counter()

    total = 0
    acceptable = 0
    undeterminable = 0
    matched = 0

    for row in annotations:
        total += 1
        label = (row.get("label") or "").strip()
        label_counts[label] += 1

        if label in ACCEPTABLE_LABELS:
            acceptable += 1
        if label == "Undeterminable/too-short":
            undeterminable += 1

        if source_lookup:
            source = source_lookup.get(row.get("uri", ""))
            if source:
                matched += 1
                decision = source.get("decision", "")
                signal_pattern = ",".join(source.get("signals", []))
                decision_counts[decision] += 1
                decision_label_counts[(decision, label)] += 1
                if not row.get("decision"):
                    row["decision"] = decision
                if not row.get("signal_pattern"):
                    row["signal_pattern"] = signal_pattern

    non_undeterminable = total - undeterminable
    summary = {
        "total_rows": total,
        "label_counts": dict(label_counts),
        "acceptable_rows": acceptable,
        "acceptable_rate_total": round(acceptable / total, 4) if total else None,
        "undeterminable_rows": undeterminable,
        "non_undeterminable_rows": non_undeterminable,
        "acceptable_rate_non_undeterminable": (
            round(acceptable / non_undeterminable, 4) if non_undeterminable else None
        ),
    }

    if source_lookup is not None:
        summary["matched_source_rows"] = matched
        summary["decision_counts"] = dict(decision_counts)
        summary["decision_label_counts"] = {
            f"{decision} || {label}": count
            for (decision, label), count in sorted(decision_label_counts.items())
        }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze an annotated validation sample.")
    parser.add_argument("--annotated-csv", required=True, help="Annotated CSV file.")
    parser.add_argument(
        "--source-jsonl",
        help="Optional source JSONL corpus to join by URI and recover decision buckets.",
    )
    parser.add_argument("--output-json", help="Optional JSON summary output path.")
    args = parser.parse_args()

    annotations = load_annotations(Path(args.annotated_csv))
    source_lookup = load_source_lookup(Path(args.source_jsonl)) if args.source_jsonl else None
    summary = build_summary(annotations, source_lookup)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

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
    parser.add_argument(
        "--annotated-csv", action="append", required=True,
        help="Annotated CSV file; repeat for a grouped dedicated-validation summary.",
    )
    parser.add_argument(
        "--source-jsonl",
        help="Optional source JSONL corpus to join by URI and recover decision buckets.",
    )
    parser.add_argument("--output-json", help="Optional JSON summary output path.")
    parser.add_argument(
        "--summary-kind", choices=["general", "dedicated", "false-negative"],
        default="general",
    )
    parser.add_argument("--sampling-summary-json", help="Safe manifest written by the sampling script.")
    parser.add_argument("--final-corpus-size", type=int)
    args = parser.parse_args()

    annotation_sets = [load_annotations(Path(path)) for path in args.annotated_csv]
    source_lookup = load_source_lookup(Path(args.source_jsonl)) if args.source_jsonl else None

    if args.summary_kind == "dedicated":
        grouped: dict[str, list[dict[str, str]]] = {}
        for rows in annotation_sets:
            for row in rows:
                category = (row.get("decision") or "").strip()
                if not category:
                    raise SystemExit("Dedicated summaries require a decision column in every row.")
                grouped.setdefault(category, []).append(row)
        summary = {
            "samples": {name: build_summary(rows) for name, rows in sorted(grouped.items())},
            "sampling_script": "scripts/sample_jsonl_by_decision.py",
            "analysis_script": "scripts/analyze_validation_samples.py",
            "sample_rows_status": "restricted",
        }
    else:
        annotations = [row for rows in annotation_sets for row in rows]
        summary = build_summary(annotations, source_lookup)
        if args.summary_kind == "false-negative":
            if not args.sampling_summary_json or not args.final_corpus_size:
                raise SystemExit(
                    "False-negative summaries require --sampling-summary-json and --final-corpus-size."
                )
            sampling = json.loads(Path(args.sampling_summary_json).read_text(encoding="utf-8"))
            sample_size = len(annotations)
            acceptable = summary["acceptable_rows"]
            rate = acceptable / sample_size
            missed = sampling["candidate_pool_size"] * rate
            summary = {
                "candidate_pool": sampling,
                "annotation": summary,
                "calculation": {
                    "sample_false_negative_rate": rate,
                    "estimated_missed_posts": missed,
                    "reported_rounded_missed_posts": round(missed, -2),
                    "final_corpus_size": args.final_corpus_size,
                    "estimated_percentage_of_final_corpus": round(
                        missed / args.final_corpus_size * 100, 4
                    ),
                    "formula": (
                        "candidate_pool_size * acceptable_rows / sample_size; "
                        "estimated_missed_posts / final_corpus_size * 100"
                    ),
                },
                "analysis_script": "scripts/analyze_validation_samples.py",
                "annotation_rows_status": "restricted",
            }

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

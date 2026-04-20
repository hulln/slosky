#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.clickhouse import ClickHouseClient, render_sql
from slosky.corpus import author_post_counts, iter_jsonl, reservoir_sample, write_jsonl
from slosky.normalize import (
    alpha_char_count,
    normalize_export_row,
    strip_urls_and_mentions,
)

try:  # pragma: no cover - optional dependency
    import fasttext
except ImportError:  # pragma: no cover - optional dependency
    fasttext = None


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def quote_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build recall-probe candidates.")
    parser.add_argument("--main-corpus", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--table", default="bluesky.bluesky")
    parser.add_argument("--start-ts", default="2024-12-23 14:00:00")
    parser.add_argument("--end-ts", default="2025-06-16 15:20:00")
    parser.add_argument("--sql", type=Path, default=Path("queries/export_author_posts.sql"))
    parser.add_argument("--endpoint", default="https://sql-clickhouse.clickhouse.com/")
    parser.add_argument("--user", default="demo")
    parser.add_argument("--password-env", default="CLICKHOUSE_PASSWORD")
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--min-author-posts", type=int, default=5)
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument(
        "--source-dataset",
        default="clickhouse:bluesky.bluesky",
    )
    args = parser.parse_args()

    if fasttext is None:
        raise SystemExit(
            "fasttext is not installed. Install it in your virtualenv before running this script."
        )
    if not args.model_path.exists():
        raise SystemExit(f"Missing fastText model file: {args.model_path}")

    author_counts = author_post_counts(iter_jsonl(args.main_corpus))
    selected_authors = sorted(
        author for author, count in author_counts.items() if count >= args.min_author_posts
    )
    if not selected_authors:
        raise SystemExit("No authors met the minimum-post threshold.")

    author_clause = ", ".join(quote_literal(author) for author in selected_authors)
    query = render_sql(
        args.sql,
        {
            "table": args.table,
            "start_ts": args.start_ts,
            "end_ts": args.end_ts,
            "author_clause": author_clause,
        },
    )

    model = fasttext.load_model(str(args.model_path))
    client = ClickHouseClient(
        endpoint=args.endpoint,
        user=args.user,
        password=os.environ.get(args.password_env, ""),
        timeout=900,
    )

    predicted: list[dict] = []
    for row in client.iter_json_each_row(query):
        normalized = normalize_export_row(row, source_dataset=args.source_dataset)
        cleaned = strip_urls_and_mentions(normalized["text"])
        if alpha_char_count(cleaned) < 20:
            continue

        labels, scores = model.predict(cleaned, k=1)
        label = labels[0].removeprefix("__label__")
        score = float(scores[0])
        if label == "sl" and score >= args.threshold:
            predicted.append(
                {
                    **normalized,
                    "lid_text": cleaned,
                    "predicted_label": label,
                    "predicted_score": round(score, 6),
                }
            )

    sample = reservoir_sample(predicted, size=args.size, seed=args.seed)
    sample.sort(key=lambda row: row["created_at"])

    if args.output_jsonl:
        write_jsonl(args.output_jsonl, predicted)

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
                "predicted_label",
                "predicted_score",
                "label",
                "notes",
            ],
        )
        writer.writeheader()
        for index, row in enumerate(sample, start=1):
            writer.writerow(
                {
                    "sample_id": f"recall-{index:03d}",
                    "uri": row["uri"],
                    "author_did": row["author_did"],
                    "created_at": row["created_at"],
                    "text": flatten_text(row["text"]),
                    "langs": "|".join(row["langs"]),
                    "predicted_label": row["predicted_label"],
                    "predicted_score": row["predicted_score"],
                    "label": "",
                    "notes": "",
                }
            )

    summary = {
        "authors_considered": len(selected_authors),
        "predicted_sl_candidates": len(predicted),
        "sample_size": len(sample),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

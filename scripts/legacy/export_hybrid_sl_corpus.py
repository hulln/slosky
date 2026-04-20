#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import write_jsonl
from slosky.normalize import alpha_char_count, is_tagged_sl, strip_urls_and_mentions
from slosky.sqlite_store import CorpusStore

try:  # pragma: no cover - optional dependency
    import fasttext
except ImportError:  # pragma: no cover - optional dependency
    fasttext = None

try:  # pragma: no cover - optional dependency
    import langid
except ImportError:  # pragma: no cover - optional dependency
    langid = None


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a high-recall hybrid Slovene corpus from an all-posts author-expansion store."
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="For fastText: minimum probability. Ignored for langid fallback.",
    )
    parser.add_argument("--min-alpha-chars", type=int, default=20)
    parser.add_argument("--include-tagged-short", action="store_true", default=True)
    args = parser.parse_args()

    backend = None
    model = None
    if fasttext is not None and args.model_path:
        if not args.model_path.exists():
            raise SystemExit(f"Missing fastText model file: {args.model_path}")
        model = fasttext.load_model(str(args.model_path))
        backend = "fasttext"
    elif langid is not None:
        backend = "langid"
    else:
        raise SystemExit("Neither fasttext nor langid is available.")
    store = CorpusStore(args.db)

    tagged_kept = 0
    lid_only_kept = 0
    scanned = 0
    kept_count = 0

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl_handle = args.output_jsonl.open("w", encoding="utf-8")
    csv_handle = None
    csv_writer = None
    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        csv_handle = args.output_csv.open("w", encoding="utf-8", newline="")
        csv_writer = csv.DictWriter(
            csv_handle,
            fieldnames=[
                "uri",
                "author_did",
                "created_at",
                "text",
                "langs",
                "kept_by",
                "predicted_score",
            ],
        )
        csv_writer.writeheader()

    try:
        for row in store.iter_posts(order_by="rowid"):
            scanned += 1
            keep = False
            kept_by = ""
            predicted_score = None

            if is_tagged_sl(row["langs"]):
                keep = True
                kept_by = "tagged"
                tagged_kept += 1
            else:
                cleaned = strip_urls_and_mentions(row["text"])
                if alpha_char_count(cleaned) >= args.min_alpha_chars:
                    if backend == "fasttext":
                        labels, scores = model.predict(cleaned, k=1)
                        label = labels[0].removeprefix("__label__")
                        score = float(scores[0])
                        keep = label == "sl" and score >= args.threshold
                    else:
                        label, score = langid.classify(cleaned)
                        score = float(score)
                        # langid scores are negative log probabilities, so the
                        # fastText threshold is not meaningful here. For the
                        # seed-author expansion store, top-label Slovene is the
                        # high-recall fallback decision rule.
                        keep = label == "sl"
                    if keep:
                        keep = True
                        kept_by = "lid"
                        predicted_score = round(score, 6)
                        lid_only_kept += 1

            if keep:
                kept_count += 1
                output_row = {
                    **row,
                    "kept_by": kept_by,
                    "predicted_score": predicted_score,
                }
                jsonl_handle.write(json.dumps(output_row, ensure_ascii=False) + "\n")
                if csv_writer is not None:
                    csv_writer.writerow(
                        {
                            "uri": row["uri"],
                            "author_did": row["author_did"],
                            "created_at": row["created_at"],
                            "text": flatten_text(row["text"]),
                            "langs": "|".join(row["langs"]),
                            "kept_by": kept_by,
                            "predicted_score": predicted_score or "",
                        }
                    )
    finally:
        jsonl_handle.close()
        if csv_handle is not None:
            csv_handle.close()

    summary = {
        "posts_scanned": scanned,
        "posts_kept": kept_count,
        "tagged_kept": tagged_kept,
        "lid_only_kept": lid_only_kept,
        "threshold": args.threshold,
        "min_alpha_chars": args.min_alpha_chars,
        "lid_backend": backend,
    }
    args.output_jsonl.with_suffix(args.output_jsonl.suffix + ".meta.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

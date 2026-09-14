#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.language_id import (
    DEFAULT_LINGUA_LANGUAGE_CODES,
    build_fasttext_model,
    build_lingua_detector,
    fasttext_predict_sl,
    langdetect_sl_probability,
    langid_predict_sl,
    lingua_predict_sl,
)
from slosky.normalize import alpha_char_count, strip_urls_and_mentions


POSITIVE_LABELS = {"Slovene-dominant", "Mixed-with-Slovene"}


def load_rows(core_csv: Path, review_csv: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with core_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row["gold"] = "POS"
            rows.append(row)
    with review_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            label = (row.get("label") or "").strip()
            if label == "Undeterminable/too-short":
                gold = "UNK"
            elif label in POSITIVE_LABELS:
                gold = "POS"
            else:
                gold = "NEG"
            row["gold"] = gold
            rows.append(row)
    return rows


def precision_recall(rows, key: str) -> dict[str, float | int]:
    positives = sum(1 for row in rows if row["gold"] == "POS")
    predicted = [row for row in rows if row[key]]
    true_positives = sum(1 for row in predicted if row["gold"] == "POS")
    false_positives = sum(1 for row in predicted if row["gold"] == "NEG")
    precision = true_positives / len(predicted) if predicted else 0.0
    recall = true_positives / positives if positives else 0.0
    return {
        "predicted_rows": len(predicted),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare four language-ID detectors on validated samples.")
    parser.add_argument("--core-sample", type=Path, required=True)
    parser.add_argument("--review-sample", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--fasttext-model", type=Path, default=Path("models/lid.176.bin"))
    parser.add_argument("--fasttext-threshold", type=float, default=0.50)
    parser.add_argument("--lingua-threshold", type=float, default=0.50)
    parser.add_argument("--langdetect-threshold", type=float, default=0.90)
    parser.add_argument("--min-alpha-chars", type=int, default=20)
    parser.add_argument(
        "--lingua-languages",
        default=",".join(DEFAULT_LINGUA_LANGUAGE_CODES),
    )
    args = parser.parse_args()

    fasttext_model = build_fasttext_model(args.fasttext_model)
    lingua_languages = tuple(
        code.strip() for code in args.lingua_languages.split(",") if code.strip()
    )
    lingua_detector = build_lingua_detector(lingua_languages)
    rows = load_rows(args.core_sample, args.review_sample)

    bucket_counts = Counter()

    for row in rows:
        cleaned = strip_urls_and_mentions(row["text"])
        alpha = alpha_char_count(cleaned)
        row["alpha_chars"] = alpha

        if alpha < args.min_alpha_chars:
            row["fasttext_signal"] = False
            row["lingua_signal"] = False
            row["langid_signal"] = False
            row["langdetect_signal"] = False
            bucket_counts["short_rows"] += 1
            continue

        fasttext_result = fasttext_predict_sl(fasttext_model, cleaned)
        row["fasttext_label"] = fasttext_result.label
        row["fasttext_prob"] = fasttext_result.prob
        row["fasttext_signal"] = (
            fasttext_result.label == "sl" and fasttext_result.prob >= args.fasttext_threshold
        )

        lingua_result = lingua_predict_sl(lingua_detector, cleaned)
        row["lingua_top_language"] = lingua_result.top_language
        row["lingua_sl_confidence"] = lingua_result.sl_confidence
        row["lingua_signal"] = (
            lingua_result.top_language == "sl"
            and lingua_result.sl_confidence >= args.lingua_threshold
        )

        langid_label, langid_score = langid_predict_sl(cleaned)
        row["langid_label"] = langid_label
        row["langid_score"] = langid_score
        row["langid_signal"] = langid_label == "sl"

        langdetect_prob = langdetect_sl_probability(cleaned)
        row["langdetect_sl_prob"] = langdetect_prob
        row["langdetect_signal"] = langdetect_prob >= args.langdetect_threshold

        signals = [
            name
            for name in ("fasttext_signal", "lingua_signal", "langid_signal", "langdetect_signal")
            if row[name]
        ]
        bucket_counts["+".join(signals) or "none"] += 1

    comparable_rows = [row for row in rows if row["gold"] != "UNK" and row["alpha_chars"] >= args.min_alpha_chars]

    summary = {
        "rows_total": len(rows),
        "rows_comparable": len(comparable_rows),
        "thresholds": {
            "fasttext_threshold": args.fasttext_threshold,
            "lingua_threshold": args.lingua_threshold,
            "langdetect_threshold": args.langdetect_threshold,
            "min_alpha_chars": args.min_alpha_chars,
            "lingua_languages": list(lingua_languages),
            "fasttext_model": str(args.fasttext_model),
        },
        "bucket_counts": dict(bucket_counts),
        "detectors": {
            "fasttext": precision_recall(comparable_rows, "fasttext_signal"),
            "lingua": precision_recall(comparable_rows, "lingua_signal"),
            "langid": precision_recall(comparable_rows, "langid_signal"),
            "langdetect": precision_recall(comparable_rows, "langdetect_signal"),
        },
        "pair_consensus": {
            "fasttext_plus_lingua": precision_recall(
                [dict(row, fasttext_plus_lingua=row["fasttext_signal"] and row["lingua_signal"]) for row in comparable_rows],
                "fasttext_plus_lingua",
            ),
            "langid_plus_langdetect": precision_recall(
                [dict(row, langid_plus_langdetect=row["langid_signal"] and row["langdetect_signal"]) for row in comparable_rows],
                "langid_plus_langdetect",
            ),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

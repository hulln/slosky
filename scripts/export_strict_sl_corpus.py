#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import langid
from langdetect import DetectorFactory, LangDetectException, detect_langs

from slosky.normalize import alpha_char_count, is_tagged_sl, strip_urls_and_mentions
from slosky.sqlite_store import CorpusStore


DetectorFactory.seed = 0


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def langdetect_sl_probability(text: str) -> float:
    try:
        for candidate in detect_langs(text):
            if candidate.lang == "sl":
                return float(candidate.prob)
        return 0.0
    except LangDetectException:
        return 0.0


def write_row_jsonl(handle, row: dict) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_row_csv(writer: csv.DictWriter, row: dict) -> None:
    writer.writerow(
        {
            "uri": row["uri"],
            "author_did": row["author_did"],
            "created_at": row["created_at"],
            "text": flatten_text(row["text"]),
            "langs": "|".join(row["langs"]),
            "decision": row["decision"],
            "signals": row["signals"],
            "langid_label": row["langid_label"],
            "langid_score": row["langid_score"],
            "langdetect_sl_prob": row["langdetect_sl_prob"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a strict Slovene corpus and a separate review bucket from the expanded author store."
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--core-jsonl", type=Path, required=True)
    parser.add_argument("--core-csv", type=Path)
    parser.add_argument("--review-jsonl", type=Path, required=True)
    parser.add_argument("--review-csv", type=Path)
    parser.add_argument("--min-alpha-chars", type=int, default=20)
    parser.add_argument("--langdetect-threshold", type=float, default=0.90)
    args = parser.parse_args()

    store = CorpusStore(args.db)
    args.core_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.review_jsonl.parent.mkdir(parents=True, exist_ok=True)

    core_handle = args.core_jsonl.open("w", encoding="utf-8")
    review_handle = args.review_jsonl.open("w", encoding="utf-8")
    core_csv_handle = None
    review_csv_handle = None
    core_writer = None
    review_writer = None

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

    if args.core_csv:
        args.core_csv.parent.mkdir(parents=True, exist_ok=True)
        core_csv_handle = args.core_csv.open("w", encoding="utf-8", newline="")
        core_writer = csv.DictWriter(core_csv_handle, fieldnames=fieldnames)
        core_writer.writeheader()

    if args.review_csv:
        args.review_csv.parent.mkdir(parents=True, exist_ok=True)
        review_csv_handle = args.review_csv.open("w", encoding="utf-8", newline="")
        review_writer = csv.DictWriter(review_csv_handle, fieldnames=fieldnames)
        review_writer.writeheader()

    scanned = 0
    core_kept = 0
    review_kept = 0
    decision_counts: dict[str, int] = {}
    signal_pattern_counts: dict[str, int] = {}

    try:
        for row in store.iter_posts(order_by="rowid"):
            scanned += 1
            cleaned = strip_urls_and_mentions(row["text"])
            alpha_count = alpha_char_count(cleaned)
            tag_signal = is_tagged_sl(row["langs"])
            langid_label = ""
            langid_score = None
            langid_signal = False
            langdetect_prob = 0.0
            langdetect_signal = False

            if alpha_count >= args.min_alpha_chars:
                langid_label, langid_score = langid.classify(cleaned)
                langid_score = round(float(langid_score), 6)
                langid_signal = langid_label == "sl"
                langdetect_prob = round(langdetect_sl_probability(cleaned), 6)
                langdetect_signal = langdetect_prob >= args.langdetect_threshold

            signals = {
                "tag": tag_signal,
                "langid": langid_signal,
                "langdetect": langdetect_signal,
            }
            signal_pattern = ",".join(
                name for name, value in signals.items() if value
            ) or "none"
            signal_pattern_counts[signal_pattern] = signal_pattern_counts.get(signal_pattern, 0) + 1

            decision = ""
            target = None

            if alpha_count < args.min_alpha_chars:
                if tag_signal:
                    decision = "review_short_tagged"
                    target = "review"
            else:
                if tag_signal and (langid_signal or langdetect_signal):
                    decision = "core_tag_supported"
                    target = "core"
                elif tag_signal:
                    decision = "review_tag_only"
                    target = "review"
                elif langid_signal and langdetect_signal:
                    decision = "review_model_consensus_only"
                    target = "review"
                elif langid_signal:
                    decision = "review_langid_only"
                    target = "review"
                elif langdetect_signal:
                    decision = "review_langdetect_only"
                    target = "review"

            if not target:
                continue

            output_row = {
                **row,
                "decision": decision,
                "signals": json.dumps(signals, ensure_ascii=False),
                "langid_label": langid_label,
                "langid_score": langid_score,
                "langdetect_sl_prob": langdetect_prob,
            }

            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            if target == "core":
                core_kept += 1
                write_row_jsonl(core_handle, output_row)
                if core_writer is not None:
                    write_row_csv(core_writer, output_row)
            else:
                review_kept += 1
                write_row_jsonl(review_handle, output_row)
                if review_writer is not None:
                    write_row_csv(review_writer, output_row)
    finally:
        core_handle.close()
        review_handle.close()
        if core_csv_handle is not None:
            core_csv_handle.close()
        if review_csv_handle is not None:
            review_csv_handle.close()
        store.close()

    summary = {
        "posts_scanned": scanned,
        "core_kept": core_kept,
        "review_kept": review_kept,
        "min_alpha_chars": args.min_alpha_chars,
        "langdetect_threshold": args.langdetect_threshold,
        "decision_counts": decision_counts,
        "signal_pattern_counts": signal_pattern_counts,
        "core_jsonl": str(args.core_jsonl),
        "review_jsonl": str(args.review_jsonl),
    }
    args.core_jsonl.with_suffix(args.core_jsonl.suffix + ".meta.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl
from slosky.language_id import (
    DEFAULT_LINGUA_LANGUAGE_CODES,
    build_fasttext_model,
    build_lingua_detector,
    fasttext_predict_sl_batch,
    langdetect_sl_probability,
    langid_predict_sl,
    lingua_predict_sl_batch,
)
from slosky.normalize import alpha_char_count, is_tagged_sl, strip_urls_and_mentions


DEFAULT_AUDIT_DECISIONS = ("review_tag_only", "review_short_tagged")


def flatten_text(value: str) -> str:
    return " ".join(value.split())


def iter_tagged_rows(path: Path, audit_decisions: set[str]):
    for row in iter_jsonl(path):
        decision = str(row.get("decision") or "")
        if decision not in audit_decisions:
            continue
        if not is_tagged_sl(row.get("langs") or []):
            continue
        yield row


def build_csv_writer(handle) -> csv.DictWriter:
    fieldnames = [
        "uri",
        "author_did",
        "created_at",
        "decision",
        "text",
        "langs",
        "alpha_chars",
        "fasttext_label",
        "fasttext_prob",
        "fasttext_signal",
        "lingua_top_language",
        "lingua_sl_confidence",
        "lingua_signal",
        "langid_label",
        "langid_score",
        "langid_signal",
        "langdetect_sl_prob",
        "langdetect_signal",
        "support_pattern",
        "candidate_reason",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    return writer


def write_csv_row(writer: csv.DictWriter, row: dict) -> None:
    writer.writerow(
        {
            "uri": row["uri"],
            "author_did": row["author_did"],
            "created_at": row["created_at"],
            "decision": row["decision"],
            "text": flatten_text(row["text"]),
            "langs": "|".join(row["langs"]),
            "alpha_chars": row["alpha_chars"],
            "fasttext_label": row["fasttext_label"],
            "fasttext_prob": row["fasttext_prob"],
            "fasttext_signal": int(bool(row["fasttext_signal"])),
            "lingua_top_language": row["lingua_top_language"],
            "lingua_sl_confidence": row["lingua_sl_confidence"],
            "lingua_signal": int(bool(row["lingua_signal"])),
            "langid_label": row["langid_label"],
            "langid_score": row["langid_score"],
            "langid_signal": int(bool(row["langid_signal"])),
            "langdetect_sl_prob": row["langdetect_sl_prob"],
            "langdetect_signal": int(bool(row["langdetect_signal"])),
            "support_pattern": row["support_pattern"],
            "candidate_reason": row["candidate_reason"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit excluded sl-tagged review rows with four language detectors."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--candidate-csv", type=Path, required=True)
    parser.add_argument("--suspicious-csv", type=Path, required=True)
    parser.add_argument("--fasttext-model", type=Path, default=Path("models/lid.176.bin"))
    parser.add_argument("--fasttext-threshold", type=float, default=0.50)
    parser.add_argument("--lingua-threshold", type=float, default=0.50)
    parser.add_argument("--langdetect-threshold", type=float, default=0.90)
    parser.add_argument("--min-alpha-chars", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument(
        "--audit-decision",
        action="append",
        default=[],
        help="Decision bucket to audit. Can be provided multiple times.",
    )
    parser.add_argument(
        "--lingua-languages",
        default=",".join(DEFAULT_LINGUA_LANGUAGE_CODES),
    )
    args = parser.parse_args()

    audit_decisions = set(args.audit_decision or DEFAULT_AUDIT_DECISIONS)
    lingua_languages = tuple(
        code.strip() for code in args.lingua_languages.split(",") if code.strip()
    )

    fasttext_model = build_fasttext_model(args.fasttext_model)
    lingua_detector = build_lingua_detector(lingua_languages)

    rows = list(iter_tagged_rows(args.input, audit_decisions))
    enriched_rows: list[dict] = []

    batch_size = max(args.batch_size, 1)
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cleaned_batch = [strip_urls_and_mentions(row["text"]) for row in batch]
        alpha_batch = [alpha_char_count(cleaned) for cleaned in cleaned_batch]

        fasttext_results = fasttext_predict_sl_batch(fasttext_model, cleaned_batch)
        lingua_results = lingua_predict_sl_batch(lingua_detector, cleaned_batch)

        for row, cleaned, alpha_chars, fasttext_result, lingua_result in zip(
            batch,
            cleaned_batch,
            alpha_batch,
            fasttext_results,
            lingua_results,
        ):
            langid_label = ""
            langid_score = 0.0
            langid_signal = False
            langdetect_sl_prob = 0.0
            langdetect_signal = False

            if alpha_chars >= args.min_alpha_chars:
                langid_label, langid_score = langid_predict_sl(cleaned)
                langid_signal = langid_label == "sl"
                langdetect_sl_prob = langdetect_sl_probability(cleaned)
                langdetect_signal = langdetect_sl_prob >= args.langdetect_threshold

            fasttext_signal = (
                fasttext_result.label == "sl" and fasttext_result.prob >= args.fasttext_threshold
            )
            lingua_signal = (
                lingua_result.top_language == "sl"
                and lingua_result.sl_confidence >= args.lingua_threshold
            )

            support_pattern = "+".join(
                name
                for name, active in (
                    ("fasttext", fasttext_signal),
                    ("lingua", lingua_signal),
                    ("langid", langid_signal),
                    ("langdetect", langdetect_signal),
                )
                if active
            ) or "none"

            candidate_reason = ""
            if row["decision"] == "review_tag_only" and (fasttext_signal or lingua_signal):
                candidate_reason = "extra_detector_support"
            elif row["decision"] == "review_short_tagged" and support_pattern != "none":
                candidate_reason = "short_but_detector_support"
            elif support_pattern == "none":
                candidate_reason = "no_detector_support"

            enriched_rows.append(
                {
                    **row,
                    "alpha_chars": alpha_chars,
                    "fasttext_label": fasttext_result.label,
                    "fasttext_prob": fasttext_result.prob,
                    "fasttext_signal": fasttext_signal,
                    "lingua_top_language": lingua_result.top_language,
                    "lingua_sl_confidence": lingua_result.sl_confidence,
                    "lingua_signal": lingua_signal,
                    "langid_label": langid_label,
                    "langid_score": langid_score,
                    "langid_signal": langid_signal,
                    "langdetect_sl_prob": langdetect_sl_prob,
                    "langdetect_signal": langdetect_signal,
                    "support_pattern": support_pattern,
                    "candidate_reason": candidate_reason,
                }
            )

    counts = Counter()
    decision_support_counts = Counter()

    args.candidate_csv.parent.mkdir(parents=True, exist_ok=True)
    args.suspicious_csv.parent.mkdir(parents=True, exist_ok=True)

    with (
        args.candidate_csv.open("w", encoding="utf-8", newline="") as candidate_handle,
        args.suspicious_csv.open("w", encoding="utf-8", newline="") as suspicious_handle,
    ):
        candidate_writer = build_csv_writer(candidate_handle)
        suspicious_writer = build_csv_writer(suspicious_handle)

        for row in enriched_rows:
            counts["rows_audited"] += 1
            counts[f"decision::{row['decision']}"] += 1
            counts[f"support::{row['support_pattern']}"] += 1
            decision_support_counts[f"{row['decision']} || {row['support_pattern']}"] += 1

            if row["alpha_chars"] < args.min_alpha_chars:
                counts["rows_below_min_alpha"] += 1
            if row["fasttext_signal"]:
                counts["fasttext_supported"] += 1
            if row["lingua_signal"]:
                counts["lingua_supported"] += 1
            if row["langid_signal"]:
                counts["langid_supported"] += 1
            if row["langdetect_signal"]:
                counts["langdetect_supported"] += 1

            if row["candidate_reason"] in {"extra_detector_support", "short_but_detector_support"}:
                counts["candidate_rows"] += 1
                counts[f"candidate::{row['candidate_reason']}"] += 1
                write_csv_row(candidate_writer, row)
            if row["candidate_reason"] == "no_detector_support":
                counts["suspicious_rows"] += 1
                write_csv_row(suspicious_writer, row)

    summary = {
        "input": str(args.input),
        "rows_audited": counts["rows_audited"],
        "audit_decisions": sorted(audit_decisions),
        "thresholds": {
            "fasttext_threshold": args.fasttext_threshold,
            "lingua_threshold": args.lingua_threshold,
            "langdetect_threshold": args.langdetect_threshold,
            "min_alpha_chars": args.min_alpha_chars,
            "lingua_languages": list(lingua_languages),
            "fasttext_model": str(args.fasttext_model),
        },
        "counts": dict(counts),
        "decision_support_counts": dict(decision_support_counts),
        "candidate_csv": str(args.candidate_csv),
        "suspicious_csv": str(args.suspicious_csv),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

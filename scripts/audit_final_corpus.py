#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.normalize import (
    alpha_char_count,
    contains_emoji,
    contains_hashtag,
    contains_mention,
    strip_urls_and_mentions,
)


ALLOWED_DECISIONS = {
    "core_tag_supported",
    "review_model_consensus_only",
    "review_langid_only",
    "review_langdetect_only",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the final Slovene corpus for structural cleanliness.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    counts = Counter(
        {
            "rows": 0,
            "rows_with_disallowed_decision": 0,
            "blank_text_rows": 0,
            "empty_after_project_cleaning": 0,
            "alpha_0_rows": 0,
            "alpha_lt_20_rows": 0,
            "rows_with_emoji": 0,
            "rows_with_hashtag": 0,
            "rows_with_mention": 0,
            "rows_with_link_domains": 0,
        }
    )

    with args.input.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = row.get("text", "")
            cleaned = strip_urls_and_mentions(text)
            alpha = alpha_char_count(cleaned)
            decision = row.get("decision", "")

            counts["rows"] += 1
            counts[f"decision::{decision}"] += 1

            if decision not in ALLOWED_DECISIONS:
                counts["rows_with_disallowed_decision"] += 1
            if text.strip() == "":
                counts["blank_text_rows"] += 1
            if cleaned == "":
                counts["empty_after_project_cleaning"] += 1
            if alpha == 0:
                counts["alpha_0_rows"] += 1
            if alpha < 20:
                counts["alpha_lt_20_rows"] += 1
            if contains_emoji(text):
                counts["rows_with_emoji"] += 1
            if contains_hashtag(text):
                counts["rows_with_hashtag"] += 1
            if contains_mention(text):
                counts["rows_with_mention"] += 1
            if row.get("link_domains"):
                counts["rows_with_link_domains"] += 1

    summary = {
        "input": str(args.input),
        "allowed_decisions": sorted(ALLOWED_DECISIONS),
        "counts": dict(counts),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

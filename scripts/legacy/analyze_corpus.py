#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl
from slosky.normalize import (
    contains_emoji,
    contains_hashtag,
    contains_mention,
    is_tagged_sl,
)


def pct(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return round(part / whole * 100, 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute corpus summary outputs.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    monthly_posts: Counter = Counter()
    monthly_authors: dict[str, set[str]] = defaultdict(set)
    lengths: list[int] = []
    total = 0
    replies = 0
    quotes = 0
    mentions = 0
    links = 0
    hashtags = 0
    emojis = 0
    single_sl = 0
    mixed = 0
    no_langs = 0
    mixed_examples: list[dict] = []

    for row in iter_jsonl(args.input):
        total += 1
        month = row["created_at"][:7]
        monthly_posts[month] += 1
        monthly_authors[month].add(row["author_did"])
        text = row["text"]
        lengths.append(len(text))

        replies += int(bool(row["reply_flag"]))
        quotes += int(bool(row["quote_flag"]))
        mentions += int(contains_mention(text))
        links += int(bool(row["link_domains"]))
        hashtags += int(contains_hashtag(text))
        emojis += int(contains_emoji(text))

        langs = row["langs"]
        if not langs:
            no_langs += 1
        elif len(langs) == 1 and is_tagged_sl(langs):
            single_sl += 1
        else:
            mixed += 1
            if len(mixed_examples) < 50:
                mixed_examples.append(
                    {
                        "uri": row["uri"],
                        "created_at": row["created_at"],
                        "langs": row["langs"],
                        "text": row["text"],
                    }
                )

    structural_profile = {
        "total_posts": total,
        "median_length_chars": statistics.median(lengths) if lengths else 0,
        "reply_posts": replies,
        "quote_posts": quotes,
        "original_non_reply_posts": total - replies,
        "percent_with_mentions": pct(mentions, total),
        "percent_with_links": pct(links, total),
        "percent_with_hashtags": pct(hashtags, total),
        "percent_with_emoji": pct(emojis, total),
    }

    multilinguality = {
        "single_language_sl_posts": single_sl,
        "mixed_language_or_variant_posts": mixed,
        "empty_langs_posts": no_langs,
        "percent_single_language_sl": pct(single_sl, total),
        "percent_mixed_language_or_variant": pct(mixed, total),
    }

    summary = {
        "structural_profile": structural_profile,
        "multilinguality_profile": multilinguality,
    }

    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    with (args.output_dir / "monthly_posts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["month", "post_count"])
        for month in sorted(monthly_posts):
            writer.writerow([month, monthly_posts[month]])

    with (args.output_dir / "monthly_authors.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["month", "unique_authors"])
        for month in sorted(monthly_authors):
            writer.writerow([month, len(monthly_authors[month])])

    with (args.output_dir / "mixed_language_candidates.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in mixed_examples:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

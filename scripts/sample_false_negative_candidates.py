#!/usr/bin/env python3
"""Sample posts from seed authors that are NOT in the final corpus and have no 'sl' tag.

These are false-negative candidates: posts written by known Slovenian-linked authors
that the pipeline never considered because the author did not tag them as Slovenian.
Annotating a random sample of these lets you estimate how many real Slovenian posts
were missed (recall / false-negative rate).

Usage:
    python scripts/sample_false_negative_candidates.py

Or with explicit paths / size:
    python scripts/sample_false_negative_candidates.py \
        --db outputs/intermediate/seed_author_posts.sqlite \
        --corpus outputs/final/final_sl_corpus.jsonl \
        --output-csv outputs/samples/false_negative_candidates.csv \
        --size 200
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.normalize import alpha_char_count, is_tagged_sl, strip_urls_and_mentions
from slosky.sqlite_store import CorpusStore

MIN_ALPHA_CHARS = 20


def flatten_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def reservoir_sample(iterable, size: int, seed: int) -> list:
    rng = random.Random(seed)
    sample: list = []
    for idx, item in enumerate(iterable):
        if idx < size:
            sample.append(item)
        else:
            j = rng.randint(0, idx)
            if j < size:
                sample[j] = item
    return sample


def load_corpus_uris(corpus_jsonl: Path) -> set[str]:
    print(f"Loading corpus URIs from {corpus_jsonl} ...")
    uris: set[str] = set()
    with corpus_jsonl.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                uris.add(json.loads(line)["uri"])
    print(f"  {len(uris):,} URIs loaded.")
    return uris


def iter_candidates(store: CorpusStore, corpus_uris: set[str], counts: dict[str, int]):
    """Yield posts that are not in the corpus and have no sl tag."""
    for post in store.iter_posts():
        counts["posts_scanned"] += 1

        if post["uri"] in corpus_uris:
            counts["already_in_corpus"] += 1
            continue

        if is_tagged_sl(post["langs"]):
            counts["sl_tagged_excluded"] += 1
            continue

        cleaned = strip_urls_and_mentions(post["text"])
        if alpha_char_count(cleaned) < MIN_ALPHA_CHARS:
            counts["too_short_excluded"] += 1
            continue

        counts["candidate_pool_size"] += 1
        yield post

    print(f"  Scanned:             {counts['posts_scanned']:>9,}")
    print(f"  Already in corpus:   {counts['already_in_corpus']:>9,}")
    print(f"  Has sl tag (skip):   {counts['sl_tagged_excluded']:>9,}  — these are handled by the main pipeline")
    print(f"  Too short (skip):    {counts['too_short_excluded']:>9,}  — below {MIN_ALPHA_CHARS} alpha chars")
    print(f"  Candidates yielded:  {counts['candidate_pool_size']:>9,}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("outputs/intermediate/seed_author_posts.sqlite"),
        help="Seed author SQLite database (default: outputs/intermediate/seed_author_posts.sqlite)",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("outputs/final/final_sl_corpus.jsonl"),
        help="Final corpus JSONL, used to exclude already-included posts",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("outputs/samples/false_negative_candidates.csv"),
        help="Where to write the annotation-ready CSV",
    )
    parser.add_argument("--size", type=int, default=200, help="Sample size (default: 200)")
    parser.add_argument("--seed", type=int, default=20260416, help="Random seed")
    parser.add_argument(
        "--summary-json", type=Path,
        help="Optional privacy-safe sampling manifest (contains no sampled rows).",
    )
    args = parser.parse_args()

    corpus_uris = load_corpus_uris(args.corpus)

    print(f"\nScanning {args.db} for false-negative candidates ...")
    counts = {
        "posts_scanned": 0,
        "already_in_corpus": 0,
        "sl_tagged_excluded": 0,
        "too_short_excluded": 0,
        "candidate_pool_size": 0,
    }
    store = CorpusStore(args.db)
    try:
        sample = reservoir_sample(iter_candidates(store, corpus_uris, counts), args.size, args.seed)
    finally:
        store.close()

    sample.sort(key=lambda r: r["created_at"])

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["sample_id", "uri", "author_did", "created_at", "text", "langs", "label", "notes"],
        )
        writer.writeheader()
        for idx, post in enumerate(sample, start=1):
            writer.writerow({
                "sample_id": f"fn-candidate-{idx:03d}",
                "uri": post["uri"],
                "author_did": post["author_did"],
                "created_at": post["created_at"],
                "text": flatten_text(post["text"]),
                "langs": "|".join(post["langs"]),
                "label": "",
                "notes": "",
            })

    print(f"\nWrote {len(sample)} rows -> {args.output_csv}")
    if args.summary_json:
        manifest = {
            **counts,
            "sample_size_requested": args.size,
            "sample_size_written": len(sample),
            "random_seed": args.seed,
            "minimum_alpha_characters": MIN_ALPHA_CHARS,
            "sampling_rule": (
                "active seed-author posts absent from the final corpus, without a Slovene "
                "language tag, and with at least 20 alphabetic characters after URL and "
                "@-mention stripping"
            ),
            "input_stage": "expanded seed-author store and final corpus URI set",
            "sampling_script": "scripts/sample_false_negative_candidates.py",
            "sample_rows_status": "restricted",
        }
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Sampling summary -> {args.summary_json}")
    print("Load this file in tools/annotate_samples.html to annotate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

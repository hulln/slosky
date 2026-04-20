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


def iter_candidates(store: CorpusStore, corpus_uris: set[str]):
    """Yield posts that are not in the corpus and have no sl tag."""
    n_total = 0
    n_in_corpus = 0
    n_sl_tagged = 0
    n_too_short = 0
    n_yielded = 0

    for post in store.iter_posts():
        n_total += 1

        if post["uri"] in corpus_uris:
            n_in_corpus += 1
            continue

        if is_tagged_sl(post["langs"]):
            n_sl_tagged += 1
            continue

        cleaned = strip_urls_and_mentions(post["text"])
        if alpha_char_count(cleaned) < MIN_ALPHA_CHARS:
            n_too_short += 1
            continue

        n_yielded += 1
        yield post

    print(f"  Scanned:             {n_total:>9,}")
    print(f"  Already in corpus:   {n_in_corpus:>9,}")
    print(f"  Has sl tag (skip):   {n_sl_tagged:>9,}  — these are handled by the main pipeline")
    print(f"  Too short (skip):    {n_too_short:>9,}  — below {MIN_ALPHA_CHARS} alpha chars")
    print(f"  Candidates yielded:  {n_yielded:>9,}")


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
    args = parser.parse_args()

    corpus_uris = load_corpus_uris(args.corpus)

    print(f"\nScanning {args.db} for false-negative candidates ...")
    store = CorpusStore(args.db)
    try:
        sample = reservoir_sample(iter_candidates(store, corpus_uris), args.size, args.seed)
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
    print("Load this file in tools/annotate_samples.html to annotate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

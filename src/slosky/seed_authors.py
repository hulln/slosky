from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from slosky.corpus import iter_jsonl
from slosky.sqlite_store import CorpusStore


def collect_seed_author_counts(
    *,
    jsonl_paths: Iterable[Path] = (),
    store_paths: Iterable[Path] = (),
) -> tuple[Counter[str], dict[str, set[str]]]:
    counts: Counter[str] = Counter()
    sources: dict[str, set[str]] = defaultdict(set)

    for path in jsonl_paths:
        source_label = f"jsonl:{path.name}"
        for row in iter_jsonl(path):
            author = row["author_did"]
            counts[author] += 1
            sources[author].add(source_label)

    for path in store_paths:
        source_label = f"store:{path.name}"
        store = CorpusStore(path)
        try:
            for row in store.iter_posts():
                author = row["author_did"]
                counts[author] += 1
                sources[author].add(source_label)
        finally:
            store.close()

    return counts, sources


def write_seed_author_csv(
    output_csv: Path,
    *,
    counts: Counter[str],
    sources: dict[str, set[str]],
    min_posts: int = 1,
) -> int:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["author_did", "tagged_post_count", "source_count", "sources"],
        )
        writer.writeheader()
        for author_did in sorted(counts):
            post_count = counts[author_did]
            if post_count < min_posts:
                continue
            author_sources = sorted(sources.get(author_did, set()))
            writer.writerow(
                {
                    "author_did": author_did,
                    "tagged_post_count": post_count,
                    "source_count": len(author_sources),
                    "sources": "|".join(author_sources),
                }
            )
            kept += 1
    return kept


def read_seed_author_csv(path: Path, *, min_posts: int = 1) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            post_count = int(row["tagged_post_count"])
            if post_count < min_posts:
                continue
            rows.append(
                {
                    "author_did": row["author_did"],
                    "tagged_post_count": post_count,
                    "source_count": int(row["source_count"]),
                    "sources": row["sources"],
                }
            )
    return rows

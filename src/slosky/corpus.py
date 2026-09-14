from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, TypeVar


T = TypeVar("T")


def iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def reservoir_sample(items: Iterable[T], size: int, seed: int) -> list[T]:
    rng = random.Random(seed)
    sample: list[T] = []
    for index, item in enumerate(items):
        if index < size:
            sample.append(item)
            continue
        replacement = rng.randint(0, index)
        if replacement < size:
            sample[replacement] = item
    return sample


def author_post_counts(rows: Iterable[dict]) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        counts[row["author_did"]] += 1
    return counts


def monthly_author_sets(rows: Iterable[dict]) -> dict[str, set[str]]:
    authors: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        month = row["created_at"][:7]
        authors[month].add(row["author_did"])
    return authors


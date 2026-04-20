#!/usr/bin/env python3
"""Produce empirical analysis outputs for the paper.

Main outputs:
  1. Growth timeline            — monthly post counts and active authors
  2. Author first-seen timeline — monthly first included post by author
  3. Community structure        — reply/quote/original breakdown, author concentration
  4. Author table               — per-author posting and infrastructure summary
  5. Topics                     — top hashtags and top linked domains
  6. Temporal + embed tables    — posting hours and embed-type counts
  7. Linguistic profile         — post length by type, code-switching characterisation

Usage:
    python3 scripts/analyze_for_paper.py
    python3 scripts/analyze_for_paper.py --input outputs/final/final_sl_corpus.jsonl \
        --output-dir outputs/analysis
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl

# Hashtag pattern: # followed by Slovenian + ASCII alphanumeric chars, min 2 chars
HASHTAG_RE = re.compile(r"#([a-zA-Z\u010d\u0161\u017e\u010c\u0160\u017d][a-zA-Z0-9_\u010d\u0161\u017e\u010c\u0160\u017d]{1,})")


def pct(part: int, whole: int, decimals: int = 1) -> float:
    return round(part / whole * 100, decimals) if whole else 0.0


def gini(counts: list[int]) -> float:
    """Gini coefficient of a distribution. 0 = perfectly equal, 1 = one author has everything."""
    if not counts:
        return 0.0
    n = len(counts)
    s = sorted(counts)
    total = sum(s)
    if total == 0:
        return 0.0
    cumsum = 0
    weighted = 0
    for i, v in enumerate(s, 1):
        cumsum += v
        weighted += cumsum
    return round(1 - 2 * weighted / (n * total) + 1 / n, 4)


def extract_hashtags(text: str) -> list[str]:
    return [m.lower() for m in HASHTAG_RE.findall(text)]


def load_pds_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iso_date(value: str) -> str:
    return value[:10]


def iso_hour_utc(value: str) -> int | None:
    if len(value) >= 13 and value[10] == "T":
        return int(value[11:13])
    return None


def normalize_host(value: str) -> str:
    host = urlparse(value).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def classify_handle(handle: str, pds_url: str) -> tuple[str, bool]:
    handle = handle.lower().strip()
    if not handle:
        return "unknown", False
    if handle.endswith(".bsky.social"):
        return "bsky_social", False

    pds_host = normalize_host(pds_url)
    if pds_host and handle.endswith("." + pds_host):
        return "pds_subdomain", False

    return "custom_domain", True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input", type=Path, default=Path("outputs/final/final_sl_corpus.jsonl")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--pds-cache", type=Path, default=Path("outputs/running/pds_cache.json"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pds_cache = load_pds_cache(args.pds_cache)

    # ── accumulators ──────────────────────────────────────────────────────────
    monthly_posts: Counter = Counter()
    monthly_active_authors: dict[str, set[str]] = defaultdict(set)
    author_months: dict[str, set[str]] = defaultdict(set)

    total = 0
    n_reply = 0
    n_reply_and_quote = 0
    n_quote = 0
    n_original = 0

    author_posts: Counter = Counter()
    author_replies: Counter = Counter()
    author_first_post: dict[str, str] = {}
    author_last_post: dict[str, str] = {}

    hashtag_counts: Counter = Counter()
    domain_counts: Counter = Counter()
    embed_kind_counts: Counter = Counter()
    posting_hours_utc: Counter = Counter()

    lengths_all: list[int] = []
    lengths_reply: list[int] = []
    lengths_original: list[int] = []
    lengths_quote: list[int] = []

    # code-switching signals
    langid_labels: Counter = Counter()
    langdetect_prob_buckets: Counter = Counter()   # 0-10, 10-20, … 90-100
    author_declared_mixed: Counter = Counter()     # non-sl langs that appear alongside sl

    print(f"Reading {args.input} …")

    for row in iter_jsonl(args.input):
        total += 1
        month = row["created_at"][:7]
        monthly_posts[month] += 1
        author_did = row["author_did"]
        monthly_active_authors[month].add(author_did)
        author_posts[author_did] += 1
        author_months[author_did].add(month)

        created_at = row["created_at"]
        if author_did not in author_first_post or created_at < author_first_post[author_did]:
            author_first_post[author_did] = created_at
        if author_did not in author_last_post or created_at > author_last_post[author_did]:
            author_last_post[author_did] = created_at

        reply = bool(row.get("reply_flag"))
        quote = bool(row.get("quote_flag"))
        text = row.get("text") or ""
        length = len(text)

        if reply and quote:
            n_reply_and_quote += 1
        if reply:
            n_reply += 1
            lengths_reply.append(length)
            author_replies[author_did] += 1
        elif quote:
            n_quote += 1
            lengths_quote.append(length)
        else:
            n_original += 1
            lengths_original.append(length)
        lengths_all.append(length)

        hour_utc = iso_hour_utc(created_at)
        if hour_utc is not None:
            posting_hours_utc[hour_utc] += 1

        # hashtags
        for tag in extract_hashtags(text):
            hashtag_counts[tag] += 1

        # link domains
        for domain in row.get("link_domains") or []:
            domain_counts[domain.lower()] += 1

        embed_kind_counts[(row.get("embed_kind") or "none")] += 1

        # code-switching: langid label
        label = row.get("langid_label") or ""
        langid_labels[label] += 1

        # code-switching: langdetect sl probability bucket
        prob = row.get("langdetect_sl_prob")
        if prob is not None:
            bucket = min(int(float(prob) * 10) * 10, 90)
            langdetect_prob_buckets[bucket] += 1

        # code-switching: author-declared mixed languages
        langs = row.get("langs") or []
        for lang in langs:
            lang = lang.lower()
            if not (lang == "sl" or lang.startswith("sl-")):
                author_declared_mixed[lang] += 1

    print(f"  {total:,} posts read.")

    # ── 1. growth timeline ────────────────────────────────────────────────────
    growth_path = args.output_dir / "paper_growth.csv"
    with growth_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "posts", "unique_authors"])
        for month in sorted(monthly_posts):
            w.writerow([month, monthly_posts[month], len(monthly_active_authors[month])])
    print(f"  → {growth_path}")

    # ── 2. author first-seen timeline ────────────────────────────────────────
    first_seen_by_month: Counter = Counter()
    for did, first_post in author_first_post.items():
        first_seen_by_month[first_post[:7]] += 1

    first_seen_path = args.output_dir / "paper_author_first_seen.csv"
    cumulative_authors = 0
    with first_seen_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["month", "new_authors", "cumulative_authors"])
        for month in sorted(first_seen_by_month):
            cumulative_authors += first_seen_by_month[month]
            w.writerow([month, first_seen_by_month[month], cumulative_authors])
    print(f"  → {first_seen_path}")

    # ── 3. community structure ────────────────────────────────────────────────
    post_counts = sorted(author_posts.values(), reverse=True)
    n_authors = len(post_counts)
    total_from_authors = sum(post_counts)

    # how many authors account for 50% / 80% of posts?
    def authors_for_share(share: float) -> int:
        target = total_from_authors * share
        running = 0
        for i, c in enumerate(post_counts, 1):
            running += c
            if running >= target:
                return i
        return n_authors

    top1_pct = max(1, n_authors // 100)
    top10_pct = max(1, n_authors // 10)
    top1_posts = sum(post_counts[:top1_pct])
    top10_posts = sum(post_counts[:top10_pct])

    community = {
        "total_posts": total,
        "total_authors": n_authors,
        "post_types": {
            "categorization": "exclusive hierarchy: reply > quote > original",
            "reply": n_reply,
            "reply_pct": pct(n_reply, total),
            "reply_and_quote": n_reply_and_quote,
            "quote": n_quote,
            "quote_pct": pct(n_quote, total),
            "quote_any": n_quote + n_reply_and_quote,
            "original": n_original,
            "original_pct": pct(n_original, total),
        },
        "author_concentration": {
            "gini_coefficient": gini(list(author_posts.values())),
            "top_1pct_authors": top1_pct,
            "top_1pct_posts_pct": pct(top1_posts, total),
            "top_10pct_authors": top10_pct,
            "top_10pct_posts_pct": pct(top10_posts, total),
            "authors_for_50pct_of_posts": authors_for_share(0.50),
            "authors_for_80pct_of_posts": authors_for_share(0.80),
            "median_posts_per_author": sorted(post_counts)[n_authors // 2],
            "max_posts_single_author": post_counts[0],
        },
    }

    community_path = args.output_dir / "paper_community.json"
    with community_path.open("w", encoding="utf-8") as fh:
        json.dump(community, fh, indent=2, ensure_ascii=False)
    print(f"  → {community_path}")

    # ── 4. author table ───────────────────────────────────────────────────────
    author_rows = []
    for did, posts in author_posts.items():
        pds_entry = pds_cache.get(did, {})
        handle = str(pds_entry.get("handle") or did)
        pds_url = str(pds_entry.get("pds_url") or "")
        handle_type, custom_domain = classify_handle(handle, pds_url)
        author_rows.append(
            {
                "handle": handle,
                "author_did": did,
                "posts": posts,
                "reply_rate": round(author_replies[did] / posts * 100, 1) if posts else 0.0,
                "months_active": len(author_months[did]),
                "first_post": iso_date(author_first_post[did]),
                "last_post": iso_date(author_last_post[did]),
                "handle_type": handle_type,
                "custom_domain": custom_domain,
                "pds": pds_url,
            }
        )

    author_rows.sort(key=lambda row: (-row["posts"], row["handle"], row["author_did"]))
    author_path = args.output_dir / "paper_authors.csv"
    with author_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "rank",
                "handle",
                "posts",
                "reply_rate",
                "months_active",
                "first_post",
                "last_post",
                "handle_type",
                "custom_domain",
                "pds",
            ]
        )
        for rank, row in enumerate(author_rows, 1):
            w.writerow(
                [
                    rank,
                    row["handle"],
                    row["posts"],
                    row["reply_rate"],
                    row["months_active"],
                    row["first_post"],
                    row["last_post"],
                    row["handle_type"],
                    row["custom_domain"],
                    row["pds"],
                ]
            )
    print(f"  → {author_path}")

    # ── 5. topics: hashtags + domains ─────────────────────────────────────────
    hashtag_path = args.output_dir / "paper_hashtags.csv"
    with hashtag_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "hashtag", "count", "pct_of_posts"])
        for rank, (tag, count) in enumerate(hashtag_counts.most_common(40), 1):
            w.writerow([rank, tag, count, pct(count, total, 2)])
    print(f"  → {hashtag_path}")

    domain_path = args.output_dir / "paper_domains.csv"
    with domain_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "domain", "count", "pct_of_posts"])
        for rank, (domain, count) in enumerate(domain_counts.most_common(40), 1):
            w.writerow([rank, domain, count, pct(count, total, 2)])
    print(f"  → {domain_path}")

    # ── 6. temporal + embed tables ────────────────────────────────────────────
    posting_hours_path = args.output_dir / "paper_posting_hours.csv"
    with posting_hours_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hour_utc", "posts"])
        for hour in range(24):
            w.writerow([hour, posting_hours_utc.get(hour, 0)])
    print(f"  → {posting_hours_path}")

    embed_types_path = args.output_dir / "paper_embed_types.csv"
    with embed_types_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["embed_kind", "count", "pct"])
        ordered_embed_kinds = sorted(
            embed_kind_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
        for embed_kind, count in ordered_embed_kinds:
            w.writerow([embed_kind, count, pct(count, total)])
    print(f"  → {embed_types_path}")

    # ── 7. linguistic profile ─────────────────────────────────────────────────
    def length_stats(lst: list[int]) -> dict:
        if not lst:
            return {}
        s = sorted(lst)
        n = len(s)
        return {
            "n": n,
            "median": s[n // 2],
            "mean": round(sum(s) / n, 1),
            "p25": s[n // 4],
            "p75": s[3 * n // 4],
            "p90": s[int(n * 0.9)],
        }

    # code-switching: posts where langid detected a non-sl language
    non_sl_langid = {k: v for k, v in langid_labels.items() if k != "sl"}
    total_non_sl_langid = sum(non_sl_langid.values())

    linguistic = {
        "post_length_chars": {
            "all": length_stats(lengths_all),
            "reply": length_stats(lengths_reply),
            "original": length_stats(lengths_original),
            "quote": length_stats(lengths_quote),
        },
        "code_switching": {
            "posts_where_langid_not_sl": total_non_sl_langid,
            "posts_where_langid_not_sl_pct": pct(total_non_sl_langid, total),
            "langdetect_sl_prob_distribution": {
                f"{b}-{b+10}%": langdetect_prob_buckets.get(b, 0)
                for b in range(0, 100, 10)
            },
            "author_declared_mixed_langs_top10": dict(author_declared_mixed.most_common(10)),
        },
    }

    linguistic_path = args.output_dir / "paper_linguistic.json"
    with linguistic_path.open("w", encoding="utf-8") as fh:
        json.dump(linguistic, fh, indent=2, ensure_ascii=False)
    print(f"  → {linguistic_path}")

    # also write langid non-sl breakdown as CSV
    langid_path = args.output_dir / "paper_codeswitching_langid.csv"
    with langid_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["langid_label", "count", "pct_of_corpus"])
        for lang, count in sorted(langid_labels.items(), key=lambda x: -x[1]):
            w.writerow([lang, count, pct(count, total, 2)])
    print(f"  → {langid_path}")

    # ── summary print ─────────────────────────────────────────────────────────
    print()
    print("═" * 60)
    print("PAPER ANALYSIS SUMMARY")
    print("═" * 60)
    print(f"Total posts:          {total:,}")
    print(f"Total authors:        {n_authors:,}")
    print(f"Date range:           {min(monthly_posts)} → {max(monthly_posts)}")
    print()
    print("Post types:")
    print(f"  Reply:    {n_reply:,} ({pct(n_reply, total)}%)")
    print(f"  Original: {n_original:,} ({pct(n_original, total)}%)")
    print(f"  Quote:    {n_quote:,} ({pct(n_quote, total)}%)")
    print(f"  Reply+Quote overlap: {n_reply_and_quote:,}")
    print()
    print("Post length (chars):")
    print(f"  Median (all):      {sorted(lengths_all)[total // 2]}")
    print(f"  Median (reply):    {sorted(lengths_reply)[len(lengths_reply) // 2]}")
    print(f"  Median (original): {sorted(lengths_original)[len(lengths_original) // 2]}")
    print()
    print("Author concentration:")
    print(f"  Gini:              {community['author_concentration']['gini_coefficient']}")
    print(f"  Top 1% authors → {community['author_concentration']['top_1pct_posts_pct']}% of posts")
    print(f"  Top 10% authors → {community['author_concentration']['top_10pct_posts_pct']}% of posts")
    print(f"  50% of posts from top {community['author_concentration']['authors_for_50pct_of_posts']} authors")
    print()
    print("Top 10 hashtags:")
    for rank, (tag, count) in enumerate(hashtag_counts.most_common(10), 1):
        print(f"  {rank:2}. #{tag:<25} {count:,}")
    print()
    print("Top 10 domains:")
    for rank, (domain, count) in enumerate(domain_counts.most_common(10), 1):
        print(f"  {rank:2}. {domain:<30} {count:,}")
    print()
    print("Code-switching (langid):")
    print(f"  Posts where langid ≠ sl: {total_non_sl_langid:,} ({pct(total_non_sl_langid, total)}%)")
    for lang, count in sorted(non_sl_langid.items(), key=lambda x: -x[1])[:8]:
        print(f"    {lang}: {count:,}")
    print()
    print("Author-declared mixed languages (alongside sl):")
    for lang, count in author_declared_mixed.most_common(8):
        print(f"  {lang}: {count:,} posts")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

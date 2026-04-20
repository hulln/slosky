#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.atproto_sync import DEFAULT_REPO_API_BASE, POST_COLLECTION, build_client, fetch_repo_snapshot
from slosky.did_resolver import DidResolver
from slosky.seed_authors import read_seed_author_csv
from slosky.sqlite_store import CorpusStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill full post histories for seed Slovene authors."
    )
    parser.add_argument("--seed-csv", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument(
        "--repo-api-base",
        default=DEFAULT_REPO_API_BASE,
        help="Fallback base URL if DID resolution fails or is disabled.",
    )
    parser.add_argument("--collection", default=POST_COLLECTION)
    parser.add_argument("--min-seed-posts", type=int, default=1)
    parser.add_argument("--author-limit", type=int)
    parser.add_argument("--record-limit", type=int, default=100)
    parser.add_argument("--max-records-per-author", type=int)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--source-dataset", default="atproto:seed-author.listRecords")
    parser.add_argument("--pds-cache", type=Path, default=Path("outputs/running/pds_cache.json"))
    parser.add_argument("--disable-pds-resolution", action="store_true")
    parser.add_argument("--retry-errors-only", action="store_true")
    parser.add_argument("--skip-ok", action="store_true", default=True)
    args = parser.parse_args()

    authors = read_seed_author_csv(args.seed_csv, min_posts=args.min_seed_posts)
    store = CorpusStore(args.db)
    store.ensure_setting("collector_kind", "seed-author-expansion")
    store.ensure_setting("collection", args.collection)
    store.ensure_setting("filter_mode", "all-posts")
    store.ensure_setting("repo_api_base", args.repo_api_base)
    store.ensure_setting("seed_csv", str(args.seed_csv))

    if args.retry_errors_only:
        author_map = {str(author["author_did"]): author for author in authors}
        error_dids = [
            row[0]
            for row in store.conn.execute(
                "SELECT did FROM repo_backfill WHERE status = 'error' ORDER BY updated_at ASC"
            )
        ]
        authors = [
            author_map.get(
                did,
                {
                    "author_did": did,
                    "tagged_post_count": 0,
                    "source_count": 0,
                    "sources": "retry_errors_only",
                },
            )
            for did in error_dids
        ]

    if args.author_limit:
        authors = authors[: args.author_limit]

    resolver = None if args.disable_pds_resolution else DidResolver(cache_path=args.pds_cache)
    clients: dict[str, object] = {}

    def client_for_did(did: str):
        base_url = args.repo_api_base
        if resolver is not None:
            base_url = resolver.resolve(did).pds_url
        if base_url not in clients:
            clients[base_url] = build_client(base_url)
        return clients[base_url], base_url

    processed = 0
    posts_seen_total = 0
    rows_retained_total = 0

    try:
        for author in authors:
            did = str(author["author_did"])
            current_status = store.get_repo_backfill_status(did)
            if args.retry_errors_only and (current_status is None or current_status[0] != "error"):
                continue
            if args.skip_ok and current_status is not None and current_status[0] == "ok":
                continue
            try:
                client, resolved_base = client_for_did(did)
                rows, posts_seen = fetch_repo_snapshot(
                    client,
                    repo_did=did,
                    filter_mode="all-posts",
                    source_dataset=f"{args.source_dataset}:{resolved_base}",
                    collection=args.collection,
                    record_limit=args.record_limit,
                    max_records=args.max_records_per_author,
                )
                retained = store.replace_author_scope(did, rows)
                store.record_repo_backfill(
                    did,
                    posts_seen=posts_seen,
                    rows_retained=retained,
                    status="ok",
                )
                processed += 1
                posts_seen_total += posts_seen
                rows_retained_total += retained
            except Exception as exc:
                store.record_repo_backfill(
                    did,
                    posts_seen=0,
                    rows_retained=0,
                    status="error",
                    last_error=str(exc),
                )
                processed += 1

            if processed % max(args.progress_every, 1) == 0:
                print(
                    json.dumps(
                        {
                            "authors_processed": processed,
                            "posts_seen_total": posts_seen_total,
                            "rows_retained_total": rows_retained_total,
                            "store_summary": store.summary(),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    finally:
        summary = {
            "authors_processed": processed,
            "posts_seen_total": posts_seen_total,
            "rows_retained_total": rows_retained_total,
            "store_summary": store.summary(),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        store.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

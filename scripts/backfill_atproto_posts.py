#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.atproto_sync import (
    DEFAULT_REPO_API_BASE,
    DEFAULT_SYNC_API_BASE,
    POST_COLLECTION,
    build_client,
    fetch_repo_snapshot,
    iter_repo_did_pages,
)
from slosky.did_resolver import DidResolver
from slosky.sqlite_store import CorpusStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill currently recoverable Bluesky posts into a local SQLite corpus store."
    )
    parser.add_argument("--db", type=Path, required=True, help="SQLite database path")
    parser.add_argument("--sync-api-base", default=DEFAULT_SYNC_API_BASE)
    parser.add_argument("--repo-api-base", default=DEFAULT_REPO_API_BASE)
    parser.add_argument("--collection", default=POST_COLLECTION)
    parser.add_argument("--filter-mode", choices=["tagged-sl", "all-posts"], default="tagged-sl")
    parser.add_argument("--repo-limit", type=int, help="Stop after this many repos")
    parser.add_argument("--page-limit", type=int, default=2000)
    parser.add_argument("--record-limit", type=int, default=100)
    parser.add_argument("--max-records-per-repo", type=int)
    parser.add_argument("--repo-did", help="Backfill a single repo DID instead of enumerating the network")
    parser.add_argument("--start-cursor", help="Override the saved listReposByCollection cursor")
    parser.add_argument("--cursor-key", default="atproto_backfill_repo_cursor")
    parser.add_argument("--source-dataset", default="atproto:repo.listRecords")
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--pds-cache", type=Path, default=Path("outputs/running/pds_cache.json"))
    parser.add_argument("--disable-pds-resolution", action="store_true")
    args = parser.parse_args()

    sync_client = build_client(args.sync_api_base)
    store = CorpusStore(args.db)
    store.ensure_setting("collector_kind", "atproto")
    store.ensure_setting("collection", args.collection)
    store.ensure_setting("filter_mode", args.filter_mode)
    store.ensure_setting("sync_api_base", args.sync_api_base)
    store.ensure_setting("repo_api_base", args.repo_api_base)

    resolver = None if args.disable_pds_resolution else DidResolver(cache_path=args.pds_cache)
    repo_clients: dict[str, object] = {}

    repos_processed = 0
    rows_retained = 0
    posts_seen = 0

    def client_for_did(repo_did: str):
        base_url = args.repo_api_base
        if resolver is not None:
            base_url = resolver.resolve(repo_did).pds_url
        if base_url not in repo_clients:
            repo_clients[base_url] = build_client(base_url)
        return repo_clients[base_url], base_url

    def process_repo(repo_did: str) -> None:
        nonlocal repos_processed, rows_retained, posts_seen
        repo_client, resolved_base = client_for_did(repo_did)
        rows, seen = fetch_repo_snapshot(
            repo_client,
            repo_did=repo_did,
            filter_mode=args.filter_mode,
            source_dataset=f"{args.source_dataset}:{resolved_base}",
            collection=args.collection,
            record_limit=args.record_limit,
            max_records=args.max_records_per_repo,
        )
        retained = store.replace_author_scope(repo_did, rows)
        store.record_repo_backfill(
            repo_did,
            posts_seen=seen,
            rows_retained=retained,
            status="ok",
        )
        repos_processed += 1
        rows_retained += retained
        posts_seen += seen
        if repos_processed % max(args.progress_every, 1) == 0:
            print(
                json.dumps(
                    {
                        "repos_processed": repos_processed,
                        "posts_seen": posts_seen,
                        "rows_retained": rows_retained,
                        "summary": store.summary(),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    try:
        if args.repo_did:
            process_repo(args.repo_did)
        else:
            cursor = args.start_cursor or store.get_state(args.cursor_key)
            for dids, next_cursor in iter_repo_did_pages(
                sync_client,
                collection=args.collection,
                cursor=cursor,
                limit=args.page_limit,
            ):
                for repo_did in dids:
                    try:
                        process_repo(repo_did)
                    except Exception as exc:
                        store.record_repo_backfill(
                            repo_did,
                            posts_seen=0,
                            rows_retained=0,
                            status="error",
                            last_error=str(exc),
                        )
                    if args.repo_limit and repos_processed >= args.repo_limit:
                        raise StopIteration
                store.set_state(args.cursor_key, next_cursor or "")
                if not next_cursor:
                    break
                cursor = next_cursor
    except StopIteration:
        pass
    finally:
        summary = {
            "repos_processed": repos_processed,
            "posts_seen": posts_seen,
            "rows_retained": rows_retained,
            "store_summary": store.summary(),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        store.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

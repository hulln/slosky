#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.atproto_sync import (
    DEFAULT_FIREHOSE_BASE,
    DEFAULT_REPO_API_BASE,
    POST_COLLECTION,
    build_client,
    build_firehose_client,
    extract_post_changes_from_commit,
    fetch_repo_snapshot,
    parse_subscribe_repos_message,
)
from slosky.did_resolver import DidResolver
from slosky.seed_authors import read_seed_author_csv
from slosky.sqlite_store import CorpusStore


def main() -> int:
    class StopCollector(Exception):
        pass

    parser = argparse.ArgumentParser(
        description="Continuously ingest all post updates for a watched list of Slovene-linked authors."
    )
    parser.add_argument("--seed-csv", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--repo-api-base", default=DEFAULT_REPO_API_BASE)
    parser.add_argument("--firehose-base", default=DEFAULT_FIREHOSE_BASE)
    parser.add_argument("--collection", default=POST_COLLECTION)
    parser.add_argument("--min-seed-posts", type=int, default=1)
    parser.add_argument("--cursor-key", default="seed_author_live_cursor_seq")
    parser.add_argument("--source-dataset", default="atproto:seed-author.firehose")
    parser.add_argument("--resync-source-dataset", default="atproto:seed-author.listRecords")
    parser.add_argument("--record-limit", type=int, default=100)
    parser.add_argument("--print-every", type=int, default=1000)
    parser.add_argument("--max-messages", type=int)
    parser.add_argument("--pds-cache", type=Path, default=Path("outputs/running/pds_cache.json"))
    parser.add_argument("--disable-pds-resolution", action="store_true")
    args = parser.parse_args()

    watched_authors = {
        str(row["author_did"])
        for row in read_seed_author_csv(args.seed_csv, min_posts=args.min_seed_posts)
    }

    store = CorpusStore(args.db)
    store.ensure_setting("collector_kind", "seed-author-live")
    store.ensure_setting("collection", args.collection)
    store.ensure_setting("filter_mode", "all-posts")
    store.ensure_setting("repo_api_base", args.repo_api_base)
    store.ensure_setting("firehose_base", args.firehose_base)
    store.ensure_setting("seed_csv", str(args.seed_csv))

    resolver = None if args.disable_pds_resolution else DidResolver(cache_path=args.pds_cache)
    repo_clients: dict[str, object] = {}

    def client_for_did(repo_did: str):
        base_url = args.repo_api_base
        if resolver is not None:
            base_url = resolver.resolve(repo_did).pds_url
        if base_url not in repo_clients:
            repo_clients[base_url] = build_client(base_url)
        return repo_clients[base_url], base_url

    saved_cursor = store.get_state(args.cursor_key)
    cursor = int(saved_cursor) if saved_cursor else None

    counters = {
        "messages": 0,
        "watched_commits": 0,
        "creates_or_updates": 0,
        "deletes": 0,
        "repo_resyncs": 0,
        "ignored_messages": 0,
    }
    firehose = build_firehose_client(cursor=cursor, base_uri=args.firehose_base)

    def refresh_repo(repo_did: str, *, last_event_seq: int | None = None) -> None:
        if repo_did not in watched_authors:
            return
        client, resolved_base = client_for_did(repo_did)
        rows, _ = fetch_repo_snapshot(
            client,
            repo_did=repo_did,
            filter_mode="all-posts",
            source_dataset=f"{args.resync_source_dataset}:{resolved_base}",
            collection=args.collection,
            record_limit=args.record_limit,
        )
        store.replace_author_scope(repo_did, rows, last_event_seq=last_event_seq)
        counters["repo_resyncs"] += 1

    def on_message(message) -> None:
        event = parse_subscribe_repos_message(message)
        counters["messages"] += 1

        if event.py_type == "com.atproto.sync.subscribeRepos#commit":
            repo_did = str(event.repo)
            if repo_did not in watched_authors:
                counters["ignored_messages"] += 1
            else:
                counters["watched_commits"] += 1
                if event.too_big:
                    refresh_repo(repo_did, last_event_seq=event.seq)
                else:
                    for change in extract_post_changes_from_commit(
                        event,
                        source_dataset=args.source_dataset,
                    ):
                        if change.action == "delete":
                            counters["deletes"] += store.mark_deleted(
                                change.uri,
                                deleted_at=str(event.time),
                                last_event_seq=event.seq,
                            )
                            continue
                        if change.row:
                            store.upsert_post(
                                change.row,
                                seen_at=str(event.time),
                                last_event_seq=event.seq,
                            )
                            counters["creates_or_updates"] += 1
            store.set_state(args.cursor_key, str(event.seq))
        elif event.py_type == "com.atproto.sync.subscribeRepos#sync":
            refresh_repo(str(event.did), last_event_seq=event.seq)
            store.set_state(args.cursor_key, str(event.seq))
        elif event.py_type == "com.atproto.sync.subscribeRepos#account":
            did = str(event.did)
            if did in watched_authors and (not event.active) and str(event.status or "") in {
                "deleted",
                "deactivated",
                "suspended",
                "takendown",
            }:
                store.mark_author_deleted(
                    did,
                    deleted_at=str(event.time),
                    last_event_seq=event.seq,
                )
            store.set_state(args.cursor_key, str(event.seq))

        if counters["messages"] % max(args.print_every, 1) == 0:
            print(
                json.dumps(
                    {
                        "watched_authors": len(watched_authors),
                        "counters": counters,
                        "summary": store.summary(),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        if args.max_messages and counters["messages"] >= args.max_messages:
            raise StopCollector

    def on_callback_error(error: BaseException) -> None:
        if isinstance(error, StopCollector):
            firehose.stop()

    try:
        firehose.start(
            on_message_callback=on_message,
            on_callback_error_callback=on_callback_error,
        )
    except StopCollector:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        print(
            json.dumps(
                {
                    "watched_authors": len(watched_authors),
                    "counters": counters,
                    "summary": store.summary(),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        store.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

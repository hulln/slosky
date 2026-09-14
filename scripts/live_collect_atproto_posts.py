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
from slosky.normalize import should_keep_row
from slosky.sqlite_store import CorpusStore


def main() -> int:
    class StopCollector(Exception):
        pass

    parser = argparse.ArgumentParser(
        description="Continuously ingest Bluesky firehose updates into the SQLite corpus store."
    )
    parser.add_argument("--db", type=Path, required=True, help="SQLite database path")
    parser.add_argument("--repo-api-base", default=DEFAULT_REPO_API_BASE)
    parser.add_argument("--firehose-base", default=DEFAULT_FIREHOSE_BASE)
    parser.add_argument("--collection", default=POST_COLLECTION)
    parser.add_argument("--filter-mode", choices=["tagged-sl", "all-posts"], default="tagged-sl")
    parser.add_argument("--cursor-key", default="atproto_live_cursor_seq")
    parser.add_argument("--source-dataset", default="atproto:firehose")
    parser.add_argument("--resync-source-dataset", default="atproto:repo.listRecords")
    parser.add_argument("--record-limit", type=int, default=100)
    parser.add_argument("--print-every", type=int, default=1000)
    parser.add_argument("--max-messages", type=int, help="Stop after this many firehose messages")
    parser.add_argument("--pds-cache", type=Path, default=Path("outputs/running/pds_cache.json"))
    parser.add_argument("--disable-pds-resolution", action="store_true")
    args = parser.parse_args()

    store = CorpusStore(args.db)
    store.ensure_setting("collector_kind", "atproto")
    store.ensure_setting("collection", args.collection)
    store.ensure_setting("filter_mode", args.filter_mode)
    store.ensure_setting("repo_api_base", args.repo_api_base)
    store.ensure_setting("firehose_base", args.firehose_base)

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
        "commits": 0,
        "creates_or_updates": 0,
        "deletes": 0,
        "filtered_out": 0,
        "repo_resyncs": 0,
    }
    firehose = build_firehose_client(cursor=cursor, base_uri=args.firehose_base)

    def refresh_repo(repo_did: str, *, last_event_seq: int | None = None) -> None:
        client, resolved_base = client_for_did(repo_did)
        rows, _ = fetch_repo_snapshot(
            client,
            repo_did=repo_did,
            filter_mode=args.filter_mode,
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
            counters["commits"] += 1
            if event.too_big:
                refresh_repo(str(event.repo), last_event_seq=event.seq)
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
                    if change.row and should_keep_row(change.row, args.filter_mode):
                        store.upsert_post(change.row, seen_at=str(event.time), last_event_seq=event.seq)
                        counters["creates_or_updates"] += 1
                    else:
                        affected = store.mark_deleted(
                            change.uri,
                            deleted_at=str(event.time),
                            last_event_seq=event.seq,
                        )
                        if affected:
                            counters["deletes"] += affected
                        else:
                            counters["filtered_out"] += 1
            store.set_state(args.cursor_key, str(event.seq))
        elif event.py_type == "com.atproto.sync.subscribeRepos#sync":
            refresh_repo(str(event.did), last_event_seq=event.seq)
            store.set_state(args.cursor_key, str(event.seq))
        elif event.py_type == "com.atproto.sync.subscribeRepos#account":
            if not event.active and str(event.status or "") in {
                "deleted",
                "deactivated",
                "suspended",
                "takendown",
            }:
                store.mark_author_deleted(
                    str(event.did),
                    deleted_at=str(event.time),
                    last_event_seq=event.seq,
                )
            store.set_state(args.cursor_key, str(event.seq))

        if counters["messages"] % max(args.print_every, 1) == 0:
            print(
                json.dumps(
                    {
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
        print(json.dumps({"counters": counters, "summary": store.summary()}, indent=2, ensure_ascii=False))
        store.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

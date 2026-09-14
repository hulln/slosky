from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from atproto import CAR, Client
from atproto import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from atproto_core.cid import CID

from slosky.normalize import normalize_post_record, should_keep_row


POST_COLLECTION = "app.bsky.feed.post"
DEFAULT_SYNC_API_BASE = "https://bsky.network"
DEFAULT_REPO_API_BASE = "https://bsky.social"
DEFAULT_FIREHOSE_BASE = "wss://bsky.network/xrpc"


def normalize_xrpc_base(base_url: str) -> str:
    if base_url.endswith("/xrpc"):
        return base_url
    return base_url.rstrip("/") + "/xrpc"


def normalize_firehose_base(base_uri: str) -> str:
    if base_uri.endswith("/xrpc"):
        return base_uri
    return base_uri.rstrip("/") + "/xrpc"


def build_client(base_url: str = DEFAULT_REPO_API_BASE) -> Client:
    return Client(base_url=normalize_xrpc_base(base_url))


def iter_repo_did_pages(
    client: Client,
    *,
    collection: str = POST_COLLECTION,
    cursor: str | None = None,
    limit: int = 2000,
) -> Iterator[tuple[list[str], str | None]]:
    next_cursor = cursor
    while True:
        response = client.com.atproto.sync.list_repos_by_collection(
            {
                "collection": collection,
                "cursor": next_cursor,
                "limit": limit,
            }
        )
        dids = [str(repo.did) for repo in response.repos]
        yield dids, response.cursor
        if not response.cursor:
            return
        next_cursor = response.cursor


def iter_repo_post_records(
    client: Client,
    *,
    repo_did: str,
    collection: str = POST_COLLECTION,
    cursor: str | None = None,
    limit: int = 100,
    reverse: bool = False,
) -> Iterator[tuple[str, dict]]:
    next_cursor = cursor
    while True:
        response = client.com.atproto.repo.list_records(
            {
                "repo": repo_did,
                "collection": collection,
                "cursor": next_cursor,
                "limit": limit,
                "reverse": reverse,
            }
        )
        for record in response.records:
            yield str(record.uri), record.value
        if not response.cursor:
            return
        next_cursor = response.cursor


def fetch_repo_snapshot(
    client: Client,
    *,
    repo_did: str,
    filter_mode: str,
    source_dataset: str,
    collection: str = POST_COLLECTION,
    record_limit: int = 100,
    max_records: int | None = None,
) -> tuple[list[dict], int]:
    rows: list[dict] = []
    posts_seen = 0
    for uri, record in iter_repo_post_records(
        client,
        repo_did=repo_did,
        collection=collection,
        limit=record_limit,
    ):
        posts_seen += 1
        normalized = normalize_post_record(
            uri=uri,
            author_did=repo_did,
            record=record,
            source_dataset=source_dataset,
        )
        if should_keep_row(normalized, filter_mode):
            rows.append(normalized)
        if max_records and posts_seen >= max_records:
            break
    return rows, posts_seen


def record_uri_from_path(repo_did: str, path: str) -> str:
    return f"at://{repo_did}/{path}"


def is_post_path(path: str, collection: str = POST_COLLECTION) -> bool:
    return path.startswith(collection + "/")


def _lookup_block(blocks: dict, cid_value: CID | str | object) -> dict | None:
    if cid_value in blocks:
        return blocks[cid_value]

    cid_str = str(cid_value)
    for block_cid, block in blocks.items():
        if str(block_cid) == cid_str:
            return block
    return None


@dataclass
class FirehoseChange:
    action: str
    uri: str
    row: dict | None


def extract_post_changes_from_commit(commit, *, source_dataset: str) -> list[FirehoseChange]:
    blocks: dict = {}
    if commit.blocks:
        raw_blocks = commit.blocks
        if isinstance(raw_blocks, str):
            raw_blocks = raw_blocks.encode("utf-8")
        blocks = CAR.from_bytes(bytes(raw_blocks)).blocks

    changes: list[FirehoseChange] = []
    for op in commit.ops:
        if not is_post_path(op.path):
            continue
        uri = record_uri_from_path(str(commit.repo), str(op.path))
        if op.action == "delete":
            changes.append(FirehoseChange(action="delete", uri=uri, row=None))
            continue
        if op.action not in {"create", "update"} or not op.cid:
            continue
        record = _lookup_block(blocks, op.cid)
        if not isinstance(record, dict):
            continue
        row = normalize_post_record(
            uri=uri,
            author_did=str(commit.repo),
            record=record,
            source_dataset=source_dataset,
            created_at_fallback=str(commit.time),
        )
        changes.append(FirehoseChange(action=str(op.action), uri=uri, row=row))
    return changes


def build_firehose_client(
    *,
    cursor: int | None = None,
    base_uri: str = DEFAULT_FIREHOSE_BASE,
) -> FirehoseSubscribeReposClient:
    params = {"cursor": cursor} if cursor is not None else None
    return FirehoseSubscribeReposClient(params=params, base_uri=normalize_firehose_base(base_uri))


__all__ = [
    "DEFAULT_FIREHOSE_BASE",
    "DEFAULT_REPO_API_BASE",
    "DEFAULT_SYNC_API_BASE",
    "POST_COLLECTION",
    "FirehoseChange",
    "build_client",
    "build_firehose_client",
    "extract_post_changes_from_commit",
    "fetch_repo_snapshot",
    "iter_repo_did_pages",
    "iter_repo_post_records",
    "normalize_firehose_base",
    "normalize_xrpc_base",
    "parse_subscribe_repos_message",
]

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_.-]+")
HASHTAG_RE = re.compile(r"(?<!\w)#[\w-]+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]"
)


def loads_json_or_none(value: str | None) -> Any:
    if not value or value == "null":
        return None
    return json.loads(value)


def normalize_domain(uri: str) -> str | None:
    parsed = urlparse(uri)
    if not parsed.netloc:
        return None
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def extract_link_domains(record: dict[str, Any]) -> list[str]:
    domains: set[str] = set()

    for facet in record.get("facets") or []:
        for feature in facet.get("features") or []:
            if feature.get("$type") == "app.bsky.richtext.facet#link":
                domain = normalize_domain(feature.get("uri", ""))
                if domain:
                    domains.add(domain)

    embed = record.get("embed") or {}
    embed_type = embed.get("$type")

    if embed_type == "app.bsky.embed.external":
        domain = normalize_domain(((embed.get("external") or {}).get("uri")) or "")
        if domain:
            domains.add(domain)

    if embed_type == "app.bsky.embed.recordWithMedia":
        media = embed.get("media") or {}
        if media.get("$type") == "app.bsky.embed.external":
            domain = normalize_domain(((media.get("external") or {}).get("uri")) or "")
            if domain:
                domains.add(domain)

    return sorted(domains)


def infer_embed_kind(record: dict[str, Any]) -> str | None:
    embed = record.get("embed")
    if isinstance(embed, dict):
        return embed.get("$type")
    return None


def infer_quote_flag(record: dict[str, Any]) -> bool:
    embed = record.get("embed")
    if not isinstance(embed, dict):
        return False

    embed_type = embed.get("$type")
    uri = None

    if embed_type == "app.bsky.embed.record":
        uri = ((embed.get("record") or {}).get("uri")) or None
    elif embed_type == "app.bsky.embed.recordWithMedia":
        uri = ((((embed.get("record") or {}).get("record")) or {}).get("uri")) or None

    return bool(uri and "/app.bsky.feed.post/" in uri)


def is_tagged_sl(langs: list[str]) -> bool:
    return any(lang == "sl" or lang.startswith("sl-") for lang in langs)


def strip_urls_and_mentions(text: str) -> str:
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def alpha_char_count(text: str) -> int:
    return sum(1 for char in text if char.isalpha())


def contains_hashtag(text: str) -> bool:
    return bool(HASHTAG_RE.search(text))


def contains_emoji(text: str) -> bool:
    return bool(EMOJI_RE.search(text))


def contains_mention(text: str) -> bool:
    return bool(MENTION_RE.search(text))


def normalize_export_row(row: dict[str, Any], source_dataset: str) -> dict[str, Any]:
    record_json = row.get("record_json")
    if record_json:
        record = loads_json_or_none(record_json) or {}
    else:
        event = loads_json_or_none(row.get("event_json")) or {}
        record = ((event.get("commit") or {}).get("record")) or {}

    langs = [str(lang) for lang in (record.get("langs") or [])]
    text = str(record.get("text") or "")
    source_bluesky_ts = row.get("source_bluesky_ts") or row.get("bluesky_ts") or ""

    return {
        "uri": row.get("uri") or "",
        "author_did": row.get("author_did") or "",
        "created_at": str(record.get("createdAt") or source_bluesky_ts),
        "text": text,
        "langs": langs,
        "reply_flag": bool(record.get("reply")),
        "quote_flag": infer_quote_flag(record),
        "embed_kind": infer_embed_kind(record),
        "facet_count": len(record.get("facets") or []),
        "link_domains": extract_link_domains(record),
        "source_dataset": source_dataset,
    }


def model_to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if hasattr(value, "dict"):
        return value.dict()
    raise TypeError(f"Unsupported record value type: {type(value)!r}")


def normalize_post_record(
    *,
    uri: str,
    author_did: str,
    record: dict[str, Any] | Any,
    source_dataset: str,
    created_at_fallback: str | None = None,
) -> dict[str, Any]:
    record_dict = model_to_dict(record)
    langs = [str(lang) for lang in (record_dict.get("langs") or [])]
    text = str(record_dict.get("text") or "")
    created_at = str(record_dict.get("createdAt") or created_at_fallback or "")

    return {
        "uri": uri,
        "author_did": author_did,
        "created_at": created_at,
        "text": text,
        "langs": langs,
        "reply_flag": bool(record_dict.get("reply")),
        "quote_flag": infer_quote_flag(record_dict),
        "embed_kind": infer_embed_kind(record_dict),
        "facet_count": len(record_dict.get("facets") or []),
        "link_domains": extract_link_domains(record_dict),
        "source_dataset": source_dataset,
    }


def should_keep_row(row: dict[str, Any], filter_mode: str) -> bool:
    if filter_mode == "all-posts":
        return True
    if filter_mode == "tagged-sl":
        return is_tagged_sl(row.get("langs") or [])
    raise ValueError(f"Unsupported filter mode: {filter_mode}")

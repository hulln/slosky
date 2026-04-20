#!/usr/bin/env python3
"""Anonymize the final corpus for public release.

Produces a JSONL (and optional CSV) with:
  - author_did  → author_id  (author_001 … author_NNN)
  - uri         → post_id    (post_000001 … post_NNNNNN)
  - @-mentions in text replaced with pseudonymized tokens:
      - corpus authors  → @author_NNN
      - external people → @external_NNN
  - user-owned custom domains in link_domains → [personal-domain]
  - dropped fields: uri, author_did, source_dataset, deleted, deleted_at, signals

Usage:
    python scripts/anonymize_corpus.py
    python scripts/anonymize_corpus.py \
        --input outputs/final/final_sl_corpus.jsonl \
        --pds-cache outputs/running/pds_cache.json \
        --output-jsonl outputs/release/slosky_corpus_anon.jsonl \
        --output-csv outputs/release/slosky_corpus_anon.csv \
        --mapping-json outputs/release/author_mapping.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]+)")

# Domains that are clearly organizational / news / platforms — keep as-is in link_domains.
# Everything else from custom-domain corpus authors gets redacted.
ORGANIZATIONAL_DOMAINS = {
    "n1info.si",
    "tehnozvezdje.si",
    "odprtaznanost.si",
    "kratkazgodba.si",
    "danesjenovdan.si",
    "opravicujemo.se",
    "voltslovenija.org",
    "zps.si",
    "koofr.net",
    "tnz.social",
}


def normalize_host(value: str) -> str:
    host = urlparse(value).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_user_owned_custom_domain(handle: str, pds_url: str) -> bool:
    handle = handle.lower().strip()
    if not handle:
        return False
    if handle.endswith(".bsky.social"):
        return False

    pds_host = normalize_host(pds_url)
    if pds_host and handle.endswith("." + pds_host):
        return False

    return True


def build_author_mapping(
    corpus_path: Path, pds_cache_path: Path
) -> tuple[dict[str, str], dict[str, str], set[str]]:
    """Build DID → author_id and handle → author_id mappings.

    Returns:
        author_id_by_did: {did: "author_001", ...}
        author_id_by_handle: {handle_lower: "author_001", ...}
        personal_domain_handles: set of custom domain handles that are personal
    """
    # Load PDS cache for handle resolution
    with pds_cache_path.open(encoding="utf-8") as f:
        pds_cache = json.load(f)

    # Collect all corpus author DIDs in order of first appearance
    seen_dids: list[str] = []
    seen_set: set[str] = set()
    with corpus_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line.strip())
            did = row["author_did"]
            if did not in seen_set:
                seen_dids.append(did)
                seen_set.add(did)

    # Assign author IDs
    author_id_by_did: dict[str, str] = {}
    author_id_by_handle: dict[str, str] = {}
    personal_domain_handles: set[str] = set()

    for idx, did in enumerate(seen_dids, start=1):
        author_id = f"author_{idx:03d}"
        author_id_by_did[did] = author_id

        entry = pds_cache.get(did, {})
        handle = entry.get("handle", "")
        if handle:
            handle_lower = handle.lower()
            author_id_by_handle[handle_lower] = author_id

            # Track user-owned custom domains, not hosted PDS subdomains.
            if is_user_owned_custom_domain(handle_lower, entry.get("pds_url", "")):
                # Check if it's an organizational domain
                base_domain = handle_lower
                if base_domain not in ORGANIZATIONAL_DOMAINS:
                    personal_domain_handles.add(base_domain)

    return author_id_by_did, author_id_by_handle, personal_domain_handles


def pseudonymize_mentions(
    text: str,
    author_id_by_handle: dict[str, str],
    external_mapping: dict[str, str],
    external_counter: list[int],
) -> str:
    """Replace @-mentions with pseudonymized tokens."""

    def replace_mention(match: re.Match) -> str:
        handle = match.group(1).lower()
        # Strip trailing dots (common typo: @handle.bsky.social.)
        handle = handle.rstrip(".")

        # Check if it's a corpus author
        if handle in author_id_by_handle:
            return f"@{author_id_by_handle[handle]}"

        # Check if it's already mapped as external
        if handle in external_mapping:
            return f"@{external_mapping[handle]}"

        # New external mention
        external_counter[0] += 1
        ext_id = f"external_{external_counter[0]:03d}"
        external_mapping[handle] = ext_id
        return f"@{ext_id}"

    return MENTION_RE.sub(replace_mention, text)


def redact_link_domains(
    domains: list[str], personal_domain_handles: set[str]
) -> list[str]:
    """Replace personal domains with [personal-domain]."""
    result = []
    for domain in domains:
        d = domain.lower()
        if d in personal_domain_handles:
            result.append("[personal-domain]")
        else:
            result.append(domain)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input", type=Path, default=Path("outputs/final/final_sl_corpus.jsonl")
    )
    parser.add_argument(
        "--pds-cache", type=Path, default=Path("outputs/running/pds_cache.json")
    )
    parser.add_argument(
        "--output-jsonl", type=Path, default=Path("outputs/release/slosky_corpus_anon.jsonl")
    )
    parser.add_argument("--output-csv", type=Path, default=Path("outputs/release/slosky_corpus_anon.csv"))
    parser.add_argument(
        "--mapping-json",
        type=Path,
        default=Path("outputs/private/author_mapping.json"),
        help="Private mapping file (DO NOT publish). For your own reference only.",
    )
    args = parser.parse_args()

    print(f"Building author mapping from {args.input} + {args.pds_cache} ...")
    author_id_by_did, author_id_by_handle, personal_domain_handles = build_author_mapping(
        args.input, args.pds_cache
    )
    print(f"  {len(author_id_by_did)} corpus authors mapped")
    print(f"  {len(author_id_by_handle)} handles mapped")
    print(f"  {len(personal_domain_handles)} personal domain handles to redact")

    # Prepare output
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    external_mapping: dict[str, str] = {}
    external_counter = [0]

    csv_fieldnames = [
        "author_id",
        "post_id",
        "created_at",
        "text",
        "langs",
        "reply_flag",
        "quote_flag",
        "embed_kind",
        "facet_count",
        "link_domains",
        "decision",
        "langid_label",
        "langid_score",
        "langdetect_sl_prob",
    ]

    csv_handle = None
    csv_writer = None
    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        csv_handle = args.output_csv.open("w", encoding="utf-8", newline="")
        csv_writer = csv.DictWriter(csv_handle, fieldnames=csv_fieldnames)
        csv_writer.writeheader()

    post_counter = 0
    mentions_replaced = 0
    domains_redacted = 0

    print(f"Anonymizing ...")
    try:
        with args.input.open(encoding="utf-8") as in_f, \
             args.output_jsonl.open("w", encoding="utf-8") as out_f:
            for line in in_f:
                row = json.loads(line.strip())
                post_counter += 1

                # Pseudonymize author
                author_id = author_id_by_did[row["author_did"]]
                post_id = f"post_{post_counter:06d}"

                # Pseudonymize mentions in text
                original_text = row["text"]
                anon_text = pseudonymize_mentions(
                    original_text, author_id_by_handle, external_mapping, external_counter
                )
                if anon_text != original_text:
                    mentions_replaced += 1

                # Redact personal domains in link_domains
                original_domains = row.get("link_domains", [])
                anon_domains = redact_link_domains(original_domains, personal_domain_handles)
                if anon_domains != original_domains:
                    domains_redacted += 1

                # Build output row
                out_row = {
                    "author_id": author_id,
                    "post_id": post_id,
                    "created_at": row["created_at"],
                    "text": anon_text,
                    "langs": row["langs"],
                    "reply_flag": row["reply_flag"],
                    "quote_flag": row["quote_flag"],
                    "embed_kind": row.get("embed_kind"),
                    "facet_count": row["facet_count"],
                    "link_domains": anon_domains,
                    "decision": row["decision"],
                    "langid_label": row.get("langid_label", ""),
                    "langid_score": row.get("langid_score"),
                    "langdetect_sl_prob": row.get("langdetect_sl_prob"),
                }

                out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")

                if csv_writer is not None:
                    csv_writer.writerow({
                        **out_row,
                        "langs": "|".join(out_row["langs"]),
                        "link_domains": "|".join(out_row["link_domains"]),
                        "reply_flag": int(out_row["reply_flag"]),
                        "quote_flag": int(out_row["quote_flag"]),
                    })
    finally:
        if csv_handle is not None:
            csv_handle.close()

    # Save private mapping (NOT for publication)
    mapping = {
        "WARNING": "This file maps pseudonymized IDs back to real identities. DO NOT publish.",
        "authors": {
            author_id: did for did, author_id in sorted(author_id_by_did.items(), key=lambda x: x[1])
        },
        "external_mentions": {
            ext_id: handle for handle, ext_id in sorted(external_mapping.items(), key=lambda x: x[1])
        },
    }
    args.mapping_json.parent.mkdir(parents=True, exist_ok=True)
    args.mapping_json.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"\nDone.")
    print(f"  Posts written:        {post_counter:,}")
    print(f"  Posts with mentions replaced: {mentions_replaced:,}")
    print(f"  Posts with domains redacted:  {domains_redacted:,}")
    print(f"  Corpus authors:       {len(author_id_by_did)}")
    print(f"  External mentions:    {external_counter[0]}")
    print(f"  Output JSONL:         {args.output_jsonl}")
    if args.output_csv:
        print(f"  Output CSV:           {args.output_csv}")
    print(f"  Mapping (PRIVATE):    {args.mapping_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

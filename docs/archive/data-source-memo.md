# Data Source Memo

## Current decision

Use a protocol-native ATProto collection pipeline as the main paper source:

- historical discovery: `com.atproto.sync.listReposByCollection` via `https://bsky.network`
- historical recovery of current repo state: `com.atproto.repo.listRecords` via each DID's resolved PDS
- live continuation after the historical crawl: `com.atproto.sync.subscribeRepos`
- strict final export: consensus filtering over expanded author histories

The paper should describe the corpus as a collection of **currently recoverable public posts**. Deleted posts are outside scope.

## What this source can support

- A historical corpus that reaches back to the earliest still-existing public Slovene post recovered by the crawl.
- Continued collection after the snapshot date through a live firehose subscriber.
- Reproducible local storage with delete handling for future live updates.
- Recovery from non-`bsky.social` PDSes through DID resolution.
- A high-precision final corpus layer separated from weaker review candidates.

## What this source cannot support

- Deleted posts that were removed before the crawl began.
- A claim about the absolute first Slovene Bluesky post ever published, if that post no longer exists publicly.

## Legacy pilot findings

- Warehouse endpoint: `https://sql-clickhouse.clickhouse.com/`
- Public login works with user `demo` and a blank password.
- The main historical table `bluesky.bluesky` contains `app.bsky.feed.post` records from **2024-12-23 14:00:00** through **2025-06-16 15:19:59.982**.
- Within that table, the default Slovene-tagged filter (`langs` containing `sl` or `sl-*`) yields:
  - **60,044 posts**
  - **823 unique authors**
  - date span **2024-12-23 14:06:19.537** to **2025-06-16 15:18:57.672**
- The rolling table `bluesky.bluesky_dedup` is much newer and much narrower for this purpose:
  - **3,631,168 post records**
  - date span **2026-03-09 18:00:00** to **2026-03-10 18:07:06.077**
- `bluesky.bluesky_raw_v2` exists, but its materialized timestamps include malformed outliers, so it should not be the default paper source without a stricter cleaning pass.

## Implication for the paper claim

Do not claim “all Slovene Bluesky posts ever published.”

Use wording like:

> a corpus of currently recoverable public Slovene Bluesky posts, collected via protocol-native ATProto backfill and continued live collection

If the final retained corpus uses `langs` as the main inclusion rule, be explicit that Slovene is operationalized through post-level language tags and later validation.

## Practical recommendation

- Treat the ClickHouse corpus as a quick pilot only.
- Build the real paper corpus from the local ATProto backfill/live pipeline.
- Record the earliest recovered `createdAt` and the snapshot date after the first full backfill, then use those exact dates in the paper.

## Open caveats

- The `langs` field is a pragmatic collection filter, not a perfect Slovene detector.
- A seed-expansion workflow can miss authors who never emit tagged Slovene posts unless a full network-wide all-posts crawl is added later.
- `listRecords` and live sync together recover current public state plus future public events, not deleted historical content.
- If you later want unlabeled Slovene posts as well, the safer route is to store all posts locally and apply language identification after collection rather than claiming `langs` is complete.

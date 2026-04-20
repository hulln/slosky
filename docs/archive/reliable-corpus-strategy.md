# Reliable Corpus Strategy

## What we are trying to optimize

The target is not just "many posts." The target is:

- as many public Slovene Bluesky posts as we can recover
- from the earliest surviving posts through the current snapshot
- across all Bluesky PDSes, not just `bsky.social`
- with a final core dataset that is precise enough for a paper

## Why one simple filter is not enough

### `langs=sl` alone is not enough

It helps discovery, but it has two problems:

- some non-Slovene posts are tagged `sl`
- some Slovene posts are not tagged `sl`

So it is useful for discovery, not sufficient as a gold-standard corpus rule.

### Language ID alone is not enough

It improves recall, but it can over-predict Slovene on:

- very short texts
- mixed-language posts
- South Slavic near-neighbors
- emoji-heavy or link-heavy posts

So it is useful as corroboration, not as the only final signal.

## Why multi-PDS recovery matters

Bluesky is decentralized. If a collector assumes every repo is served from `bsky.social`, it will miss users hosted elsewhere.

The corrected pipeline therefore:

- enumerates public repos through the relay infrastructure
- resolves each DID through PLC or `did:web`
- reads repo records from that DID's current PDS

This is necessary for a defensible "Bluesky-wide" methodology.

## Recommended practical workflow

### Layer 1: global tagged discovery

Run a network-wide historical crawl in `tagged-sl` mode, plus a live `tagged-sl` firehose collector.

Why:

- it is much lighter than a full all-posts mirror
- it finds Slovene-linked authors across the network
- it gives a high-recall discovery layer for authors who have ever emitted tagged Slovene posts

### Layer 2: full-history author expansion

Take the discovered authors and backfill all their surviving public posts from their actual PDSes.

Why:

- this is how we recover older and unlabeled Slovene posts from those authors
- it is far cheaper than mirroring the whole network in all-posts mode

### Layer 2b: live author watchlist

For ongoing collection, keep a second firehose collector that follows all future posts from the discovered Slovene-linked authors.

Why:

- it catches future unlabeled Slovene posts from known accounts
- it is especially useful for event periods such as elections

### Layer 3: strict core export

From the expanded store, create:

- `strict_sl_core`: high-precision corpus
- `strict_sl_review`: weaker candidates that need checking

Current strict rule:

- keep a post in the core corpus only if it has a Slovene tag and at least one of these model signals:
  - `langs` indicates Slovene
  - `langid` predicts Slovene
  - `langdetect` strongly predicts Slovene

Why:

- it removes obvious false positives from `sl` tagging
- it avoids letting model-only predictions define the final paper corpus

## What this still misses

This is the most important remaining limitation.

The workflow can still miss:

- accounts that never tag Slovene and are never discovered through the tagged layer
- deleted posts
- posts from currently unreachable repos

The only stronger solution would be a network-wide historical `all-posts` crawl followed by language identification over everything. That is the conceptual gold standard, but it is much heavier in time, storage, and compute.

## Recommended paper framing

For the strict core dataset, use wording like:

> a high-precision corpus of currently recoverable public Slovene Bluesky posts, built through multi-PDS ATProto collection and consensus-based language filtering

For the broader project, use wording like:

> a layered corpus-building workflow that combines network-wide tagged discovery, full-history author expansion, and strict validation-oriented filtering

## Decision log

### Why not rely on the ClickHouse warehouse

- it starts too late for a from-the-beginning claim
- it was useful for prototyping, not for the final historical source

### Why not rely on `bsky.social` only

- it breaks the decentralized assumption
- it misses repos on other PDSes

### Why not use the permissive hybrid export as the final corpus

- it admits too many weak cases
- it is better as an exploratory layer than as the paper dataset

### Why keep a review bucket

- it preserves recoverable borderline cases
- it lets you inspect what the strict rule is excluding
- it supports a transparent methodology instead of pretending a binary classifier is perfect

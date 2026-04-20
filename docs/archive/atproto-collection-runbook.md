# ATProto Collection Runbook

## Goal

Build a corpus that reaches from the earliest still-existing public Slovene Bluesky post recovered by the crawl through the current snapshot date, then continue collecting new posts live.

The corrected workflow now treats Bluesky as decentralized:

- repo enumeration: `https://bsky.network`
- repo record recovery: each DID's resolved PDS from PLC or `did:web`
- live firehose: `wss://bsky.network/xrpc`

## Reliability strategy

Use a layered workflow instead of one loose filter:

1. Network-wide tagged-Slovene discovery.
2. Live tagged-Slovene continuation.
3. Full-history expansion for discovered Slovene-linked authors.
4. Strict core export that requires at least two independent Slovene signals.
5. Separate review bucket for weaker candidates.

This is the best practical compromise between recall and precision without attempting a full network-wide all-posts mirror.

## Phase 1: Historical tagged discovery

Test the pipeline on a single repo:

```bash
python3 scripts/backfill_atproto_posts.py \
  --db outputs/atproto_corpus.sqlite \
  --repo-did did:plc:nonkr26xddsxkwcenbmesbku \
  --filter-mode tagged-sl
```

Then run the network crawl:

```bash
python3 scripts/backfill_atproto_posts.py \
  --db outputs/atproto_corpus.sqlite \
  --filter-mode tagged-sl \
  --progress-every 100
```

If you stop the process, rerun the same command. The script resumes from the saved repo-enumeration cursor.

## Phase 2: Live continuation

```bash
python3 scripts/live_collect_atproto_posts.py \
  --db outputs/atproto_live.sqlite \
  --filter-mode tagged-sl \
  --print-every 1000
```

The firehose itself is network-wide. PDS resolution matters for repo resyncs triggered by oversized commits or explicit sync events.

## Phase 3: Merge discovery stores

```bash
python3 scripts/merge_atproto_stores.py \
  --target-db outputs/atproto_tagged.sqlite \
  --source-db outputs/atproto_corpus.sqlite \
  --source-db outputs/atproto_live.sqlite
```

Audit the merged discovery store:

```bash
python3 scripts/audit_atproto_store.py \
  --db outputs/atproto_tagged.sqlite
```

## Phase 4: Expand discovered Slovene-linked authors

Build the seed list from the merged tagged store:

```bash
python3 scripts/build_seed_author_list.py \
  --output-csv outputs/intermediate/seed_authors.csv \
  --store-source outputs/atproto_tagged.sqlite
```

Then recover full histories for those authors:

```bash
python3 scripts/backfill_seed_authors.py \
  --seed-csv outputs/intermediate/seed_authors.csv \
  --db outputs/intermediate/seed_author_posts.sqlite \
  --progress-every 25
```

To keep following those authors after the historical snapshot:

```bash
python3 scripts/live_collect_seed_authors.py \
  --seed-csv outputs/intermediate/seed_authors.csv \
  --db outputs/running/seed_author_live.sqlite \
  --print-every 1000
```

Later merge `seed_author_live.sqlite` into `seed_author_posts.sqlite`.

If you need to retry only failed authors after fixing infrastructure:

```bash
python3 scripts/backfill_seed_authors.py \
  --seed-csv outputs/intermediate/seed_authors.csv \
  --db outputs/intermediate/seed_author_posts.sqlite \
  --retry-errors-only \
  --progress-every 25
```

## Phase 5: Build the strict core corpus

```bash
python3 scripts/export_strict_sl_corpus.py \
  --db outputs/intermediate/seed_author_posts.sqlite \
  --core-jsonl outputs/intermediate/strict_sl_core.jsonl \
  --core-csv outputs/intermediate/strict_sl_core.csv \
  --review-jsonl outputs/intermediate/strict_sl_review.jsonl \
  --review-csv outputs/intermediate/strict_sl_review.csv
```

The strict exporter keeps only rows supported by a Slovene tag plus at least one model signal:

- `langs` contains `sl` or `sl-*`
- `langid` predicts `sl`
- `langdetect` gives high Slovene probability

Model-only rows, tag-only rows, and very short tagged rows go into `strict_sl_review.*`.

## Phase 6: Validation

Sample the core corpus:

```bash
python3 scripts/sample_main_corpus.py \
  --input outputs/intermediate/strict_sl_core.jsonl \
  --output-csv outputs/samples/precision_validation_sample.csv \
  --size 300 \
  --seed 20260310
```

Sample the review bucket separately:

```bash
python3 scripts/sample_main_corpus.py \
  --input outputs/intermediate/strict_sl_review.jsonl \
  --output-csv outputs/samples/review_validation_sample.csv \
  --size 300 \
  --seed 20260311
```

Annotate with:

- `Slovene-dominant`
- `Mixed-with-Slovene`
- `Not-Slovene`
- `Undeterminable/too-short`

## Methodology wording

Use wording like:

> We collected currently recoverable public Bluesky posts through a protocol-native ATProto workflow. Historical repository discovery used the public Bluesky relay infrastructure, while repository recovery resolved each DID to its current personal data server. Ongoing data were collected from the public repository event stream. Deleted posts that were unavailable at crawl time were outside the scope of the corpus.

For the strict core corpus, add:

> The final high-precision corpus retained only posts that combined a Slovene language tag with at least one independent language-identification signal, while weaker candidates were separated into a manual-review bucket.

# Quality Assurance

This document summarizes what has already been checked about the current paper corpus and what still remains a limitation.

## Current official dataset

The current paper dataset is:

- [final_sl_corpus.jsonl](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.jsonl)
- [final_sl_corpus.csv](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.csv)

## Structural audit

The final corpus was structurally audited with:

- [audit_final_corpus.py](/home/nives/Projekti/slosky/scripts/audit_final_corpus.py)
- [final_corpus_audit.json](/home/nives/Projekti/slosky/outputs/validated/final_corpus_audit.json)

Current structural results:

- `141,013` total rows
- all rows belong to allowed final decision groups
- `0` blank-text rows
- `0` rows empty after project URL/mention stripping
- `0` rows with zero alphabetic characters after project cleaning
- `0` rows below the project minimum of `20` alphabetic characters after project cleaning

This means the final corpus does not currently contain the blank, emoji-only, or link-only rows that were a problem in the noisier review material.

## Manual validation already completed

Manual validation is documented in:

- [validation-results.md](/home/nives/Projekti/slosky/docs/paper/validation-results.md)

Current validation basis:

- strict core sample: `300 / 300` acceptable as Slovene
- review sample: `216 / 300` acceptable overall, with noise concentrated in excluded groups
- follow-up single-model samples:
  - `review_langid_only`: `50 / 50` acceptable
  - `review_langdetect_only`: `49 / 50` acceptable

## Why the final corpus is more defensible than the raw review layer

The final corpus keeps only these decision groups:

- `core_tag_supported`
- `review_model_consensus_only`
- `review_langid_only`
- `review_langdetect_only`

It excludes:

- `review_tag_only`
- `review_short_tagged`

This is the main reason the final corpus is cleaner than the broader review layer.

## What is still a real limitation

The corpus is defensible, but not perfect.

The remaining real limitations are:

- it is based on discovered Slovene-linked accounts, not a proven complete census of all Slovene Bluesky users
- deleted posts are not recoverable
- mixed-language posts remain in the dataset if they contain meaningful Slovene
- the single-model-only groups have only small dedicated follow-up samples (`50` rows each), so their uncertainty is lower than before but not eliminated

## Optional strengthening step

No additional routine annotation is required for the current paper dataset.

If you want an even stronger appendix-level claim, the best optional next step is to enlarge one of the already-defined validation checks:

- extend the single-model follow-up samples beyond `50` rows each
- extend the false-negative sample beyond `200` rows

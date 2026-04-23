# Outputs Layout

This folder is split by purpose.

The key distinction is:

- some outputs are stable research artefacts worth keeping;
- some are temporary runtime state;
- some are old exploratory material kept only for traceability.

## `outputs/final/`

Current official paper dataset.

- final merged corpus
- metadata for the final corpus

## `outputs/intermediate/`

Important build artifacts that were used to produce the final dataset.

- historical author-history store
- strict core/review split
- seed-author CSV

## `outputs/samples/`

Unannotated validation samples prepared for manual review.

## `outputs/validated/`

Annotated or summarized validation results.

## `outputs/running/`

Files used by active or resumable background collectors.

- discovery backfill store
- discovery live store
- seed-author live store
- PDS cache

Treat this directory as mutable runtime state, not as a clean release snapshot.

## `outputs/legacy/`

Older pilot and experimental material kept for reference.

## Practical reading guide

If you are trying to understand the paper result first, start with:

- `outputs/final/`
- `outputs/validated/`
- `outputs/community_formation/`
- `outputs/interaction_analysis/`
- `outputs/topic_analysis/`

If you are trying to rerun or extend collection, inspect:

- `outputs/running/`
- `outputs/intermediate/`

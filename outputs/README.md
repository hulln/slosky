# Outputs Layout

This folder is split by purpose.

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

## `outputs/legacy/`

Older pilot and experimental material kept for reference.

# Current Status

## What is finished

These parts are already done:

- multi-PDS collection support is implemented
- the large historical author-history store is built
- the strict export is built
- validation sample files are built

Historical corpus currently available:

- [seed_author_posts.sqlite](/home/nives/Projekti/slosky/outputs/intermediate/seed_author_posts.sqlite)
- `379,482` posts
- `742` active authors
- earliest recovered post: `2023-05-10T18:32:24.237Z`
- latest recovered post: `2026-04-16T10:24:21.070Z`

Strict corpus currently available:

- [strict_sl_core.jsonl](/home/nives/Projekti/slosky/outputs/intermediate/strict_sl_core.jsonl)
- [strict_sl_review.jsonl](/home/nives/Projekti/slosky/outputs/intermediate/strict_sl_review.jsonl)
- `85,094` core posts
- `122,889` review posts

Final corpus currently available:

- [final_sl_corpus.jsonl](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.jsonl)
- [final_sl_corpus.csv](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.csv)
- `141,013` posts
- composition documented in [methodology-decision.md](/home/nives/Projekti/slosky/docs/methodology-decision.md)
- earliest included post: `2023-08-09T13:51:59.646Z`
- latest included post: `2026-04-16T08:04:41.860109Z`

Validation samples currently available:

- [strict_core_validation_sample.csv](/home/nives/Projekti/slosky/outputs/samples/strict_core_validation_sample.csv)
- [strict_review_validation_sample.csv](/home/nives/Projekti/slosky/outputs/samples/strict_review_validation_sample.csv)
- [strict_review_validation_sample_annotated.csv](/home/nives/Projekti/slosky/outputs/validated/strict_review_validation_sample_annotated.csv)
- [strict_review_validation_summary.json](/home/nives/Projekti/slosky/outputs/validated/strict_review_validation_summary.json)
- [optional_langid_only_validation_sample.csv](/home/nives/Projekti/slosky/outputs/validated/optional_langid_only_validation_sample.csv)
- [optional_langdetect_only_validation_sample.csv](/home/nives/Projekti/slosky/outputs/validated/optional_langdetect_only_validation_sample.csv)

Current validation summary:

- [validation-results.md](/home/nives/Projekti/slosky/docs/validation-results.md)
- QA summary: [quality-assurance.md](/home/nives/Projekti/slosky/docs/quality-assurance.md)
- machine-readable QA audit: [final_corpus_audit.json](/home/nives/Projekti/slosky/outputs/validated/final_corpus_audit.json)
- detector comparison: [detector-choice.md](/home/nives/Projekti/slosky/docs/detector-choice.md)
- strict core sample manually checked: `300 / 300` acceptable as Slovene
- strict review sample manually checked: review set is too noisy to merge wholesale
- current corpus decision: [methodology-decision.md](/home/nives/Projekti/slosky/docs/methodology-decision.md)
- paper-style methodology wording: [methodology-section-draft.md](/home/nives/Projekti/slosky/docs/methodology-section-draft.md)
- chronological documentation: [process-log.md](/home/nives/Projekti/slosky/docs/process-log.md)

Current official corpus for the paper:

- [final_sl_corpus.jsonl](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.jsonl)
- [final_sl_corpus.csv](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.csv)
- `141,013` posts

Important file note:

- use the non-dated files above as the clean current paths
- ignore `*_20260416` and `*_full_20260416` corpus files unless you are debugging a rebuild

Experimental fastText/Lingua files:

- moved to [experimental_ftlingua](/home/nives/Projekti/slosky/outputs/legacy/experimental_ftlingua)
- these are not the current paper dataset

## What is still running

These are running or resumable background collector files:

1. [seed_author_live.sqlite](/home/nives/Projekti/slosky/outputs/running/seed_author_live.sqlite)
   - live collection from known Slovene-linked accounts
2. [atproto_discovery_backfill.sqlite](/home/nives/Projekti/slosky/outputs/running/atproto_discovery_backfill.sqlite)
   - slow network-wide historical tagged discovery
3. [atproto_discovery_live.sqlite](/home/nives/Projekti/slosky/outputs/running/atproto_discovery_live.sqlite)
   - inactive/resumable live tagged discovery store
4. [pds_cache.json](/home/nives/Projekti/slosky/outputs/running/pds_cache.json)
   - cache used by collectors for PDS resolution

These are useful, but they are not blocking the current dataset.

## What is the next important step

The next important step is not more engineering.

It is:

1. use the final merged corpus as the main paper dataset
2. write the methods and validation sections from the documented decisions
3. optionally spot-check the single-model validation samples if you want an even stronger appendix claim

That is the point where the corpus turns from a technical build into a paper draft.

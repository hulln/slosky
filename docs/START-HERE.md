# Start Here

This file is the simplest accurate summary of the project.

Paper status:

- the JTDH 2026 paper was submitted on `2026-04-23`
- submission record: [paper/records/SUBMISSION-2026-04-23.md](/home/nives/Projekti/slosky/paper/records/SUBMISSION-2026-04-23.md)

## What has already been done

We already built a **usable final paper corpus**.

- We found a set of Slovene-linked Bluesky accounts.
- We downloaded all surviving public posts from those accounts.
- We split the recovered posts into a strict core and a review layer.
- We manually validated the samples.
- We then built one final merged corpus from the validated good groups.

Current historical base:

- [seed_author_posts.sqlite](/home/nives/Projekti/slosky/outputs/intermediate/seed_author_posts.sqlite)
- `379,482` posts
- `742` active authors
- earliest recovered post: `2023-05-10T18:32:24.237Z`
- latest recovered post: `2026-04-16T10:24:21.070Z`

Current official paper dataset:

- [final_sl_corpus.jsonl](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.jsonl)
- [final_sl_corpus.csv](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.csv)
- `141,013` posts
- earliest included post: `2023-08-09T13:51:59.646Z`
- latest included post: `2026-04-16T08:04:41.860109Z`

Important intermediate artifacts:

- [strict_sl_core.jsonl](/home/nives/Projekti/slosky/outputs/intermediate/strict_sl_core.jsonl)
- [strict_sl_review.jsonl](/home/nives/Projekti/slosky/outputs/intermediate/strict_sl_review.jsonl)
- [strict_sl_core.csv](/home/nives/Projekti/slosky/outputs/intermediate/strict_sl_core.csv)
- [strict_sl_review.csv](/home/nives/Projekti/slosky/outputs/intermediate/strict_sl_review.csv)
- current counts:
  - `85,094` core posts
  - `122,889` review posts

## What is still running

Background collectors may still run, but they are not required for the current paper dataset.

Current running/resumable collector files live under:

- [outputs/running/](/home/nives/Projekti/slosky/outputs/running)

These are for improving and extending the corpus, not for defining the current paper dataset.

## What matters now

If you want the dataset you should actually use for the paper, use:

- [final_sl_corpus.csv](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.csv)
- [final_sl_corpus.jsonl](/home/nives/Projekti/slosky/outputs/final/final_sl_corpus.jsonl)
- [quality-assurance.md](/home/nives/Projekti/slosky/docs/paper/quality-assurance.md)

Ignore the dated `*_20260416` and `*_full_20260416` corpus files unless a doc explicitly tells you to inspect them. The non-dated files above are now the clean current paths.

If you want to validate the dataset, use:

- [strict_core_validation_sample.csv](/home/nives/Projekti/slosky/outputs/samples/strict_core_validation_sample.csv)
- [strict_review_validation_sample.csv](/home/nives/Projekti/slosky/outputs/samples/strict_review_validation_sample.csv)
- [annotate_samples.html](/home/nives/Projekti/slosky/tools/annotate_samples.html)

## What is the next step

The next human step is:

1. Keep the submitted paper state stable.
2. Clean and document the repository for GitHub/public release.
3. Only extend collection or annotation if the next paper version needs it.

## What is archived

Old pilot material, test files, and outdated or experimental files were moved into:

- `docs/archive/`
- `scripts/legacy/`
- `queries/legacy/`
- `outputs/legacy/`

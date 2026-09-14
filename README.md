# SloSky

SloSky is the corpus-construction workflow and aggregate analysis accompanying the paper *A Community in Formation: Corpus Construction and Initial Analysis of Slovene Posts on Bluesky*. The study corpus contains 141,013 Slovene-language posts from 432 authors, collected through ATProto and filtered using language metadata, automatic language identification, and manual validation.

This repository provides the methodology code and privacy-safe aggregate results. It is not a distribution of the corpus itself.

**Paper:** Publication link to be added after publication.

## Data

The underlying social-media corpus is not distributed. Post text, post and account identifiers, exact user chronology, validation rows, PDS-resolution data, pseudonymized full text, and linguistic annotation are restricted because they could enable reconstruction of a small identifiable community.

[data/README.md](data/README.md) describes the private inputs and their role. Public results contain only selected aggregates. No real user examples are included.

## Method

1. Discover public ATProto repositories containing Slovene-tagged posts.
2. Construct a seed list of Slovene-linked authors.
3. Resolve each author's PDS and collect the surviving public post history.
4. Apply post-level Slovene filtering using language tags, langid, and langdetect.
5. Manually validate the strict core, review groups, and false-negative sample.
6. Select the accepted decision groups and assemble the final corpus.
7. Compute aggregate community, interaction, linking, and linguistic analyses.

Three distinct merge stages should not be conflated:

- `merge_atproto_stores.py` merges collection SQLite stores.
- `merge_corpus_jsonl.py` merges and deduplicates filtered strict exports from collection runs.
- `build_final_sl_corpus.py` selects accepted decision groups and assembles the final corpus.

`link_domains` means extracted external link domains. Extraction covers rich-text link facets and external embed links; it is not limited to URLs literally present in post text.

## Repository contents

- `scripts/` contains the collection, filtering, validation, and analysis commands.
- `src/slosky/` contains the small shared modules used by those scripts.
- `results/` contains selected aggregate results and provenance manifests.
- `data/` documents restricted inputs; it contains no corpus data.
- `tools/annotate_samples.html` is the local manual-validation interface.
- `tests/` contains the existing synthetic unit tests.

## Reproducibility and provenance

This is a public research snapshot derived from the private working repository used for the study. Its eventual fresh Git history is not the original development history. The verified camera-ready source snapshot in the private repository is commit `d0a74e58c135b968c7f48dfd20c32b1ddf4b1b39`.

Some analyses cannot be rerun from this repository alone because their post-level inputs cannot be redistributed. [results/README.md](results/README.md) distinguishes public aggregate evidence from restricted supporting rows. The manifests in `results/provenance/` record checksums, stages, scripts, historical observations, current verification, and unresolved details where available.

The corrected public `anonymize_corpus.py` implements the intended privacy procedure. It did not generate the historical annotation input; that input and its checksum are recorded separately in `annotation_run_manifest.json`.

## Environment

The general Python dependencies are in `pyproject.toml`. The separate pinned environment used for linguistic annotation is recorded in `requirements-annotation.txt`.

## Citation

Nives Hüll. *A Community in Formation: Corpus Construction and Initial Analysis of Slovene Posts on Bluesky*. JT-DH 2026. Final publication details: TODO.

Licensing is not yet specified.


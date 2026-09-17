# SloSky

This repository contains the code and aggregate results for *A Community in Formation: Corpus Construction and Initial Analysis of Slovene Posts on Bluesky* (JT-DH 2026). The corpus is 141,013 Slovene posts from 432 authors, collected from Bluesky through ATProto and filtered using language metadata, automatic language identification, and manual validation.

**Paper:** [A Community in Formation: Corpus Construction and Initial Analysis of Slovene Posts on Bluesky](https://zenodo.org/records/22766147) (Zenodo).

**Presentation:** [JT-DH 2026 slides](presentation/slosky-jtdh-2026.pdf) (PDF).

## Data

The corpus itself is not distributed. This repository holds the code and the aggregate results used in the paper. [data/README.md](data/README.md) lists the main inputs used in the study.

## Method

1. Find public ATProto repositories with Slovene-tagged posts.
2. Build a seed list from the authors of those posts.
3. Resolve each author's PDS and collect their surviving public posts.
4. Filter posts by language tag, langid, and langdetect.
5. Manually validate the strict core, the review groups, and a false-negative sample.
6. Assemble the final corpus from the accepted decision groups.
7. Run the community, interaction, linking, and linguistic analyses.

Merging happens at three separate points: `merge_atproto_stores.py` merges the collection SQLite stores, `merge_corpus_jsonl.py` merges and deduplicates the filtered exports, and `build_final_sl_corpus.py` assembles the final corpus.

## Repository

- `scripts/` — collection, filtering, validation, and analysis commands
- `src/slosky/` — shared modules used by the scripts
- `results/` — aggregate results and provenance manifests
- `presentation/` — conference presentation slides
- `data/` — notes on the inputs; no corpus data
- `tools/annotate_samples.html` — the manual validation interface

## Running

Dependencies are in `pyproject.toml`. Linguistic annotation used a separate pinned environment, recorded in `requirements-annotation.txt`. Most scripts need the corpus data, which is not included here.

**Development note:** Claude Code and ChatGPT Codex were used in developing and revising the codebase, as well as for code review and repository maintenance.

## Reuse

Code is available under the [MIT License](LICENSE). The original slides and
aggregate results are available under [CC BY 4.0](CONTENT-LICENSE.md). The
underlying corpus is not distributed or licensed here.

## Citation

Hüll, N. (2026). *A Community in Formation: Corpus Construction and Initial Analysis of Slovene Posts on Bluesky*. Zenodo. https://zenodo.org/records/22766147

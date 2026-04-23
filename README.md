# slosky

Research code, outputs, and paper sources for a Slovene Bluesky corpus project.

What this repo already contains:

- a protocol-native collection pipeline for public Slovene Bluesky posts
- a validated paper corpus and derived analysis outputs
- the submitted JTDH 2026 paper sources

## Paper status

The paper was submitted to JTDH 2026 on `2026-04-23`.

- submission record: [paper/records/SUBMISSION-2026-04-23.md](/home/nives/Projekti/slosky/paper/records/SUBMISSION-2026-04-23.md)
- non-anonymous source: [paper/jtdh-manuscript-english.tex](/home/nives/Projekti/slosky/paper/jtdh-manuscript-english.tex)
- anonymous source: [paper/jtdh-manuscript-english-anonymous.tex](/home/nives/Projekti/slosky/paper/jtdh-manuscript-english-anonymous.tex)

## Structure

- `src/slosky/`: reusable package code
- `scripts/`: task-oriented pipeline and analysis scripts
- `outputs/`: generated corpora, samples, plots, and release files
- `paper/`: manuscript sources, template files, and figures
- `docs/`: short working notes and archived drafting material
- `tests/`: unit tests

## Notes

- `paper/build/` is local LaTeX build output and is ignored.
- `paper/references-pdfs/` is local reading material and is ignored.
- `outputs/running/` is mutable runtime state, not a stable release snapshot.

Start with [docs/START-HERE.md](/home/nives/Projekti/slosky/docs/START-HERE.md), [paper/README.md](/home/nives/Projekti/slosky/paper/README.md), and [outputs/README.md](/home/nives/Projekti/slosky/outputs/README.md).

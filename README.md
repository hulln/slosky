# slosky

Corpus and analysis code for a paper on public Slovene-language Bluesky posts.

## The corpus

**`outputs/final/final_sl_corpus.jsonl`** — 141,013 posts, 432 authors, Aug 2023 – Apr 2026.

This is the file. Everything else in this repo either built it, validates it, or analyses it.

## Paper materials

| What | Where |
|------|-------|
| Methodology section (ready to paste) | `docs/methodology-section-draft.md` |
| Validation results | `docs/validation-results.md` |
| Quality assurance summary | `docs/quality-assurance.md` |
| Language detector choice rationale | `docs/detector-choice.md` |
| Paper outline | `docs/paper-outline.md` |
| LaTeX paper | `paper/` |

## Key scripts

| Script | What it does |
|--------|-------------|
| `scripts/analyze_for_paper.py` | All four empirical analyses → `outputs/analysis/` |
| `scripts/export_strict_sl_corpus.py` | Filter SQLite → core + review JSONL |
| `scripts/build_final_sl_corpus.py` | Merge core + validated review → final corpus |
| `scripts/audit_final_corpus.py` | Structural QA of final corpus |
| `scripts/sample_false_negative_candidates.py` | Sample excluded posts for FN estimation |
| `scripts/backfill_seed_authors.py` | Collect full post history for seed authors |
| `scripts/live_collect_seed_authors.py` | Ongoing live collection |

## Outputs folder map

```
outputs/
├── final/          ← THE CORPUS — use final_sl_corpus.jsonl
├── analysis/       ← Paper analysis outputs (run analyze_for_paper.py)
├── validated/      ← Manual validation evidence (annotated CSVs, audit JSON)
├── samples/        ← Validation sample CSVs (input to annotation tool)
├── intermediate/   ← Source SQLite + intermediate processing files
└── running/        ← Live collection state (ignore for paper)
```

## Archived / legacy

Old scripts, ClickHouse code, and superseded docs are in:
- `scripts/legacy/`
- `docs/archive/`
- `queries/legacy/`
- `outputs/legacy/`

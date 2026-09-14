# Results and provenance

These are selected privacy-safe aggregates. “Restricted” means that the generating script is public but the supporting post- or author-level input is not redistributed.

| Paper result or claim | Public artefact | Generating script | Immediate input stage | Evidence status |
|---|---|---|---|---|
| Expanded store: 379,482 posts, 742 authors, May 2023–April 2026 | `provenance/expanded_store_summary.json` | `audit_atproto_store.py` | Expanded seed-author store | Aggregate public; store restricted |
| Final corpus composition and build identity | `provenance/final_corpus_provenance.json`, `validation/final_corpus_audit_exact_20260416.json` | `build_final_sl_corpus.py`, `audit_final_corpus.py` | Strict core and review exports | Aggregate public; rows restricted |
| Core and review decision-group sizes | `provenance/strict_core_export_summary.json`, `provenance/strict_review_export_summary.json` | `merge_corpus_jsonl.py` | Filtered collection-run exports | Aggregate public; rows restricted |
| Core and broad-review validation | `validation/strict_core_validation_summary.json`, `validation/strict_review_validation_summary.json` | `analyze_validation_samples.py` | Human-labelled samples | Summaries public; annotations restricted |
| Dedicated 50-post checks | `provenance/dedicated_validation_summary.json` | `sample_jsonl_by_decision.py`, `analyze_validation_samples.py` | Human-labelled decision samples | Summary public; annotations restricted |
| False-negative estimate | `provenance/false_negative_summary.json` | `sample_false_negative_candidates.py`, `analyze_validation_samples.py` | Expanded store, final URI set, human labels | Calculation public; rows restricted |
| Monthly growth and late-2024 break | `analysis/paper_growth.csv`, `analysis/community_summary.json`, `figures/figure-posts-per-month.png` | `analyze_for_paper.py`, `analyze_community_formation.py`, `plot_figure1.py` | Final corpus | Small cells suppressed; corpus restricted |
| Reply/original/quote structure | `analysis/paper_community.json`, `analysis/summary_interaction_stats.md` | `analyze_for_paper.py`, `analyze_interactional_structure.py` | Final corpus | Aggregate public; author profiles restricted |
| Posting hours and embed types | `analysis/paper_posting_hours.csv`, `analysis/paper_embed_types.csv` | `analyze_for_paper.py` | Final corpus | Aggregate public |
| Extracted external link-domain categories | `analysis/domain_category_summary.csv` | `analyze_topics_domains.py` | Final corpus link-domain field | Categories public; detailed domains/authors restricted |
| Language-tag and detector profile | `analysis/paper_codeswitching_langid.csv`, `analysis/paper_linguistic.json` | `analyze_for_paper.py` | Final corpus | Aggregate public |
| PDS and handle-type counts | `provenance/infrastructure_summary.json` | `analyze_for_paper.py` | Final corpus and PDS-resolution cache | Aggregate public; mappings restricted |
| SloSky linguistic profile | `analysis/slosky_linguistic_profile.json`, `provenance/annotation_run_manifest.json` | `annotate_release_corpus.py`, `analyze_linguistic_profile.py` | Historical pseudonymized corpus and annotation | Aggregates public; full text and annotation restricted |
| SUK 1.0 comparison | `analysis/suk_linguistic_profile.json`, `provenance/suk_provenance.json` | `analyze_linguistic_profile.py` | SUK 1.0 CoNLL-U release | Aggregate and exact source provenance public |

Detailed hashtag/domain rankings and author-concentration rows are intentionally absent. This limits independent inspection of a few low-count claims but avoids exposing individual community members.


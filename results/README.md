# Results

This directory contains aggregate outputs used in the paper. The underlying post- and author-level data are not included.

| Result | Output | Script | Input |
|---|---|---|---|
| Expanded store: 379,482 posts, 742 authors, May 2023–April 2026 | `provenance/expanded_store_summary.json` | `audit_atproto_store.py` | Expanded seed-author store |
| Final corpus composition and build identity | `provenance/final_corpus_provenance.json`, `validation/final_corpus_audit_exact_20260416.json` | `build_final_sl_corpus.py`, `audit_final_corpus.py` | Strict core and review exports |
| Core and review decision-group sizes | `provenance/strict_core_export_summary.json`, `provenance/strict_review_export_summary.json` | `merge_corpus_jsonl.py` | Filtered collection-run exports |
| Core and broad-review validation | `validation/strict_core_validation_summary.json`, `validation/strict_review_validation_summary.json` | `analyze_validation_samples.py` | Human-labelled samples |
| Dedicated 50-post checks | `provenance/dedicated_validation_summary.json` | `sample_jsonl_by_decision.py`, `analyze_validation_samples.py` | Human-labelled decision samples |
| False-negative estimate | `provenance/false_negative_summary.json` | `sample_false_negative_candidates.py`, `analyze_validation_samples.py` | Expanded store, final URI set, human labels |
| Monthly growth and late-2024 break | `analysis/paper_growth.csv`, `analysis/community_summary.json`, `figures/figure-posts-per-month.png` | `analyze_for_paper.py`, `analyze_community_formation.py`, `plot_figure1.py` | Final corpus |
| Reply/original/quote structure | `analysis/paper_community.json`, `analysis/summary_interaction_stats.md` | `analyze_for_paper.py`, `analyze_interactional_structure.py` | Final corpus |
| Posting hours and embed types | `analysis/paper_posting_hours.csv`, `analysis/paper_embed_types.csv` | `analyze_for_paper.py` | Final corpus |
| External link-domain categories | `analysis/domain_category_summary.csv` | `analyze_topics_domains.py` | Final corpus link-domain field |
| Language-tag and detector profile | `analysis/paper_codeswitching_langid.csv`, `analysis/paper_linguistic.json` | `analyze_for_paper.py` | Final corpus |
| PDS and handle-type counts | `provenance/infrastructure_summary.json` | `analyze_for_paper.py` | Final corpus and PDS-resolution cache |
| SloSky linguistic profile | `analysis/slosky_linguistic_profile.json`, `provenance/annotation_run_manifest.json` | `annotate_release_corpus.py`, `analyze_linguistic_profile.py` | Historical pseudonymized corpus and annotation |
| SUK 1.0 comparison | `analysis/suk_linguistic_profile.json`, `provenance/suk_provenance.json` | `analyze_linguistic_profile.py` | SUK 1.0 CoNLL-U release |

Apart from the SUK release, none of these inputs are distributed; see [../data/README.md](../data/README.md).

`link_domains` holds external link domains taken from rich-text link facets and external embeds, not only URLs written in the post text.

Monthly counts in the growth figure suppress small cells. Detailed hashtag and domain rankings and author-level tables are not included.

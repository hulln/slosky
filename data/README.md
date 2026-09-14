# Data

The corpus data are not included in this repository. The table below lists the main inputs used in the study and the scripts that produce or use them.

| Input | Produced by | Used by | Contents |
|---|---|---|---|
| Tagged-discovery SQLite stores | `backfill_atproto_posts.py`, `live_collect_atproto_posts.py` | `merge_atproto_stores.py`, `build_seed_author_list.py` | Tagged posts and account identifiers |
| Seed-author list | `build_seed_author_list.py` | `backfill_seed_authors.py`, `live_collect_seed_authors.py` | Author identifiers |
| Expanded seed-author store | collection and store-merge scripts | `export_strict_sl_corpus.py`, false-negative sampling | Post histories: text, identifiers, metadata |
| Strict core and review exports | `export_strict_sl_corpus.py`, `merge_corpus_jsonl.py` | validation and final assembly | Post rows with language signals and filtering decisions |
| Manual validation samples | sampling scripts, local annotation tool | `analyze_validation_samples.py` | Sampled posts with human labels and notes |
| Final corpus | `build_final_sl_corpus.py` | analysis scripts | Accepted post-level records |
| PDS-resolution cache | DID/PDS resolution during collection | collection and infrastructure analysis | Author-to-handle and hosting mappings |
| Historical pseudonymized corpus | historical `anonymize_corpus.py` | linguistic annotation | Pseudonyms, chronology, full post text |
| Annotated corpus | `annotate_release_corpus.py` | `analyze_linguistic_profile.py` | Token, lemma, and morphosyntactic annotation |
| SUK 1.0 CoNLL-U files | CLARIN.SI release | `analyze_linguistic_profile.py` | Reference-corpus annotation, distributed by CLARIN.SI |

No post text or account identifiers are distributed here.

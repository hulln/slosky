# Restricted inputs

The files below were used in the study but are not distributed. Their aggregate role is documented so that the boundary between public methodology and restricted evidence remains explicit.

| Stage or input | Produced by | Consumed by | Contents | Reason withheld |
|---|---|---|---|---|
| Tagged-discovery SQLite stores | `backfill_atproto_posts.py`, `live_collect_atproto_posts.py` | `merge_atproto_stores.py`, `build_seed_author_list.py` | Tagged posts and account identifiers | Post- and user-level social-media data |
| Seed-author list | `build_seed_author_list.py` | `backfill_seed_authors.py`, `live_collect_seed_authors.py` | Discovered author identifiers | Directly identifies corpus participants |
| Expanded seed-author store | collection and store-merge scripts | `export_strict_sl_corpus.py`, false-negative sampling | Public post histories, text, identifiers, metadata | Full-text and user-level corpus data |
| Strict core and review exports | `export_strict_sl_corpus.py`, `merge_corpus_jsonl.py` | validation and final assembly | Post rows with language signals and decisions | Contains identifiers and post text |
| Manual validation samples | sampling scripts and local annotation tool | `analyze_validation_samples.py` | Sampled posts, identifiers, human labels, notes | Posts and users remain identifiable |
| Final corpus | `build_final_sl_corpus.py` | paper analysis scripts | Accepted post-level records | Corpus redistribution is outside this release |
| PDS-resolution cache | DID/PDS resolution during collection | collection and infrastructure analysis | Author-to-handle and hosting resolution | Author-level mapping data |
| Historical pseudonymized corpus | historical `anonymize_corpus.py` | linguistic annotation | Stable pseudonyms, exact chronology, full post text | Pseudonymization does not prevent re-identification |
| Annotated corpus | `annotate_release_corpus.py` | `analyze_linguistic_profile.py` | Token, lemma, and morphosyntactic annotation over full text | Derived full-text resource |
| SUK 1.0 CoNLL-U files | CLARIN.SI release | `analyze_linguistic_profile.py` | Reference-corpus annotation | Distributed by its authoritative repository and licence |

No real post examples, DIDs, handles, or user text are included here.


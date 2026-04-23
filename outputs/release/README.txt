Slosky: A Pseudonymized Corpus of Slovene Bluesky Posts
=======================================================

This dataset contains 141,013 pseudonymized public Slovene-language posts
from the Bluesky social network, produced by 432 authors, spanning
August 2023 to April 2026.

The corpus was constructed through a multi-stage ATProto pipeline:
network-wide discovery of Slovene-tagged posts, full-history backfill
of discovered authors from their home Personal Data Servers, and
post-level language filtering using langid and langdetect.

For the full methodology and collection code, see the project repository:
https://github.com/hulln/slosky

The private deanonymization mapping is intentionally not part of the
public release bundle and should be stored outside this directory.


Files
-----

slosky_corpus_anon.jsonl
    The corpus in JSON Lines format (one JSON object per line).
    Recommended for programmatic use.

slosky_corpus_anon.csv
    The same corpus in CSV format.
    Note: fields containing commas are quoted per the CSV standard.


Fields
------

author_id           Pseudonymized author identifier (author_001 ... author_432)
post_id             Sequential post identifier (post_000001 ... post_141013)
created_at          Post creation timestamp (ISO 8601, UTC)
text                Post text (with @-mentions pseudonymized)
langs               Language tags as set by the post author
reply_flag          Whether the post is a reply (true/false)
quote_flag          Whether the post is a quote post (true/false)
embed_kind          Type of embedded media (null if none)
facet_count         Number of rich-text facets (links, mentions, etc.)
link_domains        Domains of external links (personal domains redacted)
decision            Corpus inclusion decision group
langid_label        Language label assigned by langid.py
langid_score        langid.py confidence score
langdetect_sl_prob  Probability of Slovene as assigned by langdetect


Decision groups
---------------

core_tag_supported           Author tagged post as Slovene + at least one
                             language model agrees (85,094 posts)
review_model_consensus_only  Both langid and langdetect classify as Slovene,
                             but no author tag (46,134 posts)
review_langid_only           Only langid classifies as Slovene (5,632 posts)
review_langdetect_only       Only langdetect classifies as Slovene (4,153 posts)


Pseudonymization
----------------

- Author identifiers (DIDs) replaced with sequential pseudonyms
- Post URIs replaced with sequential identifiers
- @-mentions in text replaced: corpus authors -> @author_NNN,
  external users -> @external_NNN (consistent across the corpus)
- User-owned custom domains in link_domains replaced with [personal-domain]
- No original DIDs, URIs, or Bluesky handles appear in this dataset


Notice and take-down
--------------------

Should you consider that this dataset contains material that is owned
by you and should therefore not be reproduced here, please contact the
dataset author. We will comply with legitimate requests by removing the
affected content from the next version of the corpus.


License
-------

CC-BY-SA 4.0

When using this dataset, please cite the accompanying paper (to be added if accepted).

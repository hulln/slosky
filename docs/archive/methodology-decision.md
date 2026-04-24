# Methodology Decision

This document states the current methodological decision for the paper corpus.

## Main decision

Use **one final corpus** as the main paper dataset.

Main dataset:

- [final_sl_corpus.jsonl](../../outputs/final/final_sl_corpus.jsonl)
- [final_sl_corpus.csv](../../outputs/final/final_sl_corpus.csv)
- `141,013` posts

Reason:

- the manually checked core sample was `300 / 300` acceptable as Slovene
- the review sample showed that some review subtypes are strong and worth keeping
- the review sample also showed that `tag-only` and `short tagged` rows are too noisy to merge automatically

## Unit of analysis

The unit of analysis is the **individual post**, judged by its visible text.

This means:

- we classify the post itself
- we do not reclassify an English post as Slovene only because it appears in a Slovene thread
- we do not reclassify a post as Slovene only because the author is a Slovene-linked user

Reason:

- the paper is about a **language corpus of posts**
- post-level language must therefore be visible in the post itself
- thread context is sociologically interesting, but it is a different analytical layer

## Inclusion rule for the main corpus

A post belongs in the main corpus if:

- it is part of the recovered historical/live collection
- and it belongs to one of the included final decision groups

In practice, the final corpus includes:

- `core_tag_supported`
- `review_model_consensus_only`
- `review_langid_only`
- `review_langdetect_only`

Current counts:

- `core_tag_supported`: `85,094`
- `review_model_consensus_only`: `46,134`
- `review_langid_only`: `5,632`
- `review_langdetect_only`: `4,153`

This rule keeps the strongest validated review subtypes while still excluding the weakest ones.

## Treatment of mixed-language posts

Mixed-language posts are **included** if they contain meaningful Slovene content.

Reason:

- code-switching is part of real online language use
- excluding all mixed posts would erase an important feature of social-media Slovene

## Treatment of blank, emoji-only, link-only, and very short posts

These are **not** suitable for the main language corpus unless they contain enough visible Slovene text.

Examples that should stay out of the main corpus:

- blank posts
- emoji-only posts
- emoticon-only posts
- link-only posts
- very short posts where language cannot be judged reliably

Reason:

- they do not provide enough linguistic material for a defensible language decision

## Treatment of non-Slovene posts by Slovene-linked users

These are **excluded** from the main corpus.

Reason:

- a Slovene user can still post in English, Croatian, Serbian, or some other language
- the paper corpus is a corpus of Slovene posts, not a corpus of Slovene users

## Role of excluded review groups

The excluded review groups are **auxiliary material**, not part of the final paper corpus.

Use it for:

- error analysis
- discussion of edge cases
- future expansion work

Do not merge these groups wholesale into the main dataset.

## Important nuance

The review sample suggests that some subtypes of review posts are actually very promising.

In particular:

- model-consensus-only posts performed very well in the reviewed sample
- the single-model-only groups also looked promising in the reviewed sample
- tag-only and short-tagged posts were much less reliable

For the current paper, the main corpus is therefore:

- **one final corpus that merges strict core with model-supported review additions**

The excluded groups remain useful for:

- error analysis
- limitations discussion
- future refinement

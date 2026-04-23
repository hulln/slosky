# Methodology Section Draft

This text is a paper-ready draft for the methodology part of the corpus paper.

## Corpus Construction

The corpus was built as a layered ATProto workflow rather than as a single tag-based export. First, Slovene-linked accounts were discovered through public Bluesky posts whose `langs` field contained `sl` or an `sl-*` subtag. Second, for each discovered account, the full surviving public post history was recovered through ATProto repository access. This historical recovery used DID-based PDS resolution, so collection was not restricted to `bsky.social` and could include accounts hosted on other PDSes. Third, the recovered posts were filtered conservatively to separate a high-precision core corpus from a weaker review layer.

## Unit of Analysis

The unit of analysis is the individual post as visible to the public at the time of collection. Language classification was based on the visible text of the post itself, not on the language of the surrounding thread and not on the presumed identity of the author. This means that an English reply inside an otherwise Slovene discussion was treated as English and excluded from the main Slovene corpus. This decision was made because the aim of the dataset is to model Slovene posts, not Slovene users or Slovene conversational spaces.

## Main Corpus Inclusion Rule

The final corpus uses a validated inclusion rule. A post was included if it belonged to one of four decision groups: `core_tag_supported`, `review_model_consensus_only`, `review_langid_only`, or `review_langdetect_only`. In practice, this means that the final dataset includes both high-confidence tagged Slovene posts and additional model-supported Slovene posts recovered from the full histories of discovered Slovene-linked accounts. Posts that were tagged as Slovene but lacked model support, as well as posts that were too short to classify reliably, were not merged into the final corpus.

## Excluded Review Layer

The excluded review layer contains weaker or noisier cases that were preserved for error analysis and future refinement rather than merged into the final paper dataset. This layer consists mainly of two groups: posts tagged as Slovene but lacking model support, and very short tagged posts. These groups were retained as auxiliary material because they contain both genuine Slovene posts and substantial noise.

## Treatment of Edge Cases

Mixed-language posts were included in the main corpus only when they contained meaningful Slovene content. This decision keeps naturally occurring code-switching in the dataset while excluding posts that are effectively non-Slovene. Blank posts, emoji-only posts, emoticon-only posts, link-only posts, and very short posts with too little lexical material were treated as undeterminable and excluded from the main corpus. Posts by Slovene-linked users that were clearly in English or another language were likewise excluded from the main corpus.

## Validation

The strict core corpus was evaluated with a random 300-post manual validation sample. All 300 sampled posts were judged acceptable as Slovene. The review layer was evaluated with a separate random 300-post sample. In that sample, 214 posts were labelled `Slovene-dominant`, 2 `Mixed-with-Slovene`, 40 `Not-Slovene`, and 44 `Undeterminable/too-short`. A more detailed breakdown showed that the model-supported review groups performed strongly, whereas the tag-only and short-tagged groups introduced most of the noise. This made it possible to define one larger final corpus without merging the entire review layer wholesale.

## Methodological Consequence

On the basis of this validation, the paper can use one defensible final dataset: a corpus composed of the strict core plus the model-supported review additions. The excluded review groups should be discussed separately as an auxiliary resource that captures systematic error cases and possible future refinement targets. This framing allows the paper to make a precise claim: the project yields a high-precision corpus of currently recoverable public Slovene Bluesky posts from discovered Slovene-linked accounts, while also documenting the limits of language-tag and language-model based recovery.

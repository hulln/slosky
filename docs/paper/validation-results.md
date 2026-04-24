# Validation Results

## Strict Core Sample

Source file:

- [strict_core_validation_sample.csv](../../outputs/samples/strict_core_validation_sample.csv)
- annotated copy: [strict_core_validation_sample_annotated.csv](../../outputs/validated/strict_core_validation_sample_annotated.csv)
- reproducible summary: [strict_core_validation_summary.json](../../outputs/validated/strict_core_validation_summary.json)

Manual review status:

- reviewed by hand
- `300 / 300` sampled posts judged acceptable as Slovene
- no observed false positives in the reviewed core sample

Working interpretation:

- estimated precision of the strict core sample is effectively `100%` on this reviewed sample
- this strongly supports using the strict core as the main paper dataset

Reproducibility note:

- the row-by-row annotated CSV is preserved
- the current summary can be regenerated from the preserved annotations

## Strict Review Sample

Source file:

- [strict_review_validation_sample.csv](../../outputs/samples/strict_review_validation_sample.csv)
- annotated copy: [strict_review_validation_sample_annotated.csv](../../outputs/validated/strict_review_validation_sample_annotated.csv)
- reproducible summary: [strict_review_validation_summary.json](../../outputs/validated/strict_review_validation_summary.json)

Manual review status:

- reviewed by hand
- `214 / 300` labelled `Slovene-dominant`
- `2 / 300` labelled `Mixed-with-Slovene`
- `40 / 300` labelled `Not-Slovene`
- `44 / 300` labelled `Undeterminable/too-short`

Interpretation:

- acceptable Slovene posts in the review sample: `216 / 300` (`72.0%`)
- acceptable Slovene posts among non-undeterminable review rows: `216 / 256` (`84.4%`)
- the review set is therefore too noisy to merge wholesale into the main paper corpus

More precise pattern:

- `review_model_consensus_only`: `109 / 109` acceptable as Slovene in the sample
- `review_langid_only`: `11 / 11` acceptable as Slovene in the sample
- `review_langdetect_only`: `10 / 10` acceptable as Slovene in the sample
- `review_tag_only`: mixed and unreliable in the sample
- `review_short_tagged`: mixed, with many blank, emoji-only, link-only, or context-dependent rows

Working interpretation:

- model-supported review rows look promising for inclusion
- `tag-only` and `short tagged` review rows should not be merged automatically
- the final paper dataset can therefore merge the strict core with the validated stronger review groups while keeping the noisy review groups as auxiliary/error-analysis material

Observed edge cases:

- blank posts
- emoji-only or emoticon-only posts
- link-only or near-link-only posts
- mixed Slovene-English posts
- posts from Slovene-linked accounts that were actually in English or another South Slavic language

## Optional Single-Model Samples

Source files:

- [optional_langid_only_validation_sample.csv](../../outputs/validated/optional_langid_only_validation_sample.csv)
- [optional_langid_only_validation_sample_annotated.csv](../../outputs/validated/optional_langid_only_validation_sample_annotated.csv)
- [optional_langdetect_only_validation_sample.csv](../../outputs/validated/optional_langdetect_only_validation_sample.csv)
- [optional_langdetect_only_validation_sample_annotated.csv](../../outputs/validated/optional_langdetect_only_validation_sample_annotated.csv)

Manual review status:

- `review_langid_only`: `49 / 50` labelled `Slovene-dominant`, `1 / 50` labelled `Mixed-with-Slovene`
- `review_langdetect_only`: `49 / 50` labelled `Slovene-dominant`, `1 / 50` labelled `Not-Slovene`

Interpretation:

- `review_langid_only`: `50 / 50` acceptable as Slovene if mixed-with-Slovene is counted as acceptable
- `review_langdetect_only`: `49 / 50` acceptable as Slovene
- these results support keeping both smaller single-model groups in the final corpus
- after these checks, there is no strong methodological need for additional routine annotation before writing

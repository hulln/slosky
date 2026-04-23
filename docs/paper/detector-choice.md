# Detector Choice

This document explains, in the shortest useful form, how to justify the detector choice in the paper.

## Short version

Use this as the main answer:

- the final paper corpus uses `langid` + `langdetect`
- `fastText` and `Lingua` were also evaluated as alternatives
- on the manually validated comparable sample (`477` rows), all four detectors had the same observed precision (`1.0`)
- the difference was recall:
  - `langid`: `0.885`
  - `langdetect`: `0.8496`
  - `fastText`: `0.5686`
  - `Lingua`: `0.8761`
- for the strict pairwise rule:
  - `langid + langdetect`: recall `0.7832`
  - `fastText + Lingua`: recall `0.542`

So the simplest justification is:

> We retained `langid` and `langdetect` for the final corpus because, on our manually validated sample, they matched the alternative detectors in observed precision while recovering more acceptable Slovene posts. `fastText` and `Lingua` were kept as comparison tools, but they did not improve the validated corpus build enough to justify replacing the existing rule.

## If you want only one paragraph

You do not need to discuss all four detectors at length in the paper. One short paragraph is enough:

> In addition to the detectors used in the final build (`langid` and `langdetect`), we also evaluated `fastText` and `Lingua` on the manually validated sample. On the comparable subset of 477 rows, all four detectors showed the same observed precision in this sample, so the relevant difference was recall. `langid` and `langdetect` recovered more acceptable Slovene posts than `fastText`, while `Lingua` did not provide a clear enough improvement to justify replacing the existing validated workflow. We therefore retained the original detector pair for the final corpus and kept the other detectors as comparison tools.

## Why detector choice matters

The corpus contains short social-media posts, mixed-language posts, and posts from users who may write in Slovene, English, or neighboring South Slavic languages. No single language detector can be assumed to be perfect in that setting. Detector choice therefore has to be justified both conceptually and empirically.

## The four detectors considered

The project now keeps results from four detectors:

- `fastText`
- `Lingua`
- `langid`
- `langdetect`

These are not all used equally in the final corpus decision, but they are all useful for comparison and cross-checking.

## Why `fastText` is kept

`fastText` is kept as the primary broad multilingual baseline.

Reason:

- it is an established multilingual language-identification model
- it covers a very large language inventory
- the official `lid.176` models are widely used as a practical baseline
- the official documentation states that `lid.176.bin` is slightly more accurate than the compressed `lid.176.ftz`, so the project now prefers the `bin` model

Practical interpretation:

- `fastText` is valuable as a broad multilingual check
- it is not assumed to be perfect on very short Slovene posts

## Why `Lingua` is kept

`Lingua` is kept as a comparison detector because it is especially suitable for short text.

Reason:

- it is designed to work well on short text snippets
- it supports confidence-based output
- it performs useful disambiguation for short social-media posts

Practical interpretation:

- `Lingua` is particularly helpful where broad multilingual models can confuse Slovene with nearby South Slavic languages

## Why `langid` and `langdetect` remain the build pair

The current corpus build still uses `langid` and `langdetect`.

Reason:

- both detectors are already integrated and reproducible in the current pipeline
- they achieved the strongest recall among the validated detectors without losing observed precision in the comparison sample
- keeping their outputs in exported rows makes later auditing easier

Practical interpretation:

- `langid` and `langdetect` are the detector pair used for the current corpus build
- `fastText` and `Lingua` are retained as comparison tools rather than as the adopted build rule

## Sample-based comparison

The file below records a four-detector comparison on the manually validated samples:

- [detector_comparison_summary.json](/home/nives/Projekti/slosky/outputs/validated/detector_comparison_summary.json)

At the current thresholds and minimum-text rule, all four detectors were clean on the manually judged comparable rows in this sample. The main difference was recall, not observed precision.

Interpretation:

- `fastText` was the most conservative of the four
- `Lingua`, `langid`, and `langdetect` each recovered more acceptable Slovene rows in the sample
- the `fastText + Lingua` consensus was strict and clean, but conservative

## Current methodological decision

The detector comparison is useful, but it does **not** justify replacing the current validated corpus build.

Reason:

- on the current validated sample, `fastText` was the most conservative detector
- the `fastText + Lingua` pair did not show a precision advantage over the already used detectors in this sample
- `langid` and `langdetect` achieved higher recall on the manually reviewed comparable rows while keeping the same observed precision in this comparison

So the current methodological position is:

- keep the existing validated corpus as the main paper dataset
- keep `fastText`, `Lingua`, `langid`, and `langdetect` in the project as comparison tools
- describe `fastText + Lingua` as a considered alternative rather than as the adopted final corpus rule

This is easier to defend in the paper than forcing a detector pair that did not improve the validated corpus build for this dataset.

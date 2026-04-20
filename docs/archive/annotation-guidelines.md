# Annotation Guidelines

Use these labels for both current 300-post validation files:

- the strict core sample
- the strict review sample

## Labels

- `Slovene-dominant`
  - The post is primarily in Slovene, even if it contains names, URLs, hashtags, or short foreign insertions.
- `Mixed-with-Slovene`
  - The post contains meaningful Slovene content but also substantial non-Slovene material.
- `Not-Slovene`
  - The post is not meaningfully in Slovene.
- `Undeterminable/too-short`
  - The post is too short, too noisy, or too context-dependent for a reliable language judgement.

## Rules

- Judge the visible post text only.
- Ignore the `langs` tag while annotating.
- Keep code-switching separate from pure Slovene.
- Do not overuse `Undeterminable/too-short`. Use it only when a decision would be guesswork.
- When in doubt between `Slovene-dominant` and `Mixed-with-Slovene`, ask whether a reader would describe the post as mainly Slovene.

## Precision metric

Report:

`(Slovene-dominant + Mixed-with-Slovene) / all non-undeterminable sampled posts`

Also report the share of `Undeterminable/too-short` posts separately.

## Current use

Right now, the main purpose of annotation is:

- to check how clean the strict core really is
- to understand what kinds of posts ended up in the review bucket

Recommended workflow:

1. Open [annotate_samples.html](/home/nives/Projekti/slosky/tools/annotate_samples.html) in a browser.
2. Load [strict_core_validation_sample.csv](/home/nives/Projekti/slosky/outputs/samples/strict_core_validation_sample.csv) first.
3. Export the annotated file.
4. Then do the same for [strict_review_validation_sample.csv](/home/nives/Projekti/slosky/outputs/samples/strict_review_validation_sample.csv).

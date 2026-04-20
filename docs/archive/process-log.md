# Process Log

This file records the main project decisions in simple chronological order.

## 1. Initial pilot

- An early pilot used a late public warehouse snapshot.
- That pilot was useful for testing queries and scripts.
- It was not good enough for the final paper because it did not reach back to early Bluesky history.
- This material is archived under `docs/archive/`, `scripts/legacy/`, `queries/legacy/`, and `outputs/legacy/`.

## 2. Protocol-native collection

- The project moved to ATProto-based collection.
- Historical discovery used public Bluesky/ATProto APIs.
- Live collection was added so the corpus can continue growing after the historical snapshot.

## 3. Multi-PDS correction

- An early version wrongly assumed `bsky.social` for repo access.
- This was corrected by resolving each DID to its real PDS through DID/PLC lookup.
- This means the workflow can include Bluesky accounts hosted on other PDSes.

## 4. Seed-author historical expansion

- Slovene-linked accounts were first discovered through Slovene-tagged posts.
- Then the full surviving public post histories of those discovered accounts were recovered.
- This produced the large historical author-history store.

## 5. Strict split into core and review

- The recovered post store was filtered conservatively.
- A high-precision `core` set was separated from a broader `review` set.
- This was done to avoid treating weak or noisy Slovene signals as automatically trustworthy.

## 6. Manual validation

- The strict core sample was checked manually.
- Result: `300 / 300` acceptable as Slovene.
- The strict review sample was also checked manually.
- Result: many good Slovene posts were present, but the review set was too noisy to merge wholesale.

## 7. Current final decision

- The project now uses one final corpus built from:
  - `core_tag_supported`
  - `review_model_consensus_only`
  - `review_langid_only`
  - `review_langdetect_only`
- The noisy review groups are excluded from the final corpus:
  - `review_tag_only`
  - `review_short_tagged`

## 8. Why this final decision was made

- The core sample was completely clean in the manual check.
- In the review sample, the model-supported groups looked very strong.
- The noisy cases came mostly from tag-only and short-tagged rows.
- This makes it possible to keep one larger final corpus without blindly accepting the weakest review material.

## 9. Four-detector comparison

- A later comparison step added `fastText` and `Lingua` to the project.
- All four detectors were compared on the manually validated samples:
  - `fastText`
  - `Lingua`
  - `langid`
  - `langdetect`
- This comparison was documented in [detector-choice.md](/home/nives/Projekti/slosky/docs/detector-choice.md).

## 10. Outcome of the four-detector comparison

- The comparison did not show a precision gain that justified replacing the current validated corpus build.
- `fastText` in particular was more conservative than the already used detectors on the validated comparable rows.
- Therefore the existing validated final corpus remained the current official paper dataset.
- The `fastText`/`Lingua` work remains useful as documented comparison and future experimentation, but not as the adopted main corpus rule.

## 11. Optional follow-up validation

- Two extra small validation samples were annotated for the included single-model groups.
- `review_langid_only` validated strongly in this follow-up sample.
- `review_langdetect_only` also validated strongly, with one observed non-Slovene row in the sample.
- This reduced the need for further routine manual annotation before writing.

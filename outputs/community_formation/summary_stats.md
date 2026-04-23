# Community Formation Metadata Analysis

Input corpus: `outputs/final/final_sl_corpus.jsonl`
Rows analysed: 141,013
Unique authors: 432
UTC date range: 2023-08-09T13:51:59.646000+00:00 to 2026-04-16T08:04:41.860109+00:00
Partial-month handling: Final observed month 2026-04 is partial (last timestamp: 2026-04-16T08:04:41.860109+00:00); it is flagged and excluded from retention windows, monthly period medians, and tests.

## October-November 2024 Break

| Metric | October 2024 | November 2024 | Growth |
|---|---:|---:|---:|
| posts_total | 31 | 5,984 | 19203.2% |
| authors_active | 13 | 196 | 1407.7% |
| authors_new | 8 | 172 |  |

## Period Comparison

Monthly medians exclude the partial final month when one is detected; total posts and total active authors describe all observed rows in each period.

| period                    | total_posts | total_active_authors | median_monthly_posts_total | median_monthly_authors_active | median_posts_per_active_author | monthly_medians_exclude_partial_final_month |
| ------------------------- | ----------- | -------------------- | -------------------------- | ----------------------------- | ------------------------------ | ------------------------------------------- |
| pre_surge_through_2024_10 | 178         | 30                   | 10                         | 3                             | 2.33333                        | True                                        |
| post_surge_from_2024_11   | 140835      | 429                  | 7958                       | 210                           | 37.7286                        | True                                        |

## Mann-Whitney Tests

Tests compare complete monthly observations before November 2024 with complete monthly observations from November 2024 onward. Cliff's delta is positive when post-surge monthly values tend to be larger.

| metric                  | n_pre_months | n_post_months | median_pre | median_post | mann_whitney_u_post_vs_pre | p_value_two_sided | cliffs_delta_post_vs_pre |
| ----------------------- | ------------ | ------------- | ---------- | ----------- | -------------------------- | ----------------- | ------------------------ |
| posts_total             | 15           | 17            | 10         | 7958        | 255                        | 1.60909e-06       | 1                        |
| authors_active          | 15           | 17            | 3          | 210         | 255                        | 1.52278e-06       | 1                        |
| posts_per_active_author | 15           | 17            | 2.33333    | 37.7286     | 255                        | 1.58104e-06       | 1                        |

## Interpretation

- The monthly metadata show a clear discontinuity in late 2024: posts rise from 31 in October 2024 to 5,984 in November 2024, while active authors rise from 13 to 196.
- The November 2024 increase is not only a posting-volume effect: 172 authors first appear in the included corpus in November, followed by 50 in December.
- After the break, the median complete monthly post count is 7,958, compared with 10 before November 2024.
- Monthly active-author counts are also higher after November 2024; the Mann-Whitney comparison gives Cliff's delta 1.00 (two-sided p=1.52e-06).
- The posts-per-active-author comparison is useful as a caution: it tests whether the change reflects only more participants or also a change in monthly posting intensity. In this corpus, Cliff's delta is 1.00 (two-sided p=1.58e-06).
- The retention metrics should be read descriptively rather than causally: they show which first-seen author cohorts reappear in later months, but they do not explain why authors joined or remained active.
- Final observed month 2026-04 is partial (last timestamp: 2026-04-16T08:04:41.860109+00:00); it is flagged and excluded from retention windows, monthly period medians, and tests.

## Suggested Paper Paragraph

A metadata-only monthly analysis supports reading the corpus as a record of community formation rather than as simple post accumulation. Before November 2024, the median monthly volume was 10 posts by 3 active authors; from November 2024 onward, excluding the partial final month from monthly medians, the corresponding medians were 7,958 posts and 210 active authors. The clearest break occurs between October and November 2024, when posts increased from 31 to 5,984 and active authors from 13 to 196. Mann-Whitney tests on complete months indicate large post-surge differences for both monthly post volume (Cliff's delta=1.00, p=1.61e-06) and active-author counts (Cliff's delta=1.00, p=1.52e-06). These results do not establish the cause of the increase, but they show that late 2024 marks a shift in both participation and activity in the recoverable Slovene Bluesky corpus.

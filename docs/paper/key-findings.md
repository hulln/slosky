# Key Findings

All numbers verified from `outputs/final/final_sl_corpus.jsonl` (141,013 posts, 432 authors).
Analysis script: `scripts/analyze_for_paper.py`.
Full author table: `outputs/analysis/paper_authors.csv`.

---

## 1. One clear late-2024 surge, not two inferred waves

- **November 2024**: 31 posts in Oct → 5,984 in Nov (×193), the clearest structural break in the corpus.
- By month of first included post, `172` authors first appear in November 2024 and `50` in December 2024.
- The corpus still contains `30` authors whose first included post predates November 2024, with the earliest included post in August 2023.

## 2. Extremely dialogic community

- **68.3% of all posts are replies** (96,278/141,013).
- Original posts: 29.4%. Non-reply quote posts: 2.3%.
- Median reply: 77 chars. Median original post: 114 chars.

## 3. Broadcaster/conversationalist split

- Institutional accounts post exclusively original content (0% reply rate):
  - `sportklubslovenija.bsky.social` — 1,918 posts, 0% replies
  - `supdeska.bsky.social` — 381 posts, 0% replies
  - `alpeadriagreen.bsky.social` — 184 posts, 0% replies
  - `n1info.si` — 2,560 posts, **0.3%** replies (news outlet)
- Many highly active individual users fall in the 75–99% reply-rate range.
- This split inflates the "original posts" count; among individuals the community is even more conversational.

## 4. Extreme author concentration

- Gini coefficient: **0.82**
- Top 1% of authors (4 users) → 18.2% of posts
- Top 10% (43 users) → 69.6% of posts
- **22 authors = 50% of the entire corpus**
- Median author: **35 posts**

## 5. Posting time confirms Slovenian timezone

- Morning peak: 09:00–10:00 UTC (= 10–11 AM CET / 11 AM–12 PM CEST)
- Evening peak: 18:00–19:00 UTC (= 7–8 PM CET / 8–9 PM CEST)
- Near-zero activity 01:00–04:00 UTC
- Consistent with Central European timezone users

## 6. SUP paddleboarding is the clearest hashtag subgroup

- #supslovenija (230), #supdeska (187), #aquamarina (177) — all SUP-related
- This is a real subgroup, not noise

## 7. GIF hosting is the single most-linked external domain

- `media.tenor.com` is the most linked domain (2,613 posts)
- Reflects informal, conversational register
- Top news sources: n1info.si (2,548), rtvslo.si (702)
- Tech news: tehnozvezdje.si (1,236)

## 8. Embed breakdown

- 77.8% plain text
- 11.2% external link cards
- 8.0% images
- 2.3% quote-posts
- 0.5% video (very rare)

## 9. Infrastructure: mostly default Bluesky setup, with smaller handle/hosting minorities

- 423/432 authors hosted on `*.host.bsky.network`
- 9 authors hosted on `eurosky.social`
- Handle types:
  - 395 `*.bsky.social`
  - 30 user-owned custom domains (6.9% of authors, 9.4% of posts)
  - 7 `*.eurosky.social` subdomains
- Notable custom domains: n1info.si, drfilomena.com, fletni-stajerc.si, oblachek.eu

## 10. Code-switching: author tags ≠ text content

- 41.4% of posts tagged sl+en by authors
- But langid detects English in only 278 posts
- Most sl+en tagging is a Bluesky UI effect (English app settings), not actual code-switching
- langid detects Croatian (4,506) and Bosnian (2,285) > English — South Slavic cross-label confusion

## 11. False-negative rate: ~8.5%

- 200-post sample of excluded no-tag posts from known authors, after the project minimum-text filter: 17 Slovenian (8.5%)
- Eligible comparable pool size: 97,968 posts
- Estimated ~8,300 missed Slovenian posts from known authors (~6% gap)
- This estimate applies only to the comparable excluded no-tag pool, not to all excluded posts

## 12. Corpus precision: very high, but not literally perfect in every included subgroup

- 300/300 core posts manually validated as Slovenian
- Review-model consensus rows: 109/109 acceptable in the main review sample
- `review_langid_only`: 50/50 acceptable in the follow-up sample
- `review_langdetect_only`: 49/50 acceptable in the follow-up sample

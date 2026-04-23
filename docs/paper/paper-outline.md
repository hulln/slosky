# Paper Outline

## Title

**Building a Corpus of Public Slovene Bluesky Posts: Data Collection, Validation, and First Observations on Interaction and Multilinguality**

## Research questions

1. Can a usable Slovene Bluesky corpus be built from public ATProto/Bluesky data using language tags plus validation?
2. How precise is `langs=sl`, and what kinds of Slovene posts does it miss?
3. How far can a multi-PDS ATProto workflow push Slovene-post recovery beyond a tag-only corpus?
4. What interactional and multilingual patterns are visible in the resulting Slovene Bluesky corpus?

## Section structure

### 1. Introduction

- Why Bluesky matters as a new social-media corpus source
- Why Slovene is worth studying specifically
- Paper contribution: corpus construction, validation, and first observations

### 2. Related Work

- Slovene user-generated corpora and social-media work
- Bluesky/ATProto as a data source
- Language-tagging and corpus construction limitations

### 3. Data Source and Extraction

- protocol-native ATProto source choice
- `listReposByCollection` + multi-PDS `listRecords` for historical recovery
- `subscribeRepos` for live continuation
- `app.bsky.feed.post` only
- tagged discovery, seed-author expansion, and strict consensus filtering
- exported fields, local SQLite storage, and normalization

### 4. Validation

- 300-post precision sample
- separate review-bucket sample
- annotation labels
- precision formula
- discussion of what the strict core excludes

### 5. Empirical Analysis

- brief corpus profile needed for the analysis
- reply/original/quote structure
- mentions, links, hashtags, emoji
- multilinguality and code-switching patterns
- differences between more dialogic and more broadcast-like posts

### 6. Discussion

- what these patterns suggest about Slovene use on Bluesky
- what is platform-specific and what may generalise
- what the corpus enables for future work

### 7. Limitations and Ethics

- currently recoverable public content only
- deleted posts excluded
- public-data limitations
- `langs` is helpful but imperfect
- no raw-text dump release

### 8. Conclusion

- what the corpus enables
- what remains missing
- next-step expansion path

SELECT
  min(bluesky_ts) AS first_post_ts,
  max(bluesky_ts) AS last_post_ts,
  count() AS total_posts,
  uniqExact(data.did) AS unique_authors
FROM {{table}}
WHERE kind = 'commit'
  AND data.commit.collection = 'app.bsky.feed.post'
  AND match(
    ifNull(toJSONString(data.commit.record.langs), ''),
    '(^|\\[|,)"sl(-[^"]+)?"(,|\\])'
  )
FORMAT JSONCompact


SELECT
  concat(
    'at://',
    toString(data.did),
    '/',
    toString(data.commit.collection),
    '/',
    toString(data.commit.rkey)
  ) AS uri,
  toString(data.did) AS author_did,
  toString(bluesky_ts) AS source_bluesky_ts,
  toJSONString(data) AS event_json
FROM {{table}}
WHERE kind = 'commit'
  AND data.commit.collection = 'app.bsky.feed.post'
  AND bluesky_ts >= toDateTime64('{{start_ts}}', 6)
  AND bluesky_ts < toDateTime64('{{end_ts}}', 6)
  AND match(
    ifNull(toJSONString(data.commit.record.langs), ''),
    '(^|\\[|,)"sl(-[^"]+)?"(,|\\])'
  )
{{limit_clause}}
FORMAT JSONEachRow

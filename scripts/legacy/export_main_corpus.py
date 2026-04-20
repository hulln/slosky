#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.clickhouse import ClickHouseClient, render_sql
from slosky.normalize import normalize_export_row


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the main Slovene Bluesky corpus.")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL path")
    parser.add_argument("--table", default="bluesky.bluesky")
    parser.add_argument("--start-ts", default="2024-12-23 14:00:00")
    parser.add_argument("--end-ts", default="2025-06-16 15:20:00")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--batch-days",
        type=int,
        default=1,
        help="If --limit is omitted, split the export into windows this many days wide.",
    )
    parser.add_argument("--sql", type=Path, default=Path("queries/export_main_corpus.sql"))
    parser.add_argument("--endpoint", default="https://sql-clickhouse.clickhouse.com/")
    parser.add_argument("--user", default="demo")
    parser.add_argument("--password-env", default="CLICKHOUSE_PASSWORD")
    parser.add_argument(
        "--source-dataset",
        default="clickhouse:bluesky.bluesky",
        help="Stored in each exported row for reproducibility",
    )
    args = parser.parse_args()

    client = ClickHouseClient(
        endpoint=args.endpoint,
        user=args.user,
        password=os.environ.get(args.password_env, ""),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    batch_summaries: list[dict[str, str | int]] = []

    start_dt = datetime.strptime(args.start_ts, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(args.end_ts, "%Y-%m-%d %H:%M:%S")
    if end_dt <= start_dt:
        raise SystemExit("--end-ts must be later than --start-ts")

    def iter_batches() -> list[tuple[str, str, str]]:
        if args.limit:
            return [(args.start_ts, args.end_ts, f"LIMIT {args.limit}")]

        windows: list[tuple[str, str, str]] = []
        current = start_dt
        delta = timedelta(days=max(args.batch_days, 1))
        while current < end_dt:
            next_dt = min(current + delta, end_dt)
            windows.append(
                (
                    current.strftime("%Y-%m-%d %H:%M:%S"),
                    next_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "",
                )
            )
            current = next_dt
        return windows

    with args.output.open("w", encoding="utf-8") as handle:
        for batch_start, batch_end, limit_clause in iter_batches():
            query = render_sql(
                args.sql,
                {
                    "table": args.table,
                    "start_ts": batch_start,
                    "end_ts": batch_end,
                    "limit_clause": limit_clause,
                },
            )
            batch_count = 0
            for row in client.iter_json_each_row(query):
                normalized = normalize_export_row(row, source_dataset=args.source_dataset)
                handle.write(json.dumps(normalized, ensure_ascii=False) + "\n")
                count += 1
                batch_count += 1
            batch_summaries.append(
                {
                    "start_ts": batch_start,
                    "end_ts": batch_end,
                    "rows_written": batch_count,
                }
            )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows_written": count,
        "table": args.table,
        "start_ts": args.start_ts,
        "end_ts": args.end_ts,
        "source_dataset": args.source_dataset,
        "sql_template": str(args.sql),
        "batch_days": args.batch_days if not args.limit else None,
        "batches": batch_summaries,
    }
    args.output.with_suffix(args.output.suffix + ".meta.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

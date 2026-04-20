#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.clickhouse import ClickHouseClient, render_sql


def parse_params(values: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Invalid --param value: {value!r}")
        key, item = value.split("=", 1)
        params[key] = item
    return params


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a ClickHouse SQL template.")
    parser.add_argument("--sql", type=Path, required=True, help="Path to SQL template")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Template substitution in key=value form",
    )
    parser.add_argument("--endpoint", default="https://sql-clickhouse.clickhouse.com/")
    parser.add_argument("--user", default="demo")
    parser.add_argument("--password-env", default="CLICKHOUSE_PASSWORD")
    parser.add_argument("--output", type=Path, help="Optional output file")
    args = parser.parse_args()

    params = parse_params(args.param)
    query = render_sql(args.sql, params)
    client = ClickHouseClient(
        endpoint=args.endpoint,
        user=args.user,
        password=os.environ.get(args.password_env, ""),
    )
    result = client.execute_bytes(query)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(result)
    else:
        sys.stdout.buffer.write(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

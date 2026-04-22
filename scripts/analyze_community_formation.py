#!/usr/bin/env python3
"""Analyze metadata-only community formation in the final Slovene Bluesky corpus.

The analysis intentionally uses only metadata already present in the final corpus:
timestamps, author identifiers, and post-type flags. It does not perform NLP
annotation, tokenisation, or linguistic parsing.

Outputs are written to ``outputs/community_formation`` by default:

  - monthly_community_metrics.csv
  - figure_posts_per_month.png
  - figure_active_and_new_authors.png
  - figure_cumulative_authors.png
  - figure_posts_per_active_author.png
  - figure_retention.png
  - summary_stats.md
"""
from __future__ import annotations

import argparse
import calendar
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/slosky-matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl


INCLUDED_DECISIONS = {
    "core_tag_supported",
    "review_model_consensus_only",
    "review_langid_only",
    "review_langdetect_only",
}


@dataclass(frozen=True)
class PartialMonthInfo:
    last_month: pd.Period
    last_complete_month: pd.Period
    is_partial: bool
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/final/final_sl_corpus.jsonl"),
        help="Final corpus JSONL file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/community_formation"),
        help="Directory for CSV, figures, and markdown summary.",
    )
    return parser.parse_args()


def load_final_rows(path: Path) -> pd.DataFrame:
    """Load final-corpus rows and keep only included final-corpus decisions."""
    rows: list[dict[str, object]] = []
    for row in iter_jsonl(path):
        decision = row.get("decision")
        if decision is not None and decision not in INCLUDED_DECISIONS:
            continue

        rows.append(
            {
                "created_at": row.get("created_at"),
                "author_did": row.get("author_did"),
                "reply_flag": bool(row.get("reply_flag")),
                "quote_flag": bool(row.get("quote_flag")),
                "decision": decision,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"No final-corpus rows found in {path}")

    required = {"created_at", "author_did"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(sorted(missing))}")

    # Bluesky timestamps are UTC ISO strings, but some include fractional
    # seconds while others do not. ``format="mixed"`` prevents pandas from
    # inferring one timestamp shape and coercing valid alternatives to NaT.
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce", format="mixed")
    df = df.dropna(subset=["created_at", "author_did"]).copy()
    df["month"] = df["created_at"].dt.strftime("%Y-%m").apply(lambda value: pd.Period(value, freq="M"))
    return df


def month_start(period: pd.Period) -> pd.Timestamp:
    return period.to_timestamp(how="start")


def detect_partial_final_month(max_timestamp: pd.Timestamp) -> PartialMonthInfo:
    last_month = pd.Period(max_timestamp.strftime("%Y-%m"), freq="M")
    last_day = calendar.monthrange(last_month.year, last_month.month)[1]
    final_month_complete = max_timestamp.day == last_day

    if final_month_complete:
        return PartialMonthInfo(
            last_month=last_month,
            last_complete_month=last_month,
            is_partial=False,
            note=f"Final observed month {last_month} appears complete by date.",
        )

    return PartialMonthInfo(
        last_month=last_month,
        last_complete_month=last_month - 1,
        is_partial=True,
        note=(
            f"Final observed month {last_month} is partial "
            f"(last timestamp: {max_timestamp.isoformat()}); it is flagged and "
            "excluded from retention windows, monthly period medians, and tests."
        ),
    )


def build_monthly_metrics(df: pd.DataFrame, partial: PartialMonthInfo) -> pd.DataFrame:
    first_timestamp_by_author = df.groupby("author_did")["created_at"].min()
    first_month_by_author = first_timestamp_by_author.dt.strftime("%Y-%m").apply(
        lambda value: pd.Period(value, freq="M")
    )
    first_month_map = first_month_by_author.to_dict()
    df = df.copy()
    df["author_first_month"] = df["author_did"].map(first_month_map)

    start_month = df["month"].min()
    end_month = df["month"].max()
    all_months = pd.period_range(start=start_month, end=end_month, freq="M")

    posts_total = df.groupby("month").size().reindex(all_months, fill_value=0)
    active_sets = df.groupby("month")["author_did"].agg(lambda values: set(values))

    author_months = df.groupby("author_did")["month"].agg(lambda values: set(values))
    rows: list[dict[str, object]] = []
    cumulative_authors = 0

    for month in all_months:
        active_authors = active_sets.get(month, set())
        new_authors = {
            author
            for author, first_month in first_month_map.items()
            if first_month == month
        }
        returning_authors = {
            author
            for author in active_authors
            if first_month_map.get(author) is not None and first_month_map[author] < month
        }

        cumulative_authors += len(new_authors)
        active_count = len(active_authors)
        post_count = int(posts_total.loc[month])

        retention_1m = retention_for_cohort(
            new_authors,
            author_months,
            target_months={month + 1},
            valid_until=partial.last_complete_month,
        )
        retention_3m = retention_for_cohort(
            new_authors,
            author_months,
            target_months={month + 1, month + 2, month + 3},
            valid_until=partial.last_complete_month,
        )

        rows.append(
            {
                "month": str(month),
                "posts_total": post_count,
                "authors_active": active_count,
                "authors_new": len(new_authors),
                "authors_returning": len(returning_authors),
                "posts_per_active_author": (
                    post_count / active_count if active_count else math.nan
                ),
                "author_retention_1m": retention_1m,
                "author_retention_3m": retention_3m,
                "cumulative_authors": cumulative_authors,
                "is_partial_month": month == partial.last_month and partial.is_partial,
            }
        )

    return pd.DataFrame(rows)


def retention_for_cohort(
    cohort_authors: set[str],
    author_months: pd.Series,
    target_months: set[pd.Period],
    valid_until: pd.Period,
) -> float:
    if not cohort_authors:
        return math.nan
    if max(target_months) > valid_until:
        return math.nan

    retained = 0
    for author in cohort_authors:
        months = author_months.get(author, set())
        if months.intersection(target_months):
            retained += 1
    return retained / len(cohort_authors)


def pct_growth(before: float, after: float) -> float:
    if before == 0:
        return math.nan
    return (after - before) / before * 100


def cliffs_delta(pre: pd.Series, post: pd.Series) -> float:
    """Cliff's delta, positive when post-surge values tend to be larger."""
    pre_vals = [float(v) for v in pre.dropna()]
    post_vals = [float(v) for v in post.dropna()]
    if not pre_vals or not post_vals:
        return math.nan

    greater = 0
    lower = 0
    for post_value in post_vals:
        for pre_value in pre_vals:
            if post_value > pre_value:
                greater += 1
            elif post_value < pre_value:
                lower += 1
    return (greater - lower) / (len(pre_vals) * len(post_vals))


def format_number(value: float | int) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}"
    return f"{int(value):,}"


def format_pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.1f}%"


def write_csv(monthly: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "monthly_community_metrics.csv"
    monthly.to_csv(path, index=False, float_format="%.6f")
    return path


def setup_month_axis(ax: plt.Axes) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save_figures(monthly: pd.DataFrame, output_dir: Path) -> list[Path]:
    monthly = monthly.copy()
    monthly["month_date"] = pd.to_datetime(monthly["month"] + "-01", utc=True)
    full_retention = monthly.dropna(subset=["author_retention_1m", "author_retention_3m"])

    figure_paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(monthly["month_date"], monthly["posts_total"], marker="o", linewidth=1.7)
    ax.set_title("Monthly Slovene Bluesky Posts")
    ax.set_ylabel("Posts")
    setup_month_axis(ax)
    path = output_dir / "figure_posts_per_month.png"
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figure_paths.append(path)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(monthly["month_date"], monthly["authors_active"], marker="o", linewidth=1.7, label="Active authors")
    ax.plot(monthly["month_date"], monthly["authors_new"], marker="o", linewidth=1.7, label="New authors")
    ax.set_title("Monthly Active and New Authors")
    ax.set_ylabel("Authors")
    setup_month_axis(ax)
    ax.legend(frameon=False)
    path = output_dir / "figure_active_and_new_authors.png"
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figure_paths.append(path)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(monthly["month_date"], monthly["cumulative_authors"], marker="o", linewidth=1.7)
    ax.set_title("Cumulative Authors")
    ax.set_ylabel("Authors observed")
    setup_month_axis(ax)
    path = output_dir / "figure_cumulative_authors.png"
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figure_paths.append(path)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(monthly["month_date"], monthly["posts_per_active_author"], marker="o", linewidth=1.7)
    ax.set_title("Monthly Posts per Active Author")
    ax.set_ylabel("Posts / active author")
    setup_month_axis(ax)
    path = output_dir / "figure_posts_per_active_author.png"
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figure_paths.append(path)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(
        full_retention["month_date"],
        full_retention["author_retention_1m"],
        marker="o",
        linewidth=1.7,
        label="1-month retention",
    )
    ax.plot(
        full_retention["month_date"],
        full_retention["author_retention_3m"],
        marker="o",
        linewidth=1.7,
        label="3-month retention",
    )
    ax.set_title("New-Author Retention by Cohort Month")
    ax.set_ylabel("Proportion retained")
    ax.set_ylim(0, 1.05)
    setup_month_axis(ax)
    ax.legend(frameon=False)
    path = output_dir / "figure_retention.png"
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figure_paths.append(path)

    return figure_paths


def period_summary(monthly: pd.DataFrame, df: pd.DataFrame, partial: PartialMonthInfo) -> pd.DataFrame:
    monthly_periods = monthly.copy()
    monthly_periods["period_month"] = monthly_periods["month"].apply(lambda value: pd.Period(value, freq="M"))
    monthly_complete = monthly_periods[monthly_periods["period_month"] <= partial.last_complete_month]

    periods = {
        "pre_surge_through_2024_10": (None, pd.Period("2024-10", freq="M")),
        "post_surge_from_2024_11": (pd.Period("2024-11", freq="M"), None),
    }

    rows: list[dict[str, object]] = []
    for label, (start, end) in periods.items():
        period_df = df.copy()
        if start is not None:
            period_df = period_df[period_df["month"] >= start]
        if end is not None:
            period_df = period_df[period_df["month"] <= end]

        period_monthly = monthly_complete.copy()
        if start is not None:
            period_monthly = period_monthly[period_monthly["period_month"] >= start]
        if end is not None:
            period_monthly = period_monthly[period_monthly["period_month"] <= end]

        rows.append(
            {
                "period": label,
                "total_posts": int(len(period_df)),
                "total_active_authors": int(period_df["author_did"].nunique()),
                "median_monthly_posts_total": float(period_monthly["posts_total"].median()),
                "median_monthly_authors_active": float(period_monthly["authors_active"].median()),
                "median_posts_per_active_author": float(period_monthly["posts_per_active_author"].median()),
                "monthly_medians_exclude_partial_final_month": partial.is_partial,
            }
        )

    return pd.DataFrame(rows)


def statistical_tests(monthly: pd.DataFrame, partial: PartialMonthInfo) -> pd.DataFrame:
    monthly = monthly.copy()
    monthly["period_month"] = monthly["month"].apply(lambda value: pd.Period(value, freq="M"))
    monthly = monthly[monthly["period_month"] <= partial.last_complete_month]
    pre = monthly[monthly["period_month"] <= pd.Period("2024-10", freq="M")]
    post = monthly[monthly["period_month"] >= pd.Period("2024-11", freq="M")]

    rows: list[dict[str, object]] = []
    for metric in ["posts_total", "authors_active", "posts_per_active_author"]:
        pre_values = pre[metric].dropna()
        post_values = post[metric].dropna()
        result = mannwhitneyu(post_values, pre_values, alternative="two-sided")
        rows.append(
            {
                "metric": metric,
                "n_pre_months": len(pre_values),
                "n_post_months": len(post_values),
                "median_pre": float(pre_values.median()),
                "median_post": float(post_values.median()),
                "mann_whitney_u_post_vs_pre": float(result.statistic),
                "p_value_two_sided": float(result.pvalue),
                "cliffs_delta_post_vs_pre": cliffs_delta(pre_values, post_values),
            }
        )

    return pd.DataFrame(rows)


def structural_break_summary(monthly: pd.DataFrame) -> dict[str, object]:
    by_month = monthly.set_index("month")
    oct_row = by_month.loc["2024-10"]
    nov_row = by_month.loc["2024-11"]
    return {
        "october_2024": {
            "posts_total": int(oct_row["posts_total"]),
            "authors_active": int(oct_row["authors_active"]),
            "authors_new": int(oct_row["authors_new"]),
        },
        "november_2024": {
            "posts_total": int(nov_row["posts_total"]),
            "authors_active": int(nov_row["authors_active"]),
            "authors_new": int(nov_row["authors_new"]),
        },
        "posts_total_growth_pct": pct_growth(oct_row["posts_total"], nov_row["posts_total"]),
        "authors_active_growth_pct": pct_growth(oct_row["authors_active"], nov_row["authors_active"]),
    }


def interpretation_bullets(
    monthly: pd.DataFrame,
    structural: dict[str, object],
    periods: pd.DataFrame,
    tests: pd.DataFrame,
    partial: PartialMonthInfo,
) -> list[str]:
    by_month = monthly.set_index("month")
    november = by_month.loc["2024-11"]
    december = by_month.loc["2024-12"]
    post_period = periods.set_index("period").loc["post_surge_from_2024_11"]

    posts_test = tests.set_index("metric").loc["posts_total"]
    authors_test = tests.set_index("metric").loc["authors_active"]
    ppa_test = tests.set_index("metric").loc["posts_per_active_author"]

    return [
        (
            "The monthly metadata show a clear discontinuity in late 2024: posts rise "
            f"from {structural['october_2024']['posts_total']:,} in October 2024 to "
            f"{structural['november_2024']['posts_total']:,} in November 2024, while "
            f"active authors rise from {structural['october_2024']['authors_active']:,} "
            f"to {structural['november_2024']['authors_active']:,}."
        ),
        (
            "The November 2024 increase is not only a posting-volume effect: "
            f"{int(november['authors_new']):,} authors first appear in the included corpus "
            f"in November, followed by {int(december['authors_new']):,} in December."
        ),
        (
            "After the break, the median complete monthly post count is "
            f"{post_period['median_monthly_posts_total']:,.0f}, compared with "
            f"{periods.set_index('period').loc['pre_surge_through_2024_10', 'median_monthly_posts_total']:,.0f} "
            "before November 2024."
        ),
        (
            "Monthly active-author counts are also higher after November 2024; the "
            f"Mann-Whitney comparison gives Cliff's delta {authors_test['cliffs_delta_post_vs_pre']:.2f} "
            f"(two-sided p={authors_test['p_value_two_sided']:.3g})."
        ),
        (
            "The posts-per-active-author comparison is useful as a caution: it tests whether "
            "the change reflects only more participants or also a change in monthly posting "
            f"intensity. In this corpus, Cliff's delta is {ppa_test['cliffs_delta_post_vs_pre']:.2f} "
            f"(two-sided p={ppa_test['p_value_two_sided']:.3g})."
        ),
        (
            "The retention metrics should be read descriptively rather than causally: they show "
            "which first-seen author cohorts reappear in later months, but they do not explain "
            "why authors joined or remained active."
        ),
        partial.note,
    ]


def suggested_paragraph(
    structural: dict[str, object],
    periods: pd.DataFrame,
    tests: pd.DataFrame,
    partial: PartialMonthInfo,
) -> str:
    period_index = periods.set_index("period")
    pre = period_index.loc["pre_surge_through_2024_10"]
    post = period_index.loc["post_surge_from_2024_11"]
    tests_index = tests.set_index("metric")
    posts_test = tests_index.loc["posts_total"]
    authors_test = tests_index.loc["authors_active"]

    return (
        "A metadata-only monthly analysis supports reading the corpus as a record of "
        "community formation rather than as simple post accumulation. Before November "
        f"2024, the median monthly volume was {pre['median_monthly_posts_total']:,.0f} "
        f"posts by {pre['median_monthly_authors_active']:,.0f} active authors; from "
        f"November 2024 onward, excluding the partial final month from monthly medians, "
        f"the corresponding medians were {post['median_monthly_posts_total']:,.0f} "
        f"posts and {post['median_monthly_authors_active']:,.0f} active authors. "
        f"The clearest break occurs between October and November 2024, when posts "
        f"increased from {structural['october_2024']['posts_total']:,} to "
        f"{structural['november_2024']['posts_total']:,} and active authors from "
        f"{structural['october_2024']['authors_active']:,} to "
        f"{structural['november_2024']['authors_active']:,}. Mann-Whitney tests on "
        f"complete months indicate large post-surge differences for both monthly post "
        f"volume (Cliff's delta={posts_test['cliffs_delta_post_vs_pre']:.2f}, "
        f"p={posts_test['p_value_two_sided']:.3g}) and active-author counts "
        f"(Cliff's delta={authors_test['cliffs_delta_post_vs_pre']:.2f}, "
        f"p={authors_test['p_value_two_sided']:.3g}). These results do not establish "
        "the cause of the increase, but they show that late 2024 marks a shift in both "
        "participation and activity in the recoverable Slovene Bluesky corpus."
    )


def write_summary(
    output_dir: Path,
    input_path: Path,
    df: pd.DataFrame,
    monthly: pd.DataFrame,
    structural: dict[str, object],
    periods: pd.DataFrame,
    tests: pd.DataFrame,
    partial: PartialMonthInfo,
) -> Path:
    bullets = interpretation_bullets(monthly, structural, periods, tests, partial)
    paragraph = suggested_paragraph(structural, periods, tests, partial)

    lines: list[str] = []
    lines.append("# Community Formation Metadata Analysis")
    lines.append("")
    lines.append(f"Input corpus: `{input_path}`")
    lines.append(f"Rows analysed: {len(df):,}")
    lines.append(f"Unique authors: {df['author_did'].nunique():,}")
    lines.append(
        f"UTC date range: {df['created_at'].min().isoformat()} to {df['created_at'].max().isoformat()}"
    )
    lines.append(f"Partial-month handling: {partial.note}")
    lines.append("")

    lines.append("## October-November 2024 Break")
    lines.append("")
    lines.append("| Metric | October 2024 | November 2024 | Growth |")
    lines.append("|---|---:|---:|---:|")
    lines.append(
        "| posts_total | "
        f"{structural['october_2024']['posts_total']:,} | "
        f"{structural['november_2024']['posts_total']:,} | "
        f"{format_pct(structural['posts_total_growth_pct'])} |"
    )
    lines.append(
        "| authors_active | "
        f"{structural['october_2024']['authors_active']:,} | "
        f"{structural['november_2024']['authors_active']:,} | "
        f"{format_pct(structural['authors_active_growth_pct'])} |"
    )
    lines.append(
        "| authors_new | "
        f"{structural['october_2024']['authors_new']:,} | "
        f"{structural['november_2024']['authors_new']:,} |  |"
    )
    lines.append("")

    lines.append("## Period Comparison")
    lines.append("")
    lines.append(
        "Monthly medians exclude the partial final month when one is detected; total posts "
        "and total active authors describe all observed rows in each period."
    )
    lines.append("")
    lines.extend(markdown_table(periods))
    lines.append("")

    lines.append("## Mann-Whitney Tests")
    lines.append("")
    lines.append(
        "Tests compare complete monthly observations before November 2024 with complete "
        "monthly observations from November 2024 onward. Cliff's delta is positive when "
        "post-surge monthly values tend to be larger."
    )
    lines.append("")
    lines.extend(markdown_table(tests))
    lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    for bullet in bullets:
        lines.append(f"- {bullet}")
    lines.append("")

    lines.append("## Suggested Paper Paragraph")
    lines.append("")
    lines.append(paragraph)
    lines.append("")

    path = output_dir / "summary_stats.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def markdown_table(df: pd.DataFrame) -> list[str]:
    """Render a small DataFrame as a GitHub-flavoured Markdown table.

    This avoids pandas' optional ``tabulate`` dependency and keeps the script
    runnable with only pandas, matplotlib, and scipy.
    """
    columns = list(df.columns)
    rows = [columns]
    for _, row in df.iterrows():
        rendered: list[str] = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                rendered.append(f"{value:.6g}")
            else:
                rendered.append(str(value))
        rows.append(rendered)

    widths = [
        max(len(str(row[column_index])) for row in rows)
        for column_index in range(len(columns))
    ]

    output: list[str] = []
    header = "| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(rows[0])) + " |"
    separator = "| " + " | ".join("-" * widths[index] for index in range(len(columns))) + " |"
    output.append(header)
    output.append(separator)
    for row in rows[1:]:
        output.append("| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)) + " |")
    return output


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = load_final_rows(args.input)
    partial = detect_partial_final_month(df["created_at"].max())
    monthly = build_monthly_metrics(df, partial)

    csv_path = write_csv(monthly, args.output_dir)
    figure_paths = save_figures(monthly, args.output_dir)
    structural = structural_break_summary(monthly)
    periods = period_summary(monthly, df, partial)
    tests = statistical_tests(monthly, partial)
    summary_path = write_summary(
        args.output_dir,
        args.input,
        df,
        monthly,
        structural,
        periods,
        tests,
        partial,
    )

    machine_summary = {
        "input": str(args.input),
        "rows_analyzed": int(len(df)),
        "unique_authors": int(df["author_did"].nunique()),
        "partial_final_month": partial.__dict__,
        "structural_break": structural,
        "output_files": [str(csv_path), *(str(path) for path in figure_paths), str(summary_path)],
    }
    json_path = args.output_dir / "summary_stats.json"
    json_path.write_text(json.dumps(machine_summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"Rows analysed: {len(df):,}")
    print(f"Unique authors: {df['author_did'].nunique():,}")
    print(partial.note)
    print("")
    print("October-November 2024 structural break:")
    print(
        f"  posts_total: {structural['october_2024']['posts_total']:,} -> "
        f"{structural['november_2024']['posts_total']:,} "
        f"({format_pct(structural['posts_total_growth_pct'])})"
    )
    print(
        f"  authors_active: {structural['october_2024']['authors_active']:,} -> "
        f"{structural['november_2024']['authors_active']:,} "
        f"({format_pct(structural['authors_active_growth_pct'])})"
    )
    print(
        f"  authors_new: {structural['october_2024']['authors_new']:,} -> "
        f"{structural['november_2024']['authors_new']:,}"
    )
    print("")
    print("Output files:")
    for path in machine_summary["output_files"]:
        print(f"  {path}")
    print(f"  {json_path}")
    print("")
    print("Suggested paper paragraph:")
    print(suggested_paragraph(structural, periods, tests, partial))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

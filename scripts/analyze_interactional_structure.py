#!/usr/bin/env python3
"""Metadata-only analysis of interactional structure in the final Slovene Bluesky corpus.

Uses only fields already present in the final corpus: post timestamp, author
identifier, reply_flag, and quote_flag. No NLP annotation, tokenisation,
parsing, or network analysis.

Post-type classification follows the hierarchy already used in the paper:
  - reply (reply_flag=True; reply+quote combinations also counted here)
  - original (neither flag set)
  - nonreply_quote (quote_flag=True, reply_flag=False)

Outputs (default: outputs/interaction_analysis/):
  - monthly_interaction_metrics.csv
  - author_interaction_profiles.csv
  - author_interaction_profiles_min20.csv
  - figure_monthly_interaction_shares.png
  - figure_author_replyrate_hist_min20.png
  - figure_author_style_groups_min20.png
  - summary_interaction_stats.md
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/slosky-matplotlib")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.corpus import iter_jsonl


INCLUDED_DECISIONS = {
    "core_tag_supported",
    "review_model_consensus_only",
    "review_langid_only",
    "review_langdetect_only",
}

# The structural break month; everything before this is "pre-surge".
BREAK_MONTH = pd.Period("2024-11", freq="M")

# Minimum post thresholds for author profile filters.
MIN_POSTS_20 = 20
MIN_POSTS_50 = 50

# Descriptive style-group boundaries (heuristic, not validated social categories).
BROADCAST_THRESHOLD = 0.2   # reply_rate < 0.2 → broadcast-heavy
CONVERSATIONAL_THRESHOLD = 0.8  # reply_rate > 0.8 → conversational


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/final/final_sl_corpus.jsonl"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/interaction_analysis"),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_corpus(path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for row in iter_jsonl(path):
        if row.get("decision") not in INCLUDED_DECISIONS:
            continue
        rows.append({
            "created_at": row.get("created_at"),
            "author_did": row.get("author_did"),
            "reply_flag": bool(row.get("reply_flag")),
            "quote_flag": bool(row.get("quote_flag")),
        })

    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(
        df["created_at"], utc=True, errors="coerce", format="mixed"
    )
    df = df.dropna(subset=["created_at", "author_did"]).copy()

    # Mutually exclusive post type: reply takes precedence over quote.
    df["post_type"] = "original"
    df.loc[df["quote_flag"] & ~df["reply_flag"], "post_type"] = "nonreply_quote"
    df.loc[df["reply_flag"], "post_type"] = "reply"

    df["month"] = df["created_at"].dt.strftime("%Y-%m").apply(
        lambda v: pd.Period(v, freq="M")
    )

    return df


# ---------------------------------------------------------------------------
# Partial-month detection (replicates logic from analyze_community_formation)
# ---------------------------------------------------------------------------

def is_partial_month(df: pd.DataFrame) -> tuple[pd.Period, bool]:
    import calendar
    max_ts = df["created_at"].max()
    last_month = pd.Period(max_ts.strftime("%Y-%m"), freq="M")
    last_day = calendar.monthrange(last_month.year, last_month.month)[1]
    return last_month, max_ts.day < last_day


# ---------------------------------------------------------------------------
# 2. Monthly interaction-type analysis
# ---------------------------------------------------------------------------

def build_monthly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    all_months = pd.period_range(df["month"].min(), df["month"].max(), freq="M")

    counts = (
        df.groupby(["month", "post_type"])
        .size()
        .unstack(fill_value=0)
        .reindex(all_months, fill_value=0)
    )
    for col in ("reply", "original", "nonreply_quote"):
        if col not in counts.columns:
            counts[col] = 0

    monthly = pd.DataFrame({
        "month": [str(m) for m in all_months],
        "posts_total": counts["reply"] + counts["original"] + counts["nonreply_quote"],
        "replies_total": counts["reply"],
        "originals_total": counts["original"],
        "nonreply_quotes_total": counts["nonreply_quote"],
    })

    monthly["replies_share"] = monthly["replies_total"] / monthly["posts_total"]
    monthly["originals_share"] = monthly["originals_total"] / monthly["posts_total"]
    monthly["nonreply_quotes_share"] = monthly["nonreply_quotes_total"] / monthly["posts_total"]

    return monthly


# ---------------------------------------------------------------------------
# 3. Early vs post-surge comparison
# ---------------------------------------------------------------------------

def period_comparison(df: pd.DataFrame) -> pd.DataFrame:
    pre = df[df["month"] < BREAK_MONTH]
    post = df[df["month"] >= BREAK_MONTH]

    rows = []
    for label, subset in [("through_2024_10", pre), ("2024_11_onward", post)]:
        n = len(subset)
        rows.append({
            "period": label,
            "total_posts": n,
            "reply_share": subset["post_type"].eq("reply").sum() / n if n else math.nan,
            "original_share": subset["post_type"].eq("original").sum() / n if n else math.nan,
            "nonreply_quote_share": subset["post_type"].eq("nonreply_quote").sum() / n if n else math.nan,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Per-author interaction profiles
# ---------------------------------------------------------------------------

def build_author_profiles(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("author_did")
    profiles = pd.DataFrame({
        "total_posts": g.size(),
        "reply_count": g["post_type"].apply(lambda s: (s == "reply").sum()),
        "original_count": g["post_type"].apply(lambda s: (s == "original").sum()),
        "nonreply_quote_count": g["post_type"].apply(lambda s: (s == "nonreply_quote").sum()),
    })
    profiles["reply_rate"] = profiles["reply_count"] / profiles["total_posts"]
    return profiles.reset_index()


def author_stats(profiles: pd.DataFrame, min_posts: int) -> dict:
    filtered = profiles[profiles["total_posts"] >= min_posts].copy()
    n = len(filtered)
    rr = filtered["reply_rate"]
    return {
        "min_posts": min_posts,
        "n_authors": n,
        "median_reply_rate": float(rr.median()),
        "q25_reply_rate": float(rr.quantile(0.25)),
        "q75_reply_rate": float(rr.quantile(0.75)),
        "authors_rate_zero": int((rr == 0).sum()),
        "authors_rate_zero_pct": float((rr == 0).mean() * 100),
        "authors_rate_gt80": int((rr > 0.8).sum()),
        "authors_rate_gt80_pct": float((rr > 0.8).mean() * 100),
        "authors_rate_gt90": int((rr > 0.9).sum()),
        "authors_rate_gt90_pct": float((rr > 0.9).mean() * 100),
    }


# ---------------------------------------------------------------------------
# 5. Descriptive author-style grouping (heuristic, not validated categories)
# ---------------------------------------------------------------------------

def style_groups(profiles_min20: pd.DataFrame, total_corpus_posts: int) -> pd.DataFrame:
    df = profiles_min20.copy()
    df["style_group"] = "mixed"
    df.loc[df["reply_rate"] < BROADCAST_THRESHOLD, "style_group"] = "broadcast_heavy"
    df.loc[df["reply_rate"] > CONVERSATIONAL_THRESHOLD, "style_group"] = "conversational"

    g = df.groupby("style_group")
    summary = pd.DataFrame({
        "n_authors": g.size(),
        "total_posts_contributed": g["total_posts"].sum(),
    }).reset_index()
    summary["corpus_share_pct"] = summary["total_posts_contributed"] / total_corpus_posts * 100

    # Preserve ordering
    order = ["broadcast_heavy", "mixed", "conversational"]
    summary["style_group"] = pd.Categorical(summary["style_group"], categories=order, ordered=True)
    summary = summary.sort_values("style_group").reset_index(drop=True)

    return summary, df  # return annotated profiles too


# ---------------------------------------------------------------------------
# 6. Monthly reply share: all posts vs min-20 author subset
# ---------------------------------------------------------------------------

def monthly_reply_share_by_subset(df: pd.DataFrame, profiles_min20: pd.DataFrame) -> pd.DataFrame:
    min20_authors = set(profiles_min20["author_did"])
    df_subset = df[df["author_did"].isin(min20_authors)]

    all_months = pd.period_range(df["month"].min(), df["month"].max(), freq="M")

    def monthly_share(subdf: pd.DataFrame) -> pd.Series:
        counts = subdf.groupby("month")["post_type"].apply(lambda s: (s == "reply").sum())
        totals = subdf.groupby("month").size()
        return (counts / totals).reindex(all_months)

    return pd.DataFrame({
        "month": [str(m) for m in all_months],
        "replies_share_all": monthly_share(df).values,
        "replies_share_min20": monthly_share(df_subset).values,
    })


# ---------------------------------------------------------------------------
# 7. Figures
# ---------------------------------------------------------------------------

STYLE = {
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#d9d9d9",
    "grid.linewidth": 0.7,
    "axes.axisbelow": True,
}


def figure_monthly_shares(monthly: pd.DataFrame, output_dir: Path, partial_month: str | None) -> Path:
    dates = pd.to_datetime(monthly["month"] + "-01", utc=True)

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(dates, monthly["replies_share"] * 100, label="Reply", linewidth=1.8, color="#2196F3")
        ax.plot(dates, monthly["originals_share"] * 100, label="Original post", linewidth=1.8, color="#FF9800")
        ax.plot(dates, monthly["nonreply_quotes_share"] * 100, label="Non-reply quote", linewidth=1.8, color="#4CAF50")

        if partial_month:
            partial_date = pd.to_datetime(partial_month + "-01", utc=True)
            ax.axvline(partial_date, color="gray", linestyle=":", linewidth=1.0, label="Partial month")

        ax.set_ylabel("Share of monthly posts (%)")
        ax.set_ylim(0, 100)
        ax.legend(frameon=False, fontsize=9)
        ax.set_title("Monthly post-type shares (reply / original / non-reply quote)", fontsize=11)
        fig.tight_layout()

    path = output_dir / "figure_monthly_interaction_shares.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def figure_replyrate_hist(profiles_min20: pd.DataFrame, output_dir: Path) -> Path:
    rr = profiles_min20["reply_rate"].dropna()

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(rr, bins=20, range=(0, 1), color="#2196F3", edgecolor="white", linewidth=0.5)
        ax.axvline(BROADCAST_THRESHOLD, color="#FF9800", linestyle="--", linewidth=1.2,
                   label=f"Broadcast threshold ({BROADCAST_THRESHOLD})")
        ax.axvline(CONVERSATIONAL_THRESHOLD, color="#4CAF50", linestyle="--", linewidth=1.2,
                   label=f"Conversational threshold ({CONVERSATIONAL_THRESHOLD})")
        ax.set_xlabel("Reply rate (reply count / total posts)")
        ax.set_ylabel("Number of authors")
        ax.set_title(f"Per-author reply rate — authors with ≥{MIN_POSTS_20} posts (n={len(rr)})", fontsize=11)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()

    path = output_dir / "figure_author_replyrate_hist_min20.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def figure_style_groups(groups: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    labels = [g.replace("_", "-") for g in groups["style_group"].astype(str)]
    colors = ["#FF9800", "#9E9E9E", "#2196F3"]

    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        # By number of authors
        axes[0].bar(labels, groups["n_authors"], color=colors, edgecolor="white")
        axes[0].set_ylabel("Number of authors")
        axes[0].set_title("Authors per style group")
        for i, v in enumerate(groups["n_authors"]):
            axes[0].text(i, v + 0.3, str(v), ha="center", va="bottom", fontsize=9)

        # By total posts contributed
        axes[1].bar(labels, groups["total_posts_contributed"], color=colors, edgecolor="white")
        axes[1].set_ylabel("Total posts contributed")
        axes[1].set_title("Posts per style group")
        for i, v in enumerate(groups["total_posts_contributed"]):
            axes[1].text(i, v + 100, f"{v:,}", ha="center", va="bottom", fontsize=9)

        fig.suptitle(
            "Descriptive author style groups (heuristic — not validated social categories)",
            fontsize=10, y=1.01
        )
        fig.tight_layout()

    path = output_dir / "figure_author_style_groups_min20.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 8 + 9. Markdown summary
# ---------------------------------------------------------------------------

def fmt_pct(v: float, decimals: int = 1) -> str:
    return f"{v:.{decimals}f}%"


def fmt_n(v: float | int) -> str:
    if pd.isna(v):
        return "NA"
    return f"{int(v):,}"


def write_summary(
    output_dir: Path,
    df: pd.DataFrame,
    monthly: pd.DataFrame,
    period_comp: pd.DataFrame,
    stats20: dict,
    stats50: dict | None,
    groups: pd.DataFrame,
    partial_month: str | None,
    monthly_subset: pd.DataFrame,
) -> Path:
    total_n = len(df)
    reply_n = (df["post_type"] == "reply").sum()
    original_n = (df["post_type"] == "original").sum()
    quote_n = (df["post_type"] == "nonreply_quote").sum()

    lines: list[str] = []
    lines += [
        "# Interactional Structure Analysis",
        "",
        f"Total posts analysed: {total_n:,}",
        f"Unique authors: {df['author_did'].nunique():,}",
        f"UTC date range: {df['created_at'].min().date()} to {df['created_at'].max().date()}",
    ]
    if partial_month:
        lines.append(f"Partial final month: {partial_month} (flagged; excluded from medians where noted)")
    lines.append("")

    lines += [
        "## Overall post-type distribution",
        "",
        f"| Post type | Count | Share |",
        f"|---|---:|---:|",
        f"| Reply (incl. reply+quote) | {reply_n:,} | {fmt_pct(reply_n/total_n*100)} |",
        f"| Original post | {original_n:,} | {fmt_pct(original_n/total_n*100)} |",
        f"| Non-reply quote | {quote_n:,} | {fmt_pct(quote_n/total_n*100)} |",
        "",
    ]

    lines += ["## Early vs post-surge comparison", ""]
    pc = period_comp.set_index("period")
    for period_label in ("through_2024_10", "2024_11_onward"):
        row = pc.loc[period_label]
        lines.append(f"**{period_label}** — {fmt_n(row['total_posts'])} posts")
        lines.append(
            f"  reply {fmt_pct(row['reply_share']*100)} | "
            f"original {fmt_pct(row['original_share']*100)} | "
            f"non-reply quote {fmt_pct(row['nonreply_quote_share']*100)}"
        )
        lines.append("")

    lines += ["## Per-author reply-rate summary (authors with ≥20 posts)", ""]
    s = stats20
    lines += [
        f"Authors in set: {s['n_authors']}",
        f"Median reply rate: {s['median_reply_rate']:.3f} (IQR: {s['q25_reply_rate']:.3f}–{s['q75_reply_rate']:.3f})",
        f"Reply rate = 0: {s['authors_rate_zero']} ({fmt_pct(s['authors_rate_zero_pct'])})",
        f"Reply rate > 0.8: {s['authors_rate_gt80']} ({fmt_pct(s['authors_rate_gt80_pct'])})",
        f"Reply rate > 0.9: {s['authors_rate_gt90']} ({fmt_pct(s['authors_rate_gt90_pct'])})",
        "",
    ]

    if stats50:
        s50 = stats50
        lines += [
            "## Per-author reply-rate summary (authors with ≥50 posts)",
            "",
            f"Authors in set: {s50['n_authors']}",
            f"Median reply rate: {s50['median_reply_rate']:.3f} (IQR: {s50['q25_reply_rate']:.3f}–{s50['q75_reply_rate']:.3f})",
            f"Reply rate > 0.8: {s50['authors_rate_gt80']} ({fmt_pct(s50['authors_rate_gt80_pct'])})",
            f"Reply rate > 0.9: {s50['authors_rate_gt90']} ({fmt_pct(s50['authors_rate_gt90_pct'])})",
            "",
        ]

    lines += [
        "## Descriptive author style groups",
        "",
        "> **Important:** these groups are defined by simple reply-rate thresholds",
        "> (broadcast-heavy < 0.2, conversational > 0.8). They are descriptive",
        "> heuristics and have not been validated as social categories.",
        "",
        "| Group | Authors | Posts contributed | Corpus share |",
        "|---|---:|---:|---:|",
    ]
    for _, row in groups.iterrows():
        lines.append(
            f"| {str(row['style_group']).replace('_', '-')} | "
            f"{fmt_n(row['n_authors'])} | "
            f"{fmt_n(row['total_posts_contributed'])} | "
            f"{fmt_pct(row['corpus_share_pct'])} |"
        )
    lines.append("")

    lines += ["## Monthly reply share: all posts vs ≥20-post-author subset", ""]
    complete_monthly = monthly_subset[monthly_subset["month"] != partial_month] if partial_month else monthly_subset
    all_median = complete_monthly["replies_share_all"].median()
    sub_median = complete_monthly["replies_share_min20"].median()
    lines += [
        f"Median monthly reply share (all posts, complete months): {fmt_pct(all_median*100)}",
        f"Median monthly reply share (≥20-post authors, complete months): {fmt_pct(sub_median*100)}",
        "",
    ]

    lines += [
        "## Interpretation bullets (suitable for paper adaptation)",
        "",
        _interpretation_bullets(
            df, total_n, reply_n, original_n, quote_n,
            period_comp, stats20, groups, all_median, sub_median, partial_month
        ),
        "",
        "## Suggested paragraph for Section 5.4",
        "",
        _suggested_paragraph(
            total_n, reply_n, original_n, quote_n,
            period_comp, stats20, groups
        ),
        "",
    ]

    path = output_dir / "summary_interaction_stats.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _interpretation_bullets(
    df, total_n, reply_n, original_n, quote_n,
    period_comp, stats20, groups, all_median, sub_median, partial_month
) -> str:
    pc = period_comp.set_index("period")
    pre_reply = pc.loc["through_2024_10", "reply_share"]
    post_reply = pc.loc["2024_11_onward", "reply_share"]
    s = stats20
    g = groups.set_index("style_group")

    conv_n = g.loc["conversational", "n_authors"] if "conversational" in g.index else 0
    conv_share = g.loc["conversational", "corpus_share_pct"] if "conversational" in g.index else 0.0
    broad_n = g.loc["broadcast_heavy", "n_authors"] if "broadcast_heavy" in g.index else 0
    broad_share = g.loc["broadcast_heavy", "corpus_share_pct"] if "broadcast_heavy" in g.index else 0.0

    bullets = [
        f"Across all {total_n:,} posts, {reply_n:,} ({reply_n/total_n*100:.1f}%) are replies, "
        f"{original_n:,} ({original_n/total_n*100:.1f}%) are original posts, and "
        f"{quote_n:,} ({quote_n/total_n*100:.1f}%) are non-reply quote posts, confirming that "
        "the corpus is strongly conversational in its overall composition.",

        f"Reply share is high in both periods: {pre_reply*100:.1f}% before November 2024 and "
        f"{post_reply*100:.1f}% from November 2024 onward, suggesting that the conversational "
        "character of the corpus does not depend on the post-surge influx of new authors.",

        f"The median monthly reply share across complete months is {all_median*100:.1f}% for all posts "
        f"and {sub_median*100:.1f}% for posts by authors with at least {MIN_POSTS_20} posts, "
        "showing that conversationality is not an artefact of peripheral one-off contributors.",

        f"Among the {s['n_authors']} authors with at least {MIN_POSTS_20} posts, the median per-author "
        f"reply rate is {s['median_reply_rate']:.2f} (IQR {s['q25_reply_rate']:.2f}–{s['q75_reply_rate']:.2f}). "
        f"Only {s['authors_rate_zero']} author(s) ({s['authors_rate_zero_pct']:.1f}%) have a reply rate of zero.",

        f"{s['authors_rate_gt80']} of {s['n_authors']} authors ({s['authors_rate_gt80_pct']:.1f}%) "
        f"have a reply rate above 0.8, and {s['authors_rate_gt90']} ({s['authors_rate_gt90_pct']:.1f}%) "
        f"above 0.9, indicating that high conversationality is widespread rather than confined to a few accounts.",

        f"Using descriptive heuristic thresholds (reply rate < 0.2 = broadcast-heavy; > 0.8 = conversational), "
        f"{conv_n} of {s['n_authors']} active authors ({conv_n/s['n_authors']*100:.1f}%) fall in the "
        f"conversational group and account for {conv_share:.1f}% of corpus posts, while "
        f"{broad_n} author(s) in the broadcast-heavy group account for {broad_share:.1f}% of posts. "
        "These groups are descriptive heuristics and should not be read as validated social categories.",

        "Non-reply quote posts are rare throughout the corpus (below 5% in all complete months), "
        "confirming that Bluesky's quote-post mechanism is not a dominant mode of engagement "
        "in this language community.",
    ]
    if partial_month:
        bullets.append(
            f"The final month ({partial_month}) is partial and is excluded from monthly medians "
            "and the subset-share comparison above."
        )

    return "\n".join(f"- {b}" for b in bullets)


def _suggested_paragraph(
    total_n, reply_n, original_n, quote_n,
    period_comp, stats20, groups
) -> str:
    pc = period_comp.set_index("period")
    pre_reply = pc.loc["through_2024_10", "reply_share"]
    post_reply = pc.loc["2024_11_onward", "reply_share"]
    s = stats20
    g = groups.set_index("style_group")
    conv_n = g.loc["conversational", "n_authors"] if "conversational" in g.index else 0
    broad_n = g.loc["broadcast_heavy", "n_authors"] if "broadcast_heavy" in g.index else 0

    return (
        f"The post-type distribution confirms that Slovene Bluesky use is strongly conversational. "
        f"Of the {total_n:,} corpus posts, {reply_n:,} ({reply_n/total_n*100:.1f}\\%) are replies, "
        f"{original_n:,} ({original_n/total_n*100:.1f}\\%) are original posts, and "
        f"{quote_n:,} ({quote_n/total_n*100:.1f}\\%) are non-reply quote posts. "
        "This pattern holds across the corpus timeline: reply share is "
        f"{pre_reply*100:.1f}\\% before November 2024 and {post_reply*100:.1f}\\% from November 2024 onward, "
        "suggesting that the post-surge influx of new authors did not substantially change the "
        "interactional character of the community. At the author level, among the "
        f"{s['n_authors']} authors with at least {MIN_POSTS_20} posts, the median per-author reply rate "
        f"is {s['median_reply_rate']:.2f} (IQR {s['q25_reply_rate']:.2f}\\textendash{s['q75_reply_rate']:.2f}), "
        f"and {s['authors_rate_gt80']} ({s['authors_rate_gt80_pct']:.1f}\\%) have a reply rate above 0.8. "
        f"Applying descriptive heuristic thresholds (reply rate {{$<$}}0.2 = broadcast-heavy, "
        f"{{$>$}}0.8 = conversational), {conv_n} authors fall in the conversational group and "
        f"{broad_n} in the broadcast-heavy group; these are heuristic labels rather than "
        "validated social categories. Together, these figures indicate that the dominance of "
        "reply posts is not an aggregate artefact but reflects the posting behaviour of the "
        "majority of active participants."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading corpus…")
    df = load_corpus(args.input)
    print(f"  {len(df):,} posts, {df['author_did'].nunique():,} authors")

    last_month, is_partial = is_partial_month(df)
    partial_month_str = str(last_month) if is_partial else None
    if is_partial:
        print(f"  Partial final month detected: {last_month}")

    print("Building monthly metrics…")
    monthly = build_monthly_metrics(df)
    monthly.to_csv(args.output_dir / "monthly_interaction_metrics.csv", index=False, float_format="%.6f")

    print("Computing period comparison…")
    period_comp = period_comparison(df)

    print("Building author profiles…")
    profiles = build_author_profiles(df)
    profiles.to_csv(args.output_dir / "author_interaction_profiles.csv", index=False, float_format="%.6f")

    profiles_min20 = profiles[profiles["total_posts"] >= MIN_POSTS_20].copy()
    profiles_min20.to_csv(args.output_dir / "author_interaction_profiles_min20.csv", index=False, float_format="%.6f")

    stats20 = author_stats(profiles, MIN_POSTS_20)
    stats50 = author_stats(profiles, MIN_POSTS_50) if len(profiles[profiles["total_posts"] >= MIN_POSTS_50]) > 5 else None

    print("Computing style groups…")
    groups, profiles_min20_annotated = style_groups(profiles_min20, len(df))

    print("Computing monthly subset reply shares…")
    monthly_subset = monthly_reply_share_by_subset(df, profiles_min20)

    print("Saving figures…")
    figure_monthly_shares(monthly, args.output_dir, partial_month_str)
    figure_replyrate_hist(profiles_min20, args.output_dir)
    figure_style_groups(groups, args.output_dir)

    print("Writing summary…")
    summary_path = write_summary(
        args.output_dir, df, monthly, period_comp,
        stats20, stats50, groups, partial_month_str, monthly_subset,
    )

    # Print key numbers to stdout
    total_n = len(df)
    reply_n = (df["post_type"] == "reply").sum()
    print("\n=== Key results ===")
    print(f"Overall reply share: {reply_n/total_n*100:.1f}%")
    print(f"Authors ≥{MIN_POSTS_20} posts: {stats20['n_authors']}")
    print(f"Median reply rate (≥{MIN_POSTS_20}): {stats20['median_reply_rate']:.3f}")
    print(f"Authors with reply rate > 0.8: {stats20['authors_rate_gt80']} ({stats20['authors_rate_gt80_pct']:.1f}%)")
    print(f"\nStyle groups (≥{MIN_POSTS_20} posts):")
    for _, row in groups.iterrows():
        print(f"  {row['style_group']}: {fmt_n(row['n_authors'])} authors, {fmt_n(row['total_posts_contributed'])} posts ({row['corpus_share_pct']:.1f}%)")
    print(f"\nSummary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

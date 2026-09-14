#!/usr/bin/env python3
"""Figure 1: Monthly Slovene Bluesky post counts with active-author overlay.

Reads:
    outputs/community_formation/monthly_community_metrics.csv

Writes:
    outputs/community_formation/figure1_posts_per_month.png
    outputs/community_formation/figure1_posts_per_month.pdf

Input and output paths can be overridden. The monthly input is restricted and is not
included in the public snapshot; the privacy-safe rendered figure is included.
"""

from __future__ import annotations

import os
import argparse
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/slosky-matplotlib")

import matplotlib
matplotlib.use("Agg")
# Ubuntu is the closest available substitute for Source Sans Pro (JTDH template font)
matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Ubuntu", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import blended_transform_factory
import pandas as pd

CSV_PATH  = Path("outputs/community_formation/monthly_community_metrics.csv")
# Distinct basename: analyze_community_formation.py writes its own, much plainer
# figure_posts_per_month.png into the same directory and would otherwise clobber this one.
PNG_PATH  = Path("outputs/community_formation/figure1_posts_per_month.png")
PDF_PATH  = Path("outputs/community_formation/figure1_posts_per_month.pdf")

# Colourblind-safe enough and visually restrained
C_BARS = "#3D78B5"       # muted steel blue
C_PARTIAL = "#8BBAD8"    # lighter steel blue
C_AUTHORS = "#BF5B2A"    # burnt sienna
C_EVENT = "#666666"      # dark gray for primary event lines
C_EVENT2 = "#999999"     # lighter gray for secondary (election) event lines
C_GRID = "#EEEEEE"
C_SPINE = "#CCCCCC"


def format_thousands(x: float, _: int) -> str:
    return f"{int(x):,}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=CSV_PATH)
    parser.add_argument("--output-png", type=Path, default=PNG_PATH)
    parser.add_argument("--output-pdf", type=Path, default=PDF_PATH)
    parser.add_argument("--paper-copy", type=Path, help="Optional additional PNG copy.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # ── load data ────────────────────────────────────────────────────────────
    df = pd.read_csv(args.input)
    df["month_dt"] = pd.to_datetime(df["month"] + "-01")
    df = df.sort_values("month_dt").reset_index(drop=True)

    fig, ax1 = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("white")

    # ── bars (posts) ─────────────────────────────────────────────────────────
    colors = [C_PARTIAL if p else C_BARS for p in df["is_partial_month"]]
    bars = ax1.bar(
        df["month_dt"],
        df["posts_total"],
        width=22,
        color=colors,
        zorder=2,
        linewidth=0,
    )

    for i, is_partial in enumerate(df["is_partial_month"]):
        if is_partial:
            bars[i].set_hatch("///")
            bars[i].set_edgecolor(C_PARTIAL)
            bars[i].set_linewidth(0.5)

    # ── secondary axis: active authors ──────────────────────────────────────
    ax2 = ax1.twinx()
    ax1_top = df["posts_total"].max() * 1.25
    ax2_top = df["authors_active"].max() * 1.20

    ax2.plot(
        df["month_dt"],
        df["authors_active"],
        color=C_AUTHORS,
        linewidth=1.7,
        zorder=3,
        marker="o",
        markersize=3.5,
        markerfacecolor=C_AUTHORS,
        markeredgewidth=0,
    )

    ax2.set_ylim(0, ax2_top)
    ax2.set_ylabel("Active authors", color=C_AUTHORS, fontsize=9, labelpad=8)
    ax2.tick_params(axis="y", labelcolor=C_AUTHORS, labelsize=8, length=3)

    for sp in ["top", "left", "bottom"]:
        ax2.spines[sp].set_visible(False)
    ax2.spines["right"].set_color(C_AUTHORS)
    ax2.spines["right"].set_alpha(0.12)

    # ── event annotation lines ───────────────────────────────────────────────
    trans = blended_transform_factory(ax1.transData, ax1.transAxes)

    primary_events = [
        (pd.Timestamp("2024-02-06"), "Public opening\n(6 Feb 2024)", "left", 10, 0.96),
        (pd.Timestamp("2024-11-05"), "Migration wave\n(Nov 2024)", "right", -10, 0.96),
    ]

    # Elections: contextual background, drawn dotted and lighter so they read as
    # secondary to the two platform events. Left unlabelled — the caption names them
    # in chronological order, and a label at Mar 2026 would collide with the partial
    # April bar and its tick label.
    secondary_events = [
        pd.Timestamp("2024-06-09"),  # EU Parliament elections (Slovenian polling day)
        pd.Timestamp("2026-03-22"),  # Slovenian parliamentary elections
    ]

    for xpos in secondary_events:
        ax1.axvline(
            xpos,
            color=C_EVENT2,
            linewidth=0.7,
            linestyle=(0, (1, 2)),
            zorder=1,
            alpha=0.75,
        )

    for xpos, label, ha, x_off, y_pos in primary_events:
        ax1.axvline(
            xpos,
            color=C_EVENT,
            linewidth=0.7,
            linestyle=(0, (3, 3)),
            zorder=1,
            alpha=0.50,
        )
        ax1.text(
            xpos + pd.Timedelta(days=x_off),
            y_pos,
            label,
            transform=trans,
            ha=ha,
            va="top",
            fontsize=7.4,
            color=C_EVENT,
            linespacing=1.35,
            bbox=dict(
                boxstyle="square,pad=0.08",
                facecolor="white",
                edgecolor="none",
                alpha=0.80,
            ),
        )

    # ── axes styling ─────────────────────────────────────────────────────────
    ax1.set_ylabel("Posts / month", fontsize=9, labelpad=8)
    ax1.tick_params(axis="y", labelsize=8, length=3)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(format_thousands))

    # x-ticks
    tick_dates = [
        pd.Timestamp("2023-08-01"),
        pd.Timestamp("2024-02-01"),
        pd.Timestamp("2024-08-01"),
        pd.Timestamp("2025-02-01"),
        pd.Timestamp("2025-08-01"),
        pd.Timestamp("2026-02-01"),
        pd.Timestamp("2026-04-01"),
    ]
    tick_labels = [
        "Aug 2023",
        "Feb 2024",
        "Aug 2024",
        "Feb 2025",
        "Aug 2025",
        "Feb 2026",
        "Apr 2026",
    ]

    ax1.set_xticks(tick_dates)
    ax1.set_xticklabels(tick_labels, fontsize=8)
    ax1.tick_params(axis="x", rotation=0, length=3, pad=5)

    # Slightly soften the final partial-month tick
    for lbl in ax1.get_xticklabels():
        if lbl.get_text() == "Apr 2026":
            lbl.set_color("#888888")

    pad = pd.Timedelta(days=20)
    ax1.set_xlim(df["month_dt"].min() - pad, df["month_dt"].max() + pad)
    ax1.set_ylim(0, ax1_top)

    ax1.yaxis.grid(True, color=C_GRID, linewidth=0.8, zorder=0)
    ax1.xaxis.grid(False)
    ax1.set_axisbelow(True)

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_color(C_SPINE)
    ax1.spines["bottom"].set_color(C_SPINE)

    # ── legend ───────────────────────────────────────────────────────────────
    handles = [
        Patch(facecolor=C_BARS, linewidth=0, label="Posts per month"),
        Patch(
            facecolor=C_PARTIAL,
            hatch="///",
            edgecolor=C_PARTIAL,
            linewidth=0.5,
            label="Partial month (to 16 Apr)",
        ),
        Line2D(
            [0], [0],
            color=C_AUTHORS,
            linewidth=1.7,
            marker="o",
            markersize=4,
            markeredgewidth=0,
            label="Active authors",
        ),
    ]

    ax1.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        loc="lower left",
        bbox_to_anchor=(0.01, 0.03),
    )

    # ── save ─────────────────────────────────────────────────────────────────
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    args.output_pdf.parent.mkdir(parents=True, exist_ok=True)

    fig.tight_layout(pad=1.45)
    fig.savefig(args.output_png, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(args.output_pdf, bbox_inches="tight", facecolor="white")

    if args.paper_copy:
        import shutil
        args.paper_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.output_png, args.paper_copy)

    plt.close(fig)
    print(f"Saved → {args.output_png}")
    print(f"Saved → {args.output_pdf}")
    if args.paper_copy:
        print(f"Copied → {args.paper_copy}")


if __name__ == "__main__":
    main()

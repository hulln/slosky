#!/usr/bin/env python3
"""Metadata-only hashtag and linked-domain analysis for the Slovene Bluesky corpus.

Uses only fields already present in the final corpus:
  - text (for hashtag extraction via regex)
  - author_did
  - created_at
  - link_domains (already extracted list field in the JSONL)
  - reply_flag, quote_flag (for optional post-type comparison)

No NLP annotation, topic modelling, embeddings, or parsing.

Outputs (default: outputs/topic_analysis/):
  - hashtag_summary.csv
  - domain_summary.csv
  - domain_category_summary.csv
  - figure_top_hashtags.png
  - figure_top_domains.png
  - figure_domain_categories.png
  - summary_topics_domains.md
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/slosky-matplotlib")

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from slosky.corpus import iter_jsonl


INCLUDED_DECISIONS = {
    "core_tag_supported",
    "review_model_consensus_only",
    "review_langid_only",
    "review_langdetect_only",
}

TOP_N = 20  # how many hashtags / domains to report in detail

# ---------------------------------------------------------------------------
# Explicit domain-category mapping (top domains only; others → "other")
# ---------------------------------------------------------------------------
DOMAIN_CATEGORIES: dict[str, str] = {
    # GIF / media sharing
    "media.tenor.com": "GIF / media sharing",
    "tenor.com":        "GIF / media sharing",
    "giphy.com":        "GIF / media sharing",
    # Slovene news media
    "n1info.si":        "Slovene news media",
    "rtvslo.si":        "Slovene news media",
    "tehnozvezdje.si":  "Slovene news media",
    "delo.si":          "Slovene news media",
    "siol.net":         "Slovene news media",
    "24ur.com":         "Slovene news media",
    "zurnal24.si":      "Slovene news media",
    "vecer.com":        "Slovene news media",
    "metropolitan.si":  "Slovene news media",
    "necenzurirano.si": "Slovene news media",
    "nova24tv.si":      "Slovene news media",
    "reporter.si":      "Slovene news media",
    "finance.si":       "Slovene news media",
    "sta.si":           "Slovene news media",
    "mladina.si":       "Slovene news media",
    # Platform tooling / Bluesky utilities
    "ebx.sh":           "Platform tooling / Bluesky utilities",
    "bsky.app":         "Platform tooling / Bluesky utilities",
    "bsky.social":      "Platform tooling / Bluesky utilities",
    "staging.bsky.app": "Platform tooling / Bluesky utilities",
    "atproto.com":      "Platform tooling / Bluesky utilities",
    "bskyfeed.app":     "Platform tooling / Bluesky utilities",
    "clearsky.app":     "Platform tooling / Bluesky utilities",
    "deck.blue":        "Platform tooling / Bluesky utilities",
    "blueskyfeed.app":  "Platform tooling / Bluesky utilities",
    # Video platforms
    "youtu.be":         "Video platforms",
    "youtube.com":      "Video platforms",
    "vimeo.com":        "Video platforms",
    # Social / cross-platform
    "twitter.com":      "Social / cross-platform",
    "x.com":            "Social / cross-platform",
    "instagram.com":    "Social / cross-platform",
    "mastodon.social":  "Social / cross-platform",
    "threads.net":      "Social / cross-platform",
    # Reference / encyclopaedic
    "en.wikipedia.org": "Reference / encyclopaedic",
    "sl.wikipedia.org": "Reference / encyclopaedic",
    "wikipedia.org":    "Reference / encyclopaedic",
    # Slovene news media (additional outlets found in corpus)
    "dnevnik.si":           "Slovene news media",
    "forbes.n1info.si":     "Slovene news media",
    "sportklub.n1info.si":  "Slovene news media",
    "365.rtvslo.si":        "Slovene news media",
    "val202.rtvslo.si":     "Slovene news media",
    "zurnal24.si":          "Slovene news media",
    "danesjenovdan.si":     "Slovene news media",
    # Music / audio streaming
    "open.spotify.com":     "Music / audio",
    "spotify.com":          "Music / audio",
    # Social / cross-platform (additions)
    "facebook.com":         "Social / cross-platform",
    "open.substack.com":    "Social / cross-platform",
    "substack.com":         "Social / cross-platform",
}

HASHTAG_RE = re.compile(r"#([A-Za-z0-9_À-ɏɐ-ʯ]+)", re.UNICODE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path,
        default=Path("outputs/final/final_sl_corpus.jsonl"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("outputs/topic_analysis"),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_corpus(path: Path) -> pd.DataFrame:
    rows = []
    for row in iter_jsonl(path):
        if row.get("decision") not in INCLUDED_DECISIONS:
            continue
        reply = bool(row.get("reply_flag"))
        quote = bool(row.get("quote_flag"))
        # Same hierarchy as rest of paper
        if reply:
            post_type = "reply"
        elif quote:
            post_type = "nonreply_quote"
        else:
            post_type = "original"

        rows.append({
            "author_did": row.get("author_did"),
            "text": row.get("text") or "",
            "link_domains": row.get("link_domains") or [],
            "post_type": post_type,
        })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# 1 + 2. Hashtag analysis
# ---------------------------------------------------------------------------

def analyze_hashtags(df: pd.DataFrame) -> pd.DataFrame:
    # Extract hashtags per post and track author
    tag_author_counts: dict[str, Counter] = defaultdict(Counter)
    posts_with_tag: set[int] = set()

    for idx, row in df.iterrows():
        tags = [t.lower() for t in HASHTAG_RE.findall(row["text"])]
        if tags:
            posts_with_tag.add(idx)
        for tag in tags:
            tag_author_counts[tag][row["author_did"]] += 1

    # Build summary
    records = []
    for tag, author_counter in tag_author_counts.items():
        total = sum(author_counter.values())
        top_count = author_counter.most_common(1)[0][1]
        records.append({
            "hashtag": f"#{tag}",
            "occurrences": total,
            "unique_authors": len(author_counter),
            "top_author_share": top_count / total,
        })

    summary = (
        pd.DataFrame(records)
        .sort_values("occurrences", ascending=False)
        .reset_index(drop=True)
    )
    summary.insert(0, "rank", range(1, len(summary) + 1))
    return summary, len(posts_with_tag)


# ---------------------------------------------------------------------------
# 3. Linked-domain analysis
# ---------------------------------------------------------------------------

def analyze_domains(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    domain_author_counts: dict[str, Counter] = defaultdict(Counter)
    posts_with_link: set[int] = set()

    for idx, row in df.iterrows():
        domains = row["link_domains"]
        if domains:
            posts_with_link.add(idx)
        for domain in domains:
            domain_author_counts[domain][row["author_did"]] += 1

    records = []
    for domain, author_counter in domain_author_counts.items():
        total = sum(author_counter.values())
        top_count = author_counter.most_common(1)[0][1]
        records.append({
            "domain": domain,
            "occurrences": total,
            "unique_authors": len(author_counter),
            "top_author_share": top_count / total,
            "category": DOMAIN_CATEGORIES.get(domain, "other"),
        })

    summary = (
        pd.DataFrame(records)
        .sort_values("occurrences", ascending=False)
        .reset_index(drop=True)
    )
    summary.insert(0, "rank", range(1, len(summary) + 1))
    return summary, len(posts_with_link)


# ---------------------------------------------------------------------------
# 4. Domain category summary
# ---------------------------------------------------------------------------

def analyze_domain_categories(domain_df: pd.DataFrame) -> pd.DataFrame:
    cat = (
        domain_df.groupby("category")
        .agg(total_occurrences=("occurrences", "sum"), n_domains=("domain", "count"))
        .sort_values("total_occurrences", ascending=False)
        .reset_index()
    )
    total = cat["total_occurrences"].sum()
    cat["share_pct"] = cat["total_occurrences"] / total * 100
    return cat


# ---------------------------------------------------------------------------
# 6. Optional post-type comparison
# ---------------------------------------------------------------------------

def link_share_by_post_type(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["has_link"] = df["link_domains"].apply(bool)
    result = (
        df.groupby("post_type")["has_link"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "posts_with_link", "count": "total_posts"})
        .reset_index()
    )
    result["link_share_pct"] = result["posts_with_link"] / result["total_posts"] * 100
    return result


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


def figure_top_hashtags(hashtag_df: pd.DataFrame, output_dir: Path) -> Path:
    top = hashtag_df.head(10).copy()
    # Colour by whether top-author contributes >50% (concentrated) or not
    colors = ["#FF7043" if row["top_author_share"] > 0.5 else "#42A5F5"
              for _, row in top.iterrows()]

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.barh(top["hashtag"][::-1], top["occurrences"][::-1],
                       color=colors[::-1], edgecolor="white")

        # Annotate with unique-author count
        for bar, (_, row) in zip(bars, top[::-1].iterrows()):
            ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2,
                    f"{row['unique_authors']} author{'s' if row['unique_authors'] != 1 else ''}",
                    va="center", ha="left", fontsize=8, color="#555")

        ax.set_xlabel("Occurrences")
        ax.set_title("Top 10 hashtags (orange = one author contributes >50% of uses)", fontsize=10)
        ax.margins(x=0.2)
        fig.tight_layout()

    path = output_dir / "figure_top_hashtags.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def figure_top_domains(domain_df: pd.DataFrame, output_dir: Path) -> Path:
    top = domain_df.head(10).copy()

    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.barh(top["domain"][::-1], top["occurrences"][::-1],
                       color="#42A5F5", edgecolor="white")

        for bar, (_, row) in zip(bars, top[::-1].iterrows()):
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                    f"{row['unique_authors']} authors",
                    va="center", ha="left", fontsize=8, color="#555")

        ax.set_xlabel("Occurrences")
        ax.set_title("Top 10 linked domains", fontsize=10)
        ax.margins(x=0.22)
        fig.tight_layout()

    path = output_dir / "figure_top_domains.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def figure_domain_categories(cat_df: pd.DataFrame, output_dir: Path) -> Path:
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 4.5))
        colors = plt.cm.tab10.colors
        ax.bar(cat_df["category"], cat_df["total_occurrences"],
               color=colors[:len(cat_df)], edgecolor="white")

        for i, row in cat_df.iterrows():
            ax.text(i, row["total_occurrences"] + 20,
                    f"{row['share_pct']:.1f}%",
                    ha="center", va="bottom", fontsize=8)

        ax.set_ylabel("Total occurrences")
        ax.set_title("Linked-domain occurrences by category", fontsize=10)
        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()

    path = output_dir / "figure_domain_categories.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 8 + 9. Markdown summary
# ---------------------------------------------------------------------------

def fmt_pct(v: float, d: int = 1) -> str:
    return f"{v:.{d}f}%"


def write_summary(
    output_dir: Path,
    total_posts: int,
    hashtag_df: pd.DataFrame,
    posts_with_hashtag: int,
    domain_df: pd.DataFrame,
    posts_with_link: int,
    cat_df: pd.DataFrame,
    link_by_type: pd.DataFrame,
) -> Path:
    top20_tags = hashtag_df.head(TOP_N)
    concentrated_tags = top20_tags[top20_tags["top_author_share"] > 0.5]
    top20_domains = domain_df.head(TOP_N)
    concentrated_domains = top20_domains[top20_domains["top_author_share"] > 0.5]

    lines: list[str] = []
    lines += [
        "# Topics and Domains Analysis",
        "",
        f"Total posts: {total_posts:,}",
        "",
        "## Hashtag overview",
        "",
        f"Posts containing at least one hashtag: {posts_with_hashtag:,} "
        f"({posts_with_hashtag/total_posts*100:.1f}% of corpus)",
        f"Distinct hashtags observed: {len(hashtag_df):,}",
        f"Top-20 hashtags where one author contributes >50% of uses: "
        f"{len(concentrated_tags)} of {len(top20_tags)}",
        "",
        "### Top 20 hashtags",
        "",
        _df_to_md(top20_tags.assign(top_author_share=top20_tags["top_author_share"].map("{:.2f}".format))),
        "",
        "## Domain overview",
        "",
        f"Posts containing at least one external domain: {posts_with_link:,} "
        f"({posts_with_link/total_posts*100:.1f}% of corpus)",
        f"Distinct domains observed: {len(domain_df):,}",
        f"Top-20 domains where one author contributes >50% of uses: "
        f"{len(concentrated_domains)} of {len(top20_domains)}",
        "",
        "### Top 20 domains",
        "",
        _df_to_md(
            top20_domains[["rank","domain","occurrences","unique_authors","top_author_share","category"]]
            .assign(top_author_share=top20_domains["top_author_share"].map("{:.2f}".format))
        ),
        "",
        "## Domain categories",
        "",
        _df_to_md(cat_df.assign(share_pct=cat_df["share_pct"].map("{:.1f}%".format))),
        "",
        "## Link share by post type",
        "",
        _df_to_md(link_by_type.assign(link_share_pct=link_by_type["link_share_pct"].map("{:.1f}%".format))),
        "",
        "## Interpretation bullets (suitable for paper adaptation)",
        "",
        _bullets(
            total_posts, hashtag_df, posts_with_hashtag,
            domain_df, posts_with_link, cat_df, concentrated_tags, link_by_type
        ),
        "",
        "## Suggested paragraph for Section 5.6",
        "",
        _paragraph(
            total_posts, hashtag_df, posts_with_hashtag,
            domain_df, posts_with_link, cat_df, concentrated_tags, link_by_type
        ),
        "",
    ]

    path = output_dir / "summary_topics_domains.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _df_to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join([header, sep] + rows)


def _bullets(
    total_posts, hashtag_df, posts_with_hashtag,
    domain_df, posts_with_link, cat_df, concentrated_tags, link_by_type
) -> str:
    top_tag = hashtag_df.iloc[0]
    top_domain = domain_df.iloc[0]
    cat_index = cat_df.set_index("category")
    gif_occ = cat_index.loc["GIF / media sharing", "total_occurrences"] if "GIF / media sharing" in cat_index.index else 0
    news_occ = cat_index.loc["Slovene news media", "total_occurrences"] if "Slovene news media" in cat_index.index else 0
    tool_occ = cat_index.loc["Platform tooling / Bluesky utilities", "total_occurrences"] if "Platform tooling / Bluesky utilities" in cat_index.index else 0
    total_domain_occ = cat_df["total_occurrences"].sum()

    reply_link = link_by_type.set_index("post_type").get("link_share_pct", pd.Series())
    orig_share = reply_link.get("original", float("nan"))
    reply_share = reply_link.get("reply", float("nan"))

    bullets = [
        f"Hashtag use is sparse: only {posts_with_hashtag:,} of {total_posts:,} posts "
        f"({posts_with_hashtag/total_posts*100:.1f}\\%) contain at least one hashtag, "
        "suggesting that the corpus is not organised around broad hashtag publics.",

        f"Of the top 20 hashtags, {len(concentrated_tags)} have a single author "
        "contributing more than 50\\% of all uses, indicating that a substantial share "
        "of visible hashtag activity reflects repeated self-tagging by a small number of accounts "
        f"rather than community-wide adoption. The most frequent hashtag, "
        f"\\texttt{{{top_tag['hashtag']}}}, appears {top_tag['occurrences']:,} times "
        f"across {top_tag['unique_authors']} unique author(s).",

        f"External link sharing is more common than hashtagging: {posts_with_link:,} posts "
        f"({posts_with_link/total_posts*100:.1f}\\%) contain at least one external domain.",

        f"The most frequently linked domain is \\texttt{{{top_domain['domain']}}} "
        f"({top_domain['occurrences']:,} posts, {top_domain['unique_authors']} unique authors), "
        "indicating that GIF sharing is a prominent form of informal interaction in the corpus.",

        f"By category, GIF/media sharing accounts for "
        f"{gif_occ/total_domain_occ*100:.1f}\\% of all domain occurrences, "
        f"Slovene news media for {news_occ/total_domain_occ*100:.1f}\\%, and "
        f"platform tooling/Bluesky utilities for {tool_occ/total_domain_occ*100:.1f}\\%. "
        "Together these three categories account for the large majority of linked content.",

        f"News-media linking is distributed across several Slovene outlets, suggesting "
        "recurring current-affairs engagement rather than concentration on a single source.",

        f"Link-sharing rates differ by post type: original posts link to external content "
        f"at {orig_share:.1f}\\% compared with {reply_share:.1f}\\% for replies, "
        "consistent with replies serving primarily as conversational turns rather than "
        "content-sharing acts.",
    ]

    return "\n".join(f"- {b}" for b in bullets)


def _paragraph(
    total_posts, hashtag_df, posts_with_hashtag,
    domain_df, posts_with_link, cat_df, concentrated_tags, link_by_type
) -> str:
    top_tag = hashtag_df.iloc[0]
    top_domain = domain_df.iloc[0]
    cat_index = cat_df.set_index("category")
    gif_occ = cat_index.loc["GIF / media sharing", "total_occurrences"] if "GIF / media sharing" in cat_index.index else 0
    news_occ = cat_index.loc["Slovene news media", "total_occurrences"] if "Slovene news media" in cat_index.index else 0
    total_domain_occ = cat_df["total_occurrences"].sum()

    reply_link = link_by_type.set_index("post_type").get("link_share_pct", pd.Series(dtype=float))
    orig_share = reply_link.get("original", float("nan"))
    reply_share_val = reply_link.get("reply", float("nan"))

    return (
        f"Hashtag use is sparse throughout the corpus: only {posts_with_hashtag:,} of "
        f"{total_posts:,} posts ({posts_with_hashtag/total_posts*100:.1f}\\%) contain at least one hashtag. "
        f"Of the 20 most frequent hashtags, {len(concentrated_tags)} have a single author "
        "contributing more than half of all uses, indicating that much of the visible hashtag "
        "activity reflects self-tagging by a small number of accounts rather than community-wide "
        "thematic organisation. The most frequent hashtag, "
        f"\\texttt{{{top_tag['hashtag']}}}, appears {top_tag['occurrences']:,} times "
        f"but is used by only {top_tag['unique_authors']} unique author(s). "
        f"External link sharing is more prevalent: {posts_with_link:,} posts "
        f"({posts_with_link/total_posts*100:.1f}\\%) contain at least one external domain. "
        f"The single most linked domain is \\texttt{{{top_domain['domain']}}} "
        f"({top_domain['occurrences']:,} occurrences), reflecting frequent GIF-based informal exchange. "
        f"Across all linked domains, GIF and media-sharing services account for "
        f"{gif_occ/total_domain_occ*100:.1f}\\% of domain occurrences and Slovene news outlets "
        f"for {news_occ/total_domain_occ*100:.1f}\\%, distributed across several titles. "
        f"Link-sharing rates differ by post type ({orig_share:.1f}\\% of original posts "
        f"vs.\\ {reply_share_val:.1f}\\% of replies contain an external link), consistent "
        "with replies functioning primarily as conversational turns. Together, these patterns "
        "suggest a small, conversational space oriented around informal exchange and recurring "
        "news-media engagement, rather than one organised primarily around hashtag-driven "
        "topic publics."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading corpus…")
    df = load_corpus(args.input)
    total = len(df)
    print(f"  {total:,} posts, {df['author_did'].nunique():,} authors")

    print("Analysing hashtags…")
    hashtag_df, posts_with_hashtag = analyze_hashtags(df)
    hashtag_df.to_csv(args.output_dir / "hashtag_summary.csv", index=False, float_format="%.4f")

    print("Analysing domains…")
    domain_df, posts_with_link = analyze_domains(df)
    domain_df.to_csv(args.output_dir / "domain_summary.csv", index=False, float_format="%.4f")

    print("Building domain categories…")
    cat_df = analyze_domain_categories(domain_df)
    cat_df.to_csv(args.output_dir / "domain_category_summary.csv", index=False, float_format="%.4f")

    print("Post-type link comparison…")
    link_by_type = link_share_by_post_type(df)

    print("Saving figures…")
    figure_top_hashtags(hashtag_df, args.output_dir)
    figure_top_domains(domain_df, args.output_dir)
    figure_domain_categories(cat_df, args.output_dir)

    print("Writing summary…")
    summary_path = write_summary(
        args.output_dir, total, hashtag_df, posts_with_hashtag,
        domain_df, posts_with_link, cat_df, link_by_type,
    )

    # Quick stdout report
    top20 = hashtag_df.head(TOP_N)
    conc = top20[top20["top_author_share"] > 0.5]
    print(f"\n=== Key results ===")
    print(f"Posts with hashtag: {posts_with_hashtag:,} ({posts_with_hashtag/total*100:.1f}%)")
    print(f"Concentrated top-20 hashtags (>50% one author): {len(conc)}/{len(top20)}")
    print(f"Posts with external link: {posts_with_link:,} ({posts_with_link/total*100:.1f}%)")
    print(f"\nTop 5 hashtags:")
    for _, row in hashtag_df.head(5).iterrows():
        print(f"  {row['hashtag']}: {row['occurrences']} occ, {row['unique_authors']} authors, top-author {row['top_author_share']:.0%}")
    print(f"\nTop 5 domains:")
    for _, row in domain_df.head(5).iterrows():
        print(f"  {row['domain']}: {row['occurrences']} occ, {row['unique_authors']} authors [{row['category']}]")
    print(f"\nDomain categories:")
    for _, row in cat_df.iterrows():
        print(f"  {row['category']}: {row['total_occurrences']:,} ({row['share_pct']:.1f}%)")
    print(f"\nLink share by post type:")
    for _, row in link_by_type.iterrows():
        print(f"  {row['post_type']}: {row['link_share_pct']:.1f}%")
    print(f"\nSummary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

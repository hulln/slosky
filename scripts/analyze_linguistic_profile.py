#!/usr/bin/env python3
"""Lexical and morphosyntactic profile of an annotated corpus.

Reads either

  - the annotated JSONL written by scripts/annotate_release_corpus.py, or
  - a CoNLL-U file (used to compute the same statistics over a reference corpus
    such as SUK 1.0, so the comparison in the paper is computed by identical code
    rather than lifted from published figures)

and writes a JSON summary plus CSV frequency tables.

All statistics come from the CLASSLA XPOS/MSD column, not from a Universal
Dependencies layer. Two reasons: MSD is the tagset the Slovene reference corpora
(ssj500k, SUK, Gigafida, Janes) actually use, so comparison is native rather than
cross-tagset; and CLASSLA's Slovene non-standard models are trained in part on
JANES-lineage computer-mediated communication, whereas no UD parser trained on CMC is
available (the released ones cover standard written and transcribed spoken Slovene)
and dependency parsing is the least reliable layer on this register.

Usage:
    python3 scripts/analyze_linguistic_profile.py \
        --input outputs/annotated/slosky_corpus_anon_classla-trankit.jsonl \
        --output-dir outputs/analysis --label slosky
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

# --- MULTEXT-East / JOS morphosyntactic descriptions -------------------------------
#
# The Slovene MSD exists in two notations whose leading letters conflict outright:
# "S" opens a noun in the Slovene notation but an adposition in the English one, and
# "V" opens a verb in English but a conjunction in Slovene. Guessing wrong silently
# swaps the two headline word classes in the paper, so the notation is detected from
# the data and the run aborts if it cannot be established.

WORD_CLASS_EN = {
    "N": "noun", "V": "verb", "A": "adjective", "R": "adverb", "P": "pronoun",
    "M": "numeral", "S": "adposition", "C": "conjunction", "Q": "particle",
    "I": "interjection", "Y": "abbreviation", "X": "residual", "Z": "punctuation",
}
WORD_CLASS_SL = {
    "S": "noun", "G": "verb", "P": "adjective", "R": "adverb", "Z": "pronoun",
    "K": "numeral", "D": "adposition", "V": "conjunction", "L": "particle",
    "M": "interjection", "O": "abbreviation", "N": "residual", "U": "punctuation",
}

# Verb form and person live at MSD positions 4 and 5 (1-indexed) in both notations.
# Finite forms only: present, future, conditional, imperative.
VERB_FINITE_EN = set("rfcm")
VERB_PERSON_EN = {"1": "1", "2": "2", "3": "3"}
VERB_FINITE_SL = set("spgv")
VERB_PERSON_SL = {"p": "1", "d": "2", "t": "3"}

# Residual subcategories. Janes extends MULTEXT-East residuals for CMC text; these are
# what make a token-level code-switching and emoji measure possible at all.
RESIDUAL_SUBTYPES = {
    "f": "foreign", "t": "typo", "e": "emoji", "w": "url", "h": "hashtag", "a": "mention",
}
# Excluded from the "word" count: punctuation and the non-linguistic residuals.
NON_WORD_CLASSES = {"punctuation"}
NON_WORD_RESIDUALS = {"emoji", "url", "hashtag", "mention"}

PSEUDONYM_RE = re.compile(r"^@(?:author|external)_\d+$")
MATTR_WINDOW = 1000

# The Xe/Xw/Xh/Xa residual subtypes above are JANES extensions to MULTEXT-East.
# CLASSLA's models may or may not emit them depending on the training data, and if
# they are absent every emoji and URL silently counts as a "word", inflating the
# token/type totals that get compared against reference corpora. So non-words are
# also detected from the surface form, independently of the tagset.
URL_RE = re.compile(r"^(?:https?://|www\.)\S+$|^\S+\.(?:com|org|net|si|io|ly)/?\S*$", re.I)
MENTION_RE = re.compile(r"^@\S+$")
HASHTAG_RE = re.compile(r"^#\S+$")
# Any token containing no letter and no digit is punctuation, emoji or symbol.
HAS_ALNUM_RE = re.compile(r"[^\W_]", re.UNICODE)


def is_non_word_form(form: str) -> bool:
    """True for tokens that should not count as words, judged from the form alone."""
    if not form:
        return True
    return bool(
        URL_RE.match(form)
        or MENTION_RE.match(form)
        or HASHTAG_RE.match(form)
        or not HAS_ALNUM_RE.search(form)
    )


def pct(part: int, whole: int, decimals: int = 1) -> float:
    return round(part / whole * 100, decimals) if whole else 0.0


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def detect_notation(xpos_samples: Iterable[str]) -> str:
    """Decide whether MSDs use the English or Slovene MULTEXT-East notation.

    Scores each notation by how many sampled tags start with a letter valid in it,
    then requires a clear winner. Refuses to guess: an undetected notation would
    silently swap nouns and verbs in the reported distribution.
    """
    samples = [tag for tag in xpos_samples if tag and tag != "_"]
    if not samples:
        raise SystemExit("No XPOS/MSD values found - cannot determine tagset notation.")

    en_only = set(WORD_CLASS_EN) - set(WORD_CLASS_SL)   # A C I M Q Y
    sl_only = set(WORD_CLASS_SL) - set(WORD_CLASS_EN)   # G K L O U D
    en_hits = sum(1 for tag in samples if tag[0] in en_only)
    sl_hits = sum(1 for tag in samples if tag[0] in sl_only)

    if en_hits > sl_hits * 3 and en_hits > 0:
        return "en"
    if sl_hits > en_hits * 3 and sl_hits > 0:
        return "sl"
    raise SystemExit(
        "Could not confidently determine MSD notation "
        f"(English-only leading letters: {en_hits}, Slovene-only: {sl_hits}). "
        f"Sample tags: {samples[:15]}. Inspect the data before trusting any counts."
    )


class Profile:
    """Accumulates counts for one subset of the corpus (all / replies / originals)."""

    def __init__(self, notation: str) -> None:
        self.notation = notation
        self.classes = WORD_CLASS_EN if notation == "en" else WORD_CLASS_SL
        self.finite = VERB_FINITE_EN if notation == "en" else VERB_FINITE_SL
        self.persons = VERB_PERSON_EN if notation == "en" else VERB_PERSON_SL

        self.posts = 0
        self.sentences = 0
        self.tokens = 0
        self.words = 0
        self.token_class = Counter()   # every token, including punctuation
        self.word_class = Counter()    # words only; this is what gets reported
        self.residual = Counter()
        self.word_forms = Counter()
        self.lemmas = Counter()
        self.noun_lemmas = Counter()
        self.verb_person = Counter()
        self.finite_verbs = 0
        self.words_per_post: list[int] = []
        self._window: list[str] = []
        self._mattr_sum = 0.0
        self._mattr_n = 0

    def _mattr_push(self, form: str) -> None:
        """Moving-average type-token ratio over a fixed window of word tokens.

        Raw TTR is not comparable across corpora of different sizes, which matters
        here because the reply subcorpus is nearly twice the size of the originals.
        """
        self._window.append(form)
        if len(self._window) > MATTR_WINDOW:
            self._window.pop(0)
        if len(self._window) == MATTR_WINDOW:
            self._mattr_sum += len(set(self._window)) / MATTR_WINDOW
            self._mattr_n += 1

    def add_post(self, sentences: list[dict[str, Any]]) -> None:
        self.posts += 1
        words_here = 0
        for sentence in sentences:
            self.sentences += 1
            for token in sentence["tokens"]:
                self.tokens += 1
                xpos = (token.get("xpos") or "").strip()
                form = (token.get("form") or "").strip()
                lemma = (token.get("lemma") or "").strip()
                if not xpos or xpos == "_":
                    continue

                wclass = self.classes.get(xpos[0], "unknown")
                self.token_class[wclass] += 1

                if wclass == "residual" and len(xpos) > 1:
                    self.residual[RESIDUAL_SUBTYPES.get(xpos[1].lower(), "other")] += 1

                is_residual_nonword = (
                    wclass == "residual"
                    and len(xpos) > 1
                    and RESIDUAL_SUBTYPES.get(xpos[1].lower()) in NON_WORD_RESIDUALS
                )
                # Belt and braces: the tagset test catches JANES-style residuals, the
                # form test catches the same material when the model does not emit them.
                if wclass in NON_WORD_CLASSES or is_residual_nonword or is_non_word_form(form):
                    continue
                if PSEUDONYM_RE.match(form):
                    continue

                self.words += 1
                words_here += 1
                # Word-class shares are reported over words, so the class is only
                # tallied here — after punctuation and non-linguistic tokens are out.
                self.word_class[wclass] += 1
                lowered = form.lower()
                self.word_forms[lowered] += 1
                self._mattr_push(lowered)
                if lemma and lemma != "_":
                    self.lemmas[lemma.lower()] += 1

                # Finiteness is decided at position 4 (verb form). Person lives at
                # position 5, but not every finite form has one: the Slovene
                # conditional auxiliary "bi" is invariant and tags as a 4-character
                # Va-c, so requiring 5 characters here would silently drop ~6k finite
                # verbs from SUK alone and inflate the first/second-person share.
                if wclass == "verb" and len(xpos) >= 4:
                    if xpos[3].lower() in self.finite:
                        self.finite_verbs += 1
                        if len(xpos) >= 5:
                            person = self.persons.get(xpos[4].lower())
                            if person:
                                self.verb_person[person] += 1
                # Common nouns only: position 2 is 'c'/'o' (common) vs 'p'/'l' (proper).
                if wclass == "noun" and len(xpos) >= 2 and xpos[1].lower() in {"c", "o"}:
                    if lemma and lemma != "_":
                        self.noun_lemmas[lemma.lower()] += 1

        self.words_per_post.append(words_here)

    def summary(self) -> dict[str, Any]:
        types = len(self.word_forms)
        hapax = sum(1 for count in self.word_forms.values() if count == 1)
        nouns = self.word_class.get("noun", 0)
        verbs = self.word_class.get("verb", 0)
        first_second = self.verb_person.get("1", 0) + self.verb_person.get("2", 0)
        # statistics.median averages the two central values on an even-sized sample;
        # lengths[n//2] silently returns the upper of the two.
        median = statistics.median(self.words_per_post) if self.words_per_post else 0
        return {
            "posts": self.posts,
            "sentences": self.sentences,
            "tokens": self.tokens,
            "words": self.words,
            "word_types": types,
            "lemma_types": len(self.lemmas),
            "hapax_types": hapax,
            "hapax_pct_of_types": pct(hapax, types),
            "raw_ttr": round(types / self.words, 4) if self.words else 0.0,
            "mattr_1000": round(self._mattr_sum / self._mattr_n, 4) if self._mattr_n else None,
            "median_words_per_post": median,
            "mean_words_per_post": round(self.words / self.posts, 2) if self.posts else 0.0,
            "word_class_pct": {
                name: pct(count, self.words)
                for name, count in sorted(self.word_class.items(), key=lambda kv: -kv[1])
            },
            "word_class_counts": dict(self.word_class.most_common()),
            "token_class_counts": dict(self.token_class.most_common()),
            "noun_verb_ratio": round(nouns / verbs, 2) if verbs else None,
            "finite_verbs": self.finite_verbs,
            "finite_verb_person_counts": dict(self.verb_person),
            "first_second_person_finite_pct": pct(first_second, self.finite_verbs),
            "residual_subtypes": dict(self.residual.most_common()),
            "foreign_token_pct_of_words": pct(self.residual.get("foreign", 0), self.words),
            "top_common_noun_lemmas": dict(self.noun_lemmas.most_common(20)),
        }


def iter_conllu_docs(path: Path) -> Iterator[list[dict[str, Any]]]:
    """Yield one 'document' per CoNLL-U sentence, for reference-corpus input."""
    tokens: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                if tokens:
                    yield [{"tokens": tokens}]
                    tokens = []
                continue
            if line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 5 or "-" in cols[0] or "." in cols[0]:
                continue  # skip multiword-token ranges and empty nodes
            tokens.append({"form": cols[1], "lemma": cols[2], "xpos": cols[4]})
    if tokens:
        yield [{"tokens": tokens}]


def sample_xpos(path: Path, limit: int = 4000) -> list[str]:
    tags: list[str] = []
    if path.suffix == ".conllu":
        for doc in iter_conllu_docs(path):
            for sentence in doc:
                tags.extend(t["xpos"] for t in sentence["tokens"])
            if len(tags) >= limit:
                break
    else:
        for row in iter_jsonl(path):
            for sentence in row.get("sentences", []):
                tags.extend((t.get("xpos") or "") for t in sentence["tokens"])
            if len(tags) >= limit:
                break
    return tags[:limit]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--label", default="slosky", help="Prefix for output filenames.")
    parser.add_argument("--limit", type=int, help="Process only the first N posts.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    notation = detect_notation(sample_xpos(args.input))
    print(f"MSD notation detected: {notation}", file=sys.stderr)

    subsets = {"all": Profile(notation)}
    is_conllu = args.input.suffix == ".conllu"
    if not is_conllu:
        subsets["reply"] = Profile(notation)
        subsets["original"] = Profile(notation)
        subsets["quote"] = Profile(notation)

    if is_conllu:
        for count, doc in enumerate(iter_conllu_docs(args.input), start=1):
            if args.limit and count > args.limit:
                break
            subsets["all"].add_post(doc)
    else:
        for count, row in enumerate(iter_jsonl(args.input), start=1):
            if args.limit and count > args.limit:
                break
            sentences = row.get("sentences", [])
            subsets["all"].add_post(sentences)
            if row.get("reply_flag"):
                subsets["reply"].add_post(sentences)
            elif row.get("quote_flag"):
                subsets["quote"].add_post(sentences)
            else:
                subsets["original"].add_post(sentences)
            if count % 20000 == 0:
                print(f"  {count:,} posts...", file=sys.stderr)

    summary = {
        "input": str(args.input),
        "msd_notation": notation,
        "mattr_window": MATTR_WINDOW,
        "subsets": {name: profile.summary() for name, profile in subsets.items()},
    }

    json_path = args.output_dir / f"{args.label}_linguistic_profile.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  -> {json_path}")

    csv_path = args.output_dir / f"{args.label}_top_noun_lemmas.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["lemma", "count", "pct_of_words"])
        total_words = subsets["all"].words
        for lemma, count in subsets["all"].noun_lemmas.most_common(100):
            writer.writerow([lemma, count, pct(count, total_words, 3)])
    print(f"  -> {csv_path}")

    top = subsets["all"].summary()
    print()
    print("=" * 62)
    print(f"LINGUISTIC PROFILE  ({args.label}, MSD notation: {notation})")
    print("=" * 62)
    print(f"Posts:      {top['posts']:,}")
    print(f"Sentences:  {top['sentences']:,}")
    print(f"Tokens:     {top['tokens']:,}")
    print(f"Words:      {top['words']:,}   (excl. punctuation, emoji, URLs, mentions)")
    print(f"Word types: {top['word_types']:,}   Lemma types: {top['lemma_types']:,}")
    print(f"Hapax:      {top['hapax_pct_of_types']}% of types")
    print(f"Raw TTR:    {top['raw_ttr']}   MATTR({MATTR_WINDOW}): {top['mattr_1000']}")
    print(f"Noun/verb ratio: {top['noun_verb_ratio']}")
    print(f"1st/2nd person finite verbs: {top['first_second_person_finite_pct']}% "
          f"of {top['finite_verbs']:,} finite verbs")
    print()
    print("Word classes (% of words):")
    for name, value in list(top["word_class_pct"].items())[:10]:
        print(f"  {name:<14} {value:>6}%")
    if top["residual_subtypes"]:
        print()
        print("Residual subtypes:", top["residual_subtypes"])
    print()
    print("Top 15 common-noun lemmas:")
    for rank, (lemma, count) in enumerate(list(top["top_common_noun_lemmas"].items())[:15], 1):
        print(f"  {rank:2}. {lemma:<22} {count:,}")

    for name in ("reply", "original"):
        if name in subsets and subsets[name].posts:
            sub = subsets[name].summary()
            print()
            print(f"{name}: {sub['words']:,} words | MATTR {sub['mattr_1000']} | "
                  f"raw TTR {sub['raw_ttr']} | N/V {sub['noun_verb_ratio']} | "
                  f"1st/2nd person {sub['first_second_person_finite_pct']}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

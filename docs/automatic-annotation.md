# Automatic Annotation Layer

The released corpus can be extended with an automatic linguistic annotation layer
without changing the original release files.

## Recommended Pipeline

Use a hybrid annotation setup:

- CLASSLA provides sentence segmentation and tokenization.
- CLASSLA provides lemmas and Slovene XPOS/MSD tags.
- Trankit provides the canonical UD layer: UPOS, FEATS, HEAD, and DEPREL.
- Trankit is run on CLASSLA-pretokenized sentences, so token and sentence
  boundaries remain stable.
- Trankit uses the `xlm-roberta-large` model family by default.

This reflects the current evaluation result that Trankit is stronger for UD
parsing on SSJ/SST, while CLASSLA is still the better choice for Slovene-aware
tokenization and web/social-media text handling.

## Run

Test on a small sample first:

```bash
.venv-annot/bin/python scripts/annotate_release_corpus.py --limit 100
```

Full released corpus:

```bash
.venv-annot/bin/python scripts/annotate_release_corpus.py
```

Default inputs and outputs:

- input: `outputs/release/slosky_corpus_anon.jsonl`
- annotated JSONL: `outputs/annotated/slosky_corpus_anon_classla-trankit.jsonl`
- CoNLL-U: `outputs/annotated/slosky_corpus_anon_classla-trankit.conllu`
- metadata: `outputs/annotated/slosky_corpus_anon_classla-trankit.jsonl.meta.json`

The original corpus remains the canonical text release. The annotation files are
an additive derived resource.

## Validation

The pipeline was smoke-tested on the first 100 released posts with
`xlm-roberta-large` on CPU:

- posts: 100
- sentences: 333
- tokens: 3,651

The generated JSONL contained 100 rows, and the CoNLL-U file contained 333
sentence blocks. On a CPU-only run this quality-first setup is slow; the full
141,013-post corpus should be treated as an overnight/multi-day batch job unless
GPU execution is available.

## Suggested Release Description

The corpus was automatically annotated with a hybrid Slovene NLP pipeline. Posts
were sentence-segmented and tokenized with CLASSLA-Stanza using the Slovene web
model. Lemmas and Slovene XPOS/MSD tags were taken from CLASSLA. Universal
Dependencies POS tags, morphological features, heads, and dependency relations
were assigned with Trankit using the XLM-RoBERTa-large model family and the
CLASSLA tokenization as pretokenized input. The annotation is automatic and
should be treated as a derived layer rather than manual gold annotation.

## Environment Note

The tested environment uses the newest PyPI releases available for the two
pipeline libraries, with dependency pins chosen to satisfy Trankit's current
Torch constraint:

```bash
python3 -m venv .venv-annot
.venv-annot/bin/python -m pip install -r requirements-annotation.txt
```

The default run uses `--trankit-embedding xlm-roberta-large`. The Slovene
Trankit model can be downloaded automatically by Trankit; if the original
Trankit model server is unavailable, the same model files are also mirrored in
the Hugging Face `uonlp/trankit` repository under
`models/v1.0.0/xlm-roberta-large/slovenian.zip`.

CLASSLA downloads the Slovene `web`/nonstandard resources on first use when
`--download-missing-models` is passed.

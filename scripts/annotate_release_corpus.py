#!/usr/bin/env python3
"""Create an automatic morphosyntactic/UD annotation layer for the released corpus.

The existing release corpus is left unchanged. This script reads the released
anonymized JSONL, tokenizes and sentence-splits each post with CLASSLA, runs
Trankit on the CLASSLA-pretokenized sentences for the UD layer, and writes:

  - an annotated JSONL with the original released fields plus sentence/token data
  - a CoNLL-U file for corpus/NLP tooling
  - a metadata JSON file documenting the tool split and run settings

Default canonical columns:
  FORM/tokenization: CLASSLA
  LEMMA: CLASSLA
  XPOS/MSD: CLASSLA
  UPOS/FEATS/HEAD/DEPREL: Trankit
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Iterable


DEFAULT_INPUT = Path("outputs/release/slosky_corpus_anon.jsonl")
DEFAULT_OUTPUT_JSONL = Path("outputs/annotated/slosky_corpus_anon_classla-trankit.jsonl")
DEFAULT_OUTPUT_CONLLU = Path("outputs/annotated/slosky_corpus_anon_classla-trankit.conllu")


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def json_dump(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))


def conllu_comment_value(value: Any) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").strip()


def conllu_field(value: Any) -> str:
    if value is None or value == "":
        return "_"
    return str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def misc_atom(value: Any) -> str:
    text = conllu_field(value)
    return (
        text.replace(" ", "%20")
        .replace("\t", "%09")
        .replace("|", "%7C")
        .replace("=", "%3D")
    )


def normalize_feats(value: Any) -> str:
    if value is None or value == "":
        return "_"
    if isinstance(value, dict):
        return "|".join(f"{key}={value[key]}" for key in sorted(value))
    return str(value)


def require_import(module_name: str, install_hint: str) -> Any:
    try:
        return __import__(module_name)
    except Exception as exc:  # noqa: BLE001 - preserve the original dependency error.
        raise SystemExit(
            f"Could not import {module_name!r}: {exc}\n\n{install_hint}"
        ) from exc


def init_classla_pipeline(args: argparse.Namespace) -> Any:
    classla = require_import(
        "classla",
        "Install CLASSLA and its Slovene models, for example:\n"
        "  pip install classla\n"
        "  python -c \"import classla; classla.download('sl', type='web')\"",
    )
    if args.download_missing_models:
        download_kwargs: dict[str, Any] = {}
        if args.classla_type != "standard":
            download_kwargs["type"] = args.classla_type
        classla.download("sl", **download_kwargs)

    pipeline_kwargs: dict[str, Any] = {
        "processors": "tokenize,pos,lemma",
        "use_gpu": args.gpu,
    }
    if args.classla_type != "standard":
        pipeline_kwargs["type"] = args.classla_type
    return classla, classla.Pipeline("sl", **pipeline_kwargs)


def init_trankit_pipeline(args: argparse.Namespace) -> Any:
    trankit = require_import(
        "trankit",
        "Install Trankit with a compatible torch/transformers stack, for example:\n"
        "  pip install trankit\n\n"
        "If import fails inside transformers with missing torch attributes, use a\n"
        "matching torch/transformers pair rather than changing the corpus script.",
    )
    pipeline_kwargs: dict[str, Any] = {
        "lang": args.trankit_language,
        "gpu": args.gpu,
        "embedding": args.trankit_embedding,
    }
    if args.trankit_cache_dir:
        pipeline_kwargs["cache_dir"] = str(args.trankit_cache_dir)
    return trankit, trankit.Pipeline(**pipeline_kwargs)


def classla_token_value(word: Any, name: str) -> Any:
    return getattr(word, name, None)


def classla_sentences(doc: Any) -> list[dict[str, Any]]:
    sentences: list[dict[str, Any]] = []
    for sent_index, sentence in enumerate(getattr(doc, "sentences", []), start=1):
        words = []
        for word in getattr(sentence, "words", []):
            words.append(
                {
                    "id": classla_token_value(word, "id"),
                    "form": classla_token_value(word, "text"),
                    "lemma": classla_token_value(word, "lemma"),
                    "upos": classla_token_value(word, "upos"),
                    "xpos": classla_token_value(word, "xpos"),
                    "feats": normalize_feats(classla_token_value(word, "feats")),
                    "misc": conllu_field(classla_token_value(word, "misc")),
                }
            )
        sentences.append(
            {
                "id": sent_index,
                "text": conllu_comment_value(getattr(sentence, "text", "")),
                "tokens": words,
            }
        )
    return sentences


def trankit_sentence_tokens(sentence: dict[str, Any]) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for token in sentence.get("tokens", []):
        expanded = token.get("expanded")
        if expanded:
            tokens.extend(expanded)
        else:
            tokens.append(token)
    return tokens


def annotate_row(row: dict[str, Any], classla_pipeline: Any, trankit_pipeline: Any) -> dict[str, Any]:
    text = row.get("text") or ""
    classla_doc = classla_pipeline(text)
    sentences = classla_sentences(classla_doc)
    pretokenized = [[token["form"] for token in sentence["tokens"]] for sentence in sentences]

    if pretokenized:
        trankit_doc = trankit_pipeline.posdep(pretokenized)
        trankit_sentences = trankit_doc.get("sentences", [])
    else:
        trankit_sentences = []

    if len(sentences) != len(trankit_sentences):
        raise ValueError(
            f"Sentence mismatch for {row.get('post_id') or row.get('uri')}: "
            f"CLASSLA={len(sentences)} Trankit={len(trankit_sentences)}"
        )

    merged_sentences: list[dict[str, Any]] = []
    for classla_sentence, trankit_sentence in zip(sentences, trankit_sentences):
        classla_tokens = classla_sentence["tokens"]
        trankit_tokens = trankit_sentence_tokens(trankit_sentence)
        if len(classla_tokens) != len(trankit_tokens):
            raise ValueError(
                f"Token mismatch for {row.get('post_id') or row.get('uri')} "
                f"sentence {classla_sentence['id']}: "
                f"CLASSLA={len(classla_tokens)} Trankit={len(trankit_tokens)}"
            )

        tokens: list[dict[str, Any]] = []
        for token_index, (classla_token, trankit_token) in enumerate(
            zip(classla_tokens, trankit_tokens), start=1
        ):
            if classla_token["form"] != trankit_token.get("text"):
                raise ValueError(
                    f"Token text mismatch for {row.get('post_id') or row.get('uri')} "
                    f"sentence {classla_sentence['id']} token {token_index}: "
                    f"CLASSLA={classla_token['form']!r} Trankit={trankit_token.get('text')!r}"
                )

            tokens.append(
                {
                    "id": token_index,
                    "form": classla_token["form"],
                    "lemma": classla_token["lemma"],
                    "upos": trankit_token.get("upos") or classla_token["upos"],
                    "xpos": classla_token["xpos"],
                    "feats": normalize_feats(trankit_token.get("feats")),
                    "head": trankit_token.get("head"),
                    "deprel": trankit_token.get("deprel"),
                    "classla": {
                        "lemma": classla_token["lemma"],
                        "upos": classla_token["upos"],
                        "xpos": classla_token["xpos"],
                        "feats": classla_token["feats"],
                        "misc": classla_token["misc"],
                    },
                    "trankit": {
                        "lemma": trankit_token.get("lemma"),
                        "upos": trankit_token.get("upos"),
                        "xpos": trankit_token.get("xpos"),
                        "feats": normalize_feats(trankit_token.get("feats")),
                        "head": trankit_token.get("head"),
                        "deprel": trankit_token.get("deprel"),
                    },
                }
            )

        merged_sentences.append(
            {
                "id": classla_sentence["id"],
                "text": classla_sentence["text"],
                "tokens": tokens,
            }
        )

    output = dict(row)
    output["annotation"] = {
        "schema": "slosky-auto-annotation-v1",
        "tokenization": "classla",
        "sentence_segmentation": "classla",
        "lemma": "classla",
        "xpos": "classla",
        "upos": "trankit",
        "feats": "trankit",
        "dependencies": "trankit",
        "sentence_count": len(merged_sentences),
        "token_count": sum(len(sentence["tokens"]) for sentence in merged_sentences),
    }
    output["sentences"] = merged_sentences
    return output


def token_misc(token: dict[str, Any]) -> str:
    misc: list[str] = []
    classla_misc = token.get("classla", {}).get("misc")
    if classla_misc and classla_misc != "_":
        misc.append(classla_misc)
    trankit_lemma = token.get("trankit", {}).get("lemma")
    if trankit_lemma and trankit_lemma != token.get("lemma"):
        misc.append(f"TrankitLemma={misc_atom(trankit_lemma)}")
    classla_upos = token.get("classla", {}).get("upos")
    if classla_upos and classla_upos != token.get("upos"):
        misc.append(f"ClasslaUPOS={misc_atom(classla_upos)}")
    classla_feats = token.get("classla", {}).get("feats")
    if classla_feats and classla_feats != "_" and classla_feats != token.get("feats"):
        misc.append(f"ClasslaFEATS={misc_atom(classla_feats)}")
    return "|".join(misc) if misc else "_"


def write_conllu_sentence(handle: Any, row: dict[str, Any], sentence: dict[str, Any]) -> None:
    post_id = row.get("post_id") or row.get("uri")
    sent_id = f"{post_id}:{sentence['id']}"
    handle.write(f"# sent_id = {conllu_comment_value(sent_id)}\n")
    if post_id:
        handle.write(f"# post_id = {conllu_comment_value(post_id)}\n")
    if row.get("author_id"):
        handle.write(f"# author_id = {conllu_comment_value(row['author_id'])}\n")
    if row.get("created_at"):
        handle.write(f"# created_at = {conllu_comment_value(row['created_at'])}\n")
    handle.write("# tokenization = CLASSLA\n")
    handle.write("# ud = Trankit on CLASSLA-pretokenized input\n")
    handle.write(f"# text = {conllu_comment_value(sentence.get('text') or row.get('text') or '')}\n")
    for token in sentence["tokens"]:
        columns = [
            conllu_field(token["id"]),
            conllu_field(token["form"]),
            conllu_field(token["lemma"]),
            conllu_field(token["upos"]),
            conllu_field(token["xpos"]),
            conllu_field(token["feats"]),
            conllu_field(token["head"]),
            conllu_field(token["deprel"]),
            "_",
            token_misc(token),
        ]
        handle.write("\t".join(columns) + "\n")
    handle.write("\n")


def write_meta(args: argparse.Namespace, counts: dict[str, int], modules: dict[str, Any]) -> None:
    meta = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_jsonl": str(args.input),
        "output_jsonl": str(args.output_jsonl) if args.output_jsonl else None,
        "output_conllu": str(args.output_conllu) if args.output_conllu else None,
        "limit": args.limit,
        "counts": counts,
        "pipeline": {
            "sentence_segmentation": "CLASSLA",
            "tokenization": "CLASSLA",
            "lemma": "CLASSLA",
            "xpos": "CLASSLA",
            "upos": "Trankit",
            "feats": "Trankit",
            "dependencies": "Trankit",
            "trankit_input": "CLASSLA-pretokenized sentences",
        },
        "settings": {
            "classla_language": "sl",
            "classla_type": args.classla_type,
            "classla_processors": "tokenize,pos,lemma",
            "trankit_language": args.trankit_language,
            "trankit_embedding": args.trankit_embedding,
            "gpu": args.gpu,
        },
        "versions": {
            "classla": getattr(modules["classla"], "__version__", None),
            "trankit": getattr(modules["trankit"], "__version__", None),
        },
    }
    args.meta_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-conllu", type=Path, default=DEFAULT_OUTPUT_CONLLU)
    parser.add_argument(
        "--meta-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSONL.with_suffix(DEFAULT_OUTPUT_JSONL.suffix + ".meta.json"),
    )
    parser.add_argument(
        "--classla-type",
        choices=["standard", "web", "nonstandard", "spoken"],
        default="web",
        help="CLASSLA Slovene model type used for sentence segmentation and tokenization.",
    )
    parser.add_argument("--trankit-language", default="slovenian")
    parser.add_argument(
        "--trankit-embedding",
        choices=["xlm-roberta-base", "xlm-roberta-large"],
        default="xlm-roberta-large",
        help="Trankit embedding/model family. xlm-roberta-large is slower but stronger.",
    )
    parser.add_argument("--trankit-cache-dir", type=Path)
    parser.add_argument("--limit", type=int, help="Annotate only the first N rows for testing.")
    parser.add_argument("--progress-every", type=int, default=1000)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument(
        "--download-missing-models",
        action="store_true",
        help="Download missing CLASSLA models before running. Trankit may also download on first pipeline init.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_conllu.parent.mkdir(parents=True, exist_ok=True)
    args.meta_json.parent.mkdir(parents=True, exist_ok=True)

    trankit_module, trankit_pipeline = init_trankit_pipeline(args)
    classla_module, classla_pipeline = init_classla_pipeline(args)

    counts = {"posts": 0, "sentences": 0, "tokens": 0}
    with args.output_jsonl.open("w", encoding="utf-8") as jsonl_handle, args.output_conllu.open(
        "w", encoding="utf-8"
    ) as conllu_handle:
        for row in iter_jsonl(args.input):
            if args.limit is not None and counts["posts"] >= args.limit:
                break
            annotated = annotate_row(row, classla_pipeline, trankit_pipeline)
            jsonl_handle.write(json_dump(annotated) + "\n")
            for sentence in annotated["sentences"]:
                write_conllu_sentence(conllu_handle, annotated, sentence)

            counts["posts"] += 1
            counts["sentences"] += annotated["annotation"]["sentence_count"]
            counts["tokens"] += annotated["annotation"]["token_count"]
            if args.progress_every and counts["posts"] % args.progress_every == 0:
                print(
                    f"Annotated {counts['posts']:,} posts, "
                    f"{counts['sentences']:,} sentences, {counts['tokens']:,} tokens",
                    file=sys.stderr,
                )

    write_meta(args, counts, {"classla": classla_module, "trankit": trankit_module})
    print(json.dumps(counts, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

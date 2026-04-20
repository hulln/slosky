from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fasttext
import langid
from langdetect import DetectorFactory, LangDetectException, detect_langs
from lingua import Language, LanguageDetectorBuilder


DetectorFactory.seed = 0


DEFAULT_LINGUA_LANGUAGE_CODES = ("sl", "en", "hr", "sr", "bs", "de", "it")

LINGUA_LANGUAGE_BY_CODE = {
    "sl": Language.SLOVENE,
    "en": Language.ENGLISH,
    "hr": Language.CROATIAN,
    "sr": Language.SERBIAN,
    "bs": Language.BOSNIAN,
    "de": Language.GERMAN,
    "it": Language.ITALIAN,
}

LINGUA_CODE_BY_LANGUAGE = {value: key for key, value in LINGUA_LANGUAGE_BY_CODE.items()}


@dataclass(frozen=True)
class FastTextResult:
    label: str
    prob: float


@dataclass(frozen=True)
class LinguaResult:
    top_language: str
    sl_confidence: float


def build_fasttext_model(model_path: Path | str):
    return fasttext.load_model(str(model_path))


def build_lingua_detector(language_codes: tuple[str, ...] = DEFAULT_LINGUA_LANGUAGE_CODES):
    languages = [LINGUA_LANGUAGE_BY_CODE[code] for code in language_codes]
    return LanguageDetectorBuilder.from_languages(*languages).with_preloaded_language_models().build()


def fasttext_predict_sl(model, text: str) -> FastTextResult:
    labels, probs = model.predict(text, k=1)
    if not labels:
        return FastTextResult(label="", prob=0.0)
    label = labels[0].replace("__label__", "")
    prob = round(float(probs[0]), 6)
    return FastTextResult(label=label, prob=prob)


def fasttext_predict_sl_batch(model, texts: list[str]) -> list[FastTextResult]:
    if not texts:
        return []
    labels_batch, probs_batch = model.predict(texts, k=1)
    results: list[FastTextResult] = []
    for labels, probs in zip(labels_batch, probs_batch):
        if not labels:
            results.append(FastTextResult(label="", prob=0.0))
            continue
        label = labels[0].replace("__label__", "")
        prob = round(float(probs[0]), 6)
        results.append(FastTextResult(label=label, prob=prob))
    return results


def lingua_predict_sl(detector, text: str) -> LinguaResult:
    detected = detector.detect_language_of(text)
    if detected is None:
        return LinguaResult(top_language="", sl_confidence=0.0)

    top_language = LINGUA_CODE_BY_LANGUAGE.get(detected, "")
    sl_confidence = round(float(detector.compute_language_confidence(text, Language.SLOVENE)), 6)
    return LinguaResult(top_language=top_language, sl_confidence=sl_confidence)


def lingua_predict_sl_batch(detector, texts: list[str]) -> list[LinguaResult]:
    if not texts:
        return []
    detected_batch = list(detector.detect_languages_in_parallel_of(texts))
    sl_conf_batch = list(detector.compute_language_confidence_in_parallel(texts, Language.SLOVENE))
    results: list[LinguaResult] = []
    for detected, sl_conf in zip(detected_batch, sl_conf_batch):
        top_language = LINGUA_CODE_BY_LANGUAGE.get(detected, "") if detected is not None else ""
        results.append(
            LinguaResult(
                top_language=top_language,
                sl_confidence=round(float(sl_conf), 6),
            )
        )
    return results


def langid_predict_sl(text: str) -> tuple[str, float]:
    label, score = langid.classify(text)
    return label, round(float(score), 6)


def langdetect_sl_probability(text: str) -> float:
    try:
        for candidate in detect_langs(text):
            if candidate.lang == "sl":
                return round(float(candidate.prob), 6)
        return 0.0
    except LangDetectException:
        return 0.0

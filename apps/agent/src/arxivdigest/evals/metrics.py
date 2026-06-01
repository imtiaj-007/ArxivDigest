"""Eval metrics — pure functions, no I/O."""

from __future__ import annotations

from collections.abc import Sequence


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _f1(precision: float, recall: float) -> float:
    return _safe_div(2 * precision * recall, precision + recall)


def _theme_tp_fp_fn(
    theme: str, predicted: Sequence[set[str]], expected: Sequence[set[str]]
) -> tuple[int, int, int]:
    tp = fp = fn = 0
    for p, e in zip(predicted, expected, strict=True):
        in_p, in_e = theme in p, theme in e
        if in_p and in_e:
            tp += 1
        elif in_p:
            fp += 1
        elif in_e:
            fn += 1
    return tp, fp, fn


def multilabel_classification_metrics(
    predicted: Sequence[set[str]], expected: Sequence[set[str]]
) -> dict[str, float]:
    """Multi-label classification metrics over (predicted, expected) per-paper theme sets.

    Returns micro + macro precision / recall / F1. Micro pools all (paper, theme)
    decisions; macro averages per-theme F1 across the union of observed themes.
    """
    if len(predicted) != len(expected):
        raise ValueError("predicted and expected must be the same length")
    if not predicted:
        return {
            "micro_precision": 0.0, "micro_recall": 0.0, "micro_f1": 0.0,
            "macro_precision": 0.0, "macro_recall": 0.0, "macro_f1": 0.0,
        }

    tp = sum(len(p & e) for p, e in zip(predicted, expected, strict=True))
    fp = sum(len(p - e) for p, e in zip(predicted, expected, strict=True))
    fn = sum(len(e - p) for p, e in zip(predicted, expected, strict=True))

    micro_p = _safe_div(tp, tp + fp)
    micro_r = _safe_div(tp, tp + fn)
    micro_f1 = _f1(micro_p, micro_r)

    themes: set[str] = set().union(*predicted, *expected)
    per_theme_f1: list[float] = []
    per_theme_p: list[float] = []
    per_theme_r: list[float] = []
    for theme in themes:
        tp_t, fp_t, fn_t = _theme_tp_fp_fn(theme, predicted, expected)
        p_t = _safe_div(tp_t, tp_t + fp_t)
        r_t = _safe_div(tp_t, tp_t + fn_t)
        per_theme_p.append(p_t)
        per_theme_r.append(r_t)
        per_theme_f1.append(_f1(p_t, r_t))

    macro_p = _safe_div(sum(per_theme_p), len(per_theme_p))
    macro_r = _safe_div(sum(per_theme_r), len(per_theme_r))
    macro_f1 = _safe_div(sum(per_theme_f1), len(per_theme_f1))

    return {
        "micro_precision": micro_p, "micro_recall": micro_r, "micro_f1": micro_f1,
        "macro_precision": macro_p, "macro_recall": macro_r, "macro_f1": macro_f1,
    }


def per_theme_f1(
    predicted: Sequence[set[str]], expected: Sequence[set[str]]
) -> dict[str, float]:
    """F1 score per theme — useful for identifying which themes the agent struggles with."""
    out: dict[str, float] = {}
    themes: set[str] = set().union(*predicted, *expected)
    for theme in themes:
        tp, fp, fn = _theme_tp_fp_fn(theme, predicted, expected)
        p = _safe_div(tp, tp + fp)
        r = _safe_div(tp, tp + fn)
        out[theme] = _f1(p, r)
    return out

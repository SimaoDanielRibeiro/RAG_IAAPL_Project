"""Deterministic metrics for the RAG eval harness.

Each metric returns a float in [0, 1] or `None` when the metric does not
apply to the case (e.g. citation_present on a standard-mode case). `None`
values are excluded from the aggregate mean.
"""

from __future__ import annotations

import re
from typing import Any, Callable


def metric_source_recall(case: dict, result: dict) -> float | None:
    """Fraction of expected sources that appeared in the retrieved sources."""
    expected = case.get("expected_sources") or []
    if not expected:
        return None
    got = set(result["retrieval"]["sources"])
    hits = sum(1 for s in expected if s in got)
    return round(hits / len(expected), 3)


def metric_page_recall(case: dict, result: dict) -> float | None:
    """Fraction of expected pages that appeared in the retrieved pages."""
    expected = case.get("expected_pages") or []
    if not expected:
        return None
    got = set(result["retrieval"]["pages"])
    hits = sum(1 for p in expected if p in got)
    return round(hits / len(expected), 3)


def metric_must_contain(case: dict, result: dict) -> float | None:
    """Fraction of required substrings present in the answer (case-insensitive)."""
    needles = case.get("must_contain") or []
    if not needles or "answer" not in result:
        return None
    answer = result["answer"].lower()
    hits = sum(1 for needle in needles if needle.lower() in answer)
    return round(hits / len(needles), 3)


def metric_must_not_contain(case: dict, result: dict) -> float | None:
    """1.0 if no forbidden substring appears in the answer, else 0.0."""
    forbidden = case.get("must_not_contain") or []
    if "answer" not in result:
        return None
    if not forbidden:
        return 1.0
    answer = result["answer"].lower()
    return 0.0 if any(b.lower() in answer for b in forbidden) else 1.0


def metric_fallback_correct(case: dict, result: dict) -> float | None:
    """1.0 if the fallback flag matches the case's `expects_fallback`."""
    expects = bool(case.get("expects_fallback", False))
    actual = bool(result["retrieval"].get("fallback", False))
    return 1.0 if expects == actual else 0.0


_CITATION_PATTERN = re.compile(r"\[[^\]\[]+(?:,\s*p\.\d+)?\]")


def metric_citation_present(case: dict, result: dict) -> float | None:
    """For exhaustive cases only: 1.0 if at least one [file, p.N] marker appears."""
    if case.get("answer_mode") != "exhaustive" or "answer" not in result:
        return None
    if case.get("expects_fallback"):
        return None
    return 1.0 if _CITATION_PATTERN.search(result["answer"]) else 0.0


METRICS: dict[str, Callable[[dict, dict], float | None]] = {
    "source_recall": metric_source_recall,
    "page_recall": metric_page_recall,
    "must_contain": metric_must_contain,
    "must_not_contain": metric_must_not_contain,
    "fallback_correct": metric_fallback_correct,
    "citation_present": metric_citation_present,
}


def compute_metrics(case: dict, result: dict) -> dict[str, float | None]:
    """Run every metric for one case + result."""
    return {name: fn(case, result) for name, fn in METRICS.items()}


def aggregate_summary(results: list[dict]) -> dict[str, Any]:
    """Compute mean + sample count for every metric across all results."""
    summary: dict[str, Any] = {"total_cases": len(results)}
    summary["errors"] = sum(1 for r in results if r.get("error"))
    for metric_name in METRICS:
        values = [
            r["metrics"][metric_name]
            for r in results
            if r.get("metrics") and r["metrics"].get(metric_name) is not None
        ]
        if values:
            summary[f"{metric_name}_mean"] = round(sum(values) / len(values), 3)
            summary[f"{metric_name}_n"] = len(values)
    return summary

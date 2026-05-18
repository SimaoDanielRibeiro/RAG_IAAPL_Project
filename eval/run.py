"""Eval harness runner: load golden set, exercise the RAG pipeline, score, save."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so `backend.*` / `src.*` resolve when
# this file is run as `python -m eval.run`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.rag_service import rag_service  # noqa: E402
from src.rag.config import FALLBACK_ANSWER  # noqa: E402

from eval.metrics import aggregate_summary, compute_metrics  # noqa: E402


def load_golden(path: Path) -> list[dict]:
    """Read a JSONL golden file. Lines starting with `#` and blank lines are skipped."""
    cases: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON ({error})") from error
    return cases


def apply_filter(cases: list[dict], filter_expr: str | None) -> list[dict]:
    """Filter cases by simple `key=value` comma-separated expression.

    Examples:
      answer_mode=exhaustive
      tags=hard
      answer_mode=standard,tags=lookup
    """
    if not filter_expr:
        return cases
    constraints: list[tuple[str, str]] = []
    for term in filter_expr.split(","):
        term = term.strip()
        if not term:
            continue
        if "=" not in term:
            raise ValueError(f"Bad filter term '{term}'. Expected key=value.")
        key, _, value = term.partition("=")
        constraints.append((key.strip(), value.strip()))

    def keep(case: dict) -> bool:
        for key, value in constraints:
            if key == "tags":
                if value not in (case.get("tags") or []):
                    return False
            else:
                if str(case.get(key)) != value:
                    return False
        return True

    return [case for case in cases if keep(case)]


def load_fixture_files(document_paths: list[str]) -> list[tuple[str, bytes]]:
    """Read fixture files from disk and return (filename, bytes) tuples for the service."""
    loaded: list[tuple[str, bytes]] = []
    for relative in document_paths:
        path = (PROJECT_ROOT / relative).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Fixture not found: {path}")
        loaded.append((path.name, path.read_bytes()))
    return loaded


def run_case(case: dict, retrieval_only: bool) -> dict[str, Any]:
    """Reset the service, load this case's documents, and run retrieval (+ answer)."""
    rag_service.remove_all_documents()
    fixtures = load_fixture_files(case["documents"])
    rag_service.add_documents(fixtures)

    answer_mode = case.get("answer_mode", "standard")

    prep = rag_service.prepare_answer(
        question=case["question"],
        answer_mode=answer_mode,
    )

    retrieval = {
        "sources": prep.get("sources", []),
        "pages": prep.get("pages", []),
        "confidence": prep.get("confidence"),
        "chunks_used": prep.get("chunks_used", 0),
        "fallback": bool(prep.get("fallback", False)),
    }
    output: dict[str, Any] = {
        "id": case["id"],
        "question": case["question"],
        "answer_mode": answer_mode,
        "retrieval": retrieval,
    }

    if retrieval_only:
        return output

    if prep.get("fallback"):
        output["answer"] = FALLBACK_ANSWER
        return output

    full = rag_service.answer_question(
        question=case["question"],
        answer_mode=answer_mode,
    )
    output["answer"] = full.get("answer", "")
    return output


def get_git_sha() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return sha or "unknown"
    except Exception:
        return "unknown"


def _format_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def print_summary(summary: dict, results: list[dict]) -> None:
    print()
    print("=" * 60)
    print(f"Cases run: {summary['total_cases']}  |  errors: {summary['errors']}")
    print("-" * 60)
    metric_labels = [
        ("source_recall", "Source recall"),
        ("page_recall", "Page recall"),
        ("must_contain", "Must-contain pass rate"),
        ("must_not_contain", "Must-not-contain pass rate"),
        ("fallback_correct", "Fallback correctness"),
        ("citation_present", "Citation present (exhaustive)"),
    ]
    for key, label in metric_labels:
        mean = summary.get(f"{key}_mean")
        count = summary.get(f"{key}_n")
        if mean is None:
            print(f"{label:<32} —")
        else:
            print(f"{label:<32} {mean:.3f}   (n={count})")
    print("-" * 60)
    failures = [
        r for r in results
        if r.get("error") or any(
            v == 0.0 for v in (r.get("metrics") or {}).values() if v is not None
        )
    ]
    if failures:
        print(f"Failures ({len(failures)}):")
        for r in failures:
            if r.get("error"):
                print(f"  [X] {r['id']}  ERROR: {r['error']}")
                continue
            failed_metrics = [
                name for name, value in (r.get("metrics") or {}).items()
                if value == 0.0
            ]
            print(f"  [X] {r['id']}  failed: {', '.join(failed_metrics)}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RAG eval harness.")
    parser.add_argument(
        "--golden",
        default="eval/golden/set_v1.jsonl",
        help="Path to a golden JSONL file (default: eval/golden/set_v1.jsonl).",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip answer generation (faster; still scores retrieval metrics).",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help='Filter expression, e.g. "answer_mode=exhaustive,tags=hard".',
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output path. Default: eval/results/<timestamp>_<sha>.json",
    )
    args = parser.parse_args()

    golden_path = (PROJECT_ROOT / args.golden).resolve()
    if not golden_path.is_file():
        raise SystemExit(f"Golden file not found: {golden_path}")

    cases = apply_filter(load_golden(golden_path), args.filter)
    if not cases:
        raise SystemExit("No cases to run after filtering.")

    print(f"Loaded {len(cases)} case(s) from {golden_path}")
    if args.retrieval_only:
        print("Mode: retrieval-only (no generation)")
    print()

    results: list[dict] = []
    start_time = time.time()
    for index, case in enumerate(cases, start=1):
        case_start = time.time()
        print(f"[{index}/{len(cases)}] {case['id']}...", end=" ", flush=True)
        try:
            result = run_case(case, retrieval_only=args.retrieval_only)
            result["metrics"] = compute_metrics(case, result)
            print(f"ok ({time.time() - case_start:.1f}s)")
        except Exception as error:
            traceback.print_exc()
            result = {
                "id": case["id"],
                "error": f"{type(error).__name__}: {error}",
                "metrics": {},
            }
            print(f"ERROR ({time.time() - case_start:.1f}s)")
        result["elapsed_seconds"] = round(time.time() - case_start, 2)
        results.append(result)

    summary = aggregate_summary(results)
    summary["wall_clock_seconds"] = round(time.time() - start_time, 2)

    run_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": get_git_sha(),
        "config": {
            "chat_model": rag_service.chat_model,
            "embedding_model": rag_service.embedding_model,
            "retrieval_only": args.retrieval_only,
            "filter": args.filter,
            "golden": str(golden_path.relative_to(PROJECT_ROOT)),
        },
        "summary": summary,
        "per_question": results,
    }

    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
    else:
        stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
        out_path = PROJECT_ROOT / "eval" / "results" / f"{stamp}_{run_payload['git_sha']}.json"
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")

    print_summary(summary, results)
    try:
        display_path = out_path.relative_to(PROJECT_ROOT)
    except ValueError:
        display_path = out_path
    print(f"\nResults written to {display_path}")


if __name__ == "__main__":
    main()

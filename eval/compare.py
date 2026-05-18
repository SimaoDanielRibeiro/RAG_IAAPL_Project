"""Compare two eval runs and print per-metric deltas plus per-case regressions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.metrics import METRICS


def _load_run(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _by_id(results: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in results if "id" in r}


def _binary_pass(case_result: dict) -> bool:
    """A case is considered passing if every applicable metric is 1.0."""
    metrics = case_result.get("metrics") or {}
    values = [v for v in metrics.values() if v is not None]
    if not values:
        return False
    return all(v == 1.0 for v in values)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two eval runs.")
    parser.add_argument("baseline", help="Baseline result JSON.")
    parser.add_argument("candidate", help="Candidate result JSON.")
    args = parser.parse_args()

    baseline = _load_run(Path(args.baseline))
    candidate = _load_run(Path(args.candidate))

    print(f"Baseline:  {baseline['git_sha']}  {baseline['timestamp']}")
    print(f"Candidate: {candidate['git_sha']}  {candidate['timestamp']}")
    print()

    print(f"{'Metric':<28}{'Baseline':>12}{'Candidate':>12}{'Delta':>10}")
    print("-" * 62)
    for metric in METRICS:
        key = f"{metric}_mean"
        base_value = baseline["summary"].get(key)
        cand_value = candidate["summary"].get(key)
        if base_value is None or cand_value is None:
            continue
        delta = cand_value - base_value
        marker = "  ^" if delta > 0.005 else ("  v" if delta < -0.005 else "")
        print(f"{metric:<28}{base_value:>12.3f}{cand_value:>12.3f}{delta:>+10.3f}{marker}")

    base_by_id = _by_id(baseline["per_question"])
    cand_by_id = _by_id(candidate["per_question"])
    shared = sorted(set(base_by_id) & set(cand_by_id))

    regressions: list[str] = []
    improvements: list[str] = []
    for case_id in shared:
        base_pass = _binary_pass(base_by_id[case_id])
        cand_pass = _binary_pass(cand_by_id[case_id])
        if base_pass and not cand_pass:
            regressions.append(case_id)
        elif not base_pass and cand_pass:
            improvements.append(case_id)

    if regressions:
        print("\nRegressions:")
        for case_id in regressions:
            print(f"  [X] {case_id}")
    if improvements:
        print("\nNew passes:")
        for case_id in improvements:
            print(f"  [+] {case_id}")
    if not regressions and not improvements:
        print("\nNo per-case pass/fail changes.")


if __name__ == "__main__":
    main()

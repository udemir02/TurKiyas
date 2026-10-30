import argparse
import collections
import copy
import datetime
import hashlib
import json
import statistics
import time
from pathlib import Path

import tour_compare as app


def checks_for(case, intent, state, result):
    expected = case["expect"]
    checks = {}
    if "in_scope" in expected:
        checks["in_scope"] = intent["in_scope"] == expected["in_scope"]
    else:
        checks["in_scope"] = intent["in_scope"] is True
    if "constraints" in expected:
        actual = {k: app.normalise(v) if isinstance(v, str) else v for k, v in state["constraints"].items()}
        gold = {k: app.normalise(v) if isinstance(v, str) else v for k, v in expected["constraints"].items()}
        checks["constraints_exact"] = actual == gold
    if "tour_ids" in expected:
        checks["tour_ids"] = set(state["tour_ids"]) == set(expected["tour_ids"])
    if "criteria_contains" in expected:
        checks["criteria"] = set(expected["criteria_contains"]).issubset(state["criteria"])
    checks["unsupported"] = bool(intent["unsupported"]) == bool(expected.get("unsupported", False))
    if "statuses" in expected:
        actual = {r["tour"]["id"]: r["status"] for r in result["rows"]}
        checks["statuses"] = all(actual.get(k) == v for k, v in expected["statuses"].items())
    if "result_ids" in expected:
        checks["result_ids"] = [r["tour"]["id"] for r in result["rows"]] == expected["result_ids"]
    return checks


def main():
    parser = argparse.ArgumentParser(description='Evaluate language interpretation against fixed authored cases; save all raw outputs.')
    parser.add_argument("--backend", choices=("ollama", "rules"), default="ollama")
    parser.add_argument("--split", choices=("development", "evaluation", "all"), default="evaluation")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = app.ROOT / "evaluation/cases.json"
    cases = json.loads(source.read_text(encoding="utf-8"))
    cases = [c for c in cases if args.split == "all" or c["split"] == args.split]
    tours, records = app.load_catalogue(), []
    for case in cases:
        state = copy.deepcopy(case.get("state", app.new_state()))
        started = time.perf_counter()
        record = {"id": case["id"], "category": case["category"], "question": case["question"], "input_state": copy.deepcopy(state), "expected": case["expect"]}
        try:
            fn = app.ollama_intent if args.backend == "ollama" else app.rule_intent
            intent, metrics = fn(case["question"], state, tours, **({"model": args.model} if args.backend == "ollama" else {}))
            state = app.update_state(state, intent)
            result = app.compare(tours, state)
            checks = {"expected_error": False} if case["expect"].get("error") else checks_for(case, intent, state, result)
            record.update(intent=intent, output_state=state, metrics=metrics, checks=checks, answer=app.render(result, intent))
            record["passed"] = all(checks.values())
        except app.AppError as exc:
            record.update(error=str(exc), passed=case["expect"].get("error", False), checks={"expected_error": bool(case["expect"].get("error"))})
        record["wall_seconds"] = round(time.perf_counter() - started, 3)
        records.append(record)
        print(f"{case['id']} {'PASS' if record['passed'] else 'FAIL'} {record['wall_seconds']:.2f}s", flush=True)
    categories = collections.defaultdict(lambda: {"passed": 0, "total": 0})
    for row in records:
        categories[row["category"]]["total"] += 1
        categories[row["category"]]["passed"] += int(row["passed"])
    model_times = [r["wall_seconds"] for r in records if "metrics" in r and args.backend == "ollama"]
    summary = {"total": len(records), "passed": sum(r["passed"] for r in records), "categories": dict(categories),
               "model_calls": len(model_times), "mean_model_seconds": round(statistics.mean(model_times), 3) if model_times else None,
               "median_model_seconds": round(statistics.median(model_times), 3) if model_times else None,
               "max_model_seconds": max(model_times) if model_times else None}
    run = {"backend": args.backend, "model": args.model if args.backend == "ollama" else None, "split": args.split,
           "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "cases_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "application_sha256": hashlib.sha256((app.ROOT / 'tour_compare.py').read_bytes()).hexdigest(),
           "method": "Fixed authored gold cases; exact constraint state, ID selection, required criteria, scope, unsupported detection and selected eligibility checks. Not a user study or real-market benchmark.",
           "summary": summary, "records": records}
    output = args.output or app.ROOT / f"evaluation/{args.backend}_{args.split}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Saved", output)


if __name__ == "__main__":
    main()

# ABOUTME: Evaluation harness for running Proceda against SOP-Bench benchmarks.
# ABOUTME: Loads tasks from CSV, runs each through Proceda, scores against ground truth.

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from benchmarks.sop_bench.output_extractor import extract_output
from proceda.agent import Agent
from proceda.config import ProcedaConfig
from proceda.events import CollectorEventSink

BENCHMARKS_DIR = Path(__file__).parent / "domains"
RESULTS_DIR = Path(__file__).parent / "results"


def load_benchmark_data(domain: str, data_dir: str) -> tuple[list[dict], list[str], list[str]]:
    """Load task data, input columns, and output columns for a domain.

    Returns (tasks, input_columns, output_columns) where tasks is a list of
    dicts with all CSV columns.
    """
    domain_path = Path(data_dir) / domain

    # Load metadata for column definitions
    metadata_path = domain_path / "metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    input_columns = metadata["input_columns"]
    output_columns = metadata["output_columns"]

    # Load CSV data
    csv_path = domain_path / "test_set_with_outputs.csv"
    tasks = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(dict(row))

    return tasks, input_columns, output_columns


def compare_decisions(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare predicted vs expected output, case-insensitive with normalization."""
    if not predicted or not expected:
        return False

    for key, expected_val in expected.items():
        pred_val = predicted.get(key)
        if pred_val is None:
            return False
        # Normalize: lowercase, strip whitespace, normalize separators
        pred_norm = str(pred_val).lower().strip().replace("-", "_").replace(" ", "_")
        exp_norm = str(expected_val).lower().strip().replace("-", "_").replace(" ", "_")
        if pred_norm != exp_norm:
            return False

    return True


def save_trace(
    domain: str,
    task_id: str,
    status: str,
    collector: CollectorEventSink,
    predicted: dict,
    expected: dict,
    run_event_log_path: Path | None,
) -> None:
    """Save full trace for a task to the results/traces directory."""
    traces_dir = RESULTS_DIR / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    trace_path = traces_dir / f"{domain}_{task_id}_{status}.jsonl"
    with open(trace_path, "w") as f:
        # Write metadata header
        f.write(
            json.dumps(
                {
                    "_meta": True,
                    "domain": domain,
                    "task_id": task_id,
                    "status": status,
                    "predicted": predicted,
                    "expected": expected,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            + "\n"
        )
        # Write all events
        for event in collector.events:
            f.write(event.to_json() + "\n")

    # Copy Proceda's native event log if available
    if run_event_log_path:
        log_path = Path(run_event_log_path)
        if log_path.is_dir():
            # event_log_path is the run directory; look for events.jsonl inside it
            events_file = log_path / "events.jsonl"
            if events_file.exists():
                dest = traces_dir / f"{domain}_{task_id}_{status}_proceda.jsonl"
                shutil.copy2(events_file, dest)
        elif log_path.is_file():
            dest = traces_dir / f"{domain}_{task_id}_{status}_proceda.jsonl"
            shutil.copy2(log_path, dest)


def run_evaluation(
    domain: str,
    data_dir: str,
    max_tasks: int | None = None,
) -> dict[str, Any]:
    """Run Proceda against all tasks in a domain and return metrics."""
    tasks, input_columns, output_columns = load_benchmark_data(domain, data_dir)

    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    skill_dir = BENCHMARKS_DIR / domain
    if not (skill_dir / "SKILL.md").exists():
        print(f"Error: {skill_dir / 'SKILL.md'} not found. Run `proceda convert` first.")
        sys.exit(1)

    # Load domain-specific config
    config_path = skill_dir / "config.yaml"
    if config_path.exists():
        config = ProcedaConfig.load(str(config_path))
    else:
        config = ProcedaConfig.load()

    results = []
    total = len(tasks)

    for i, task in enumerate(tasks):
        task_id = task.get("patient_id", task.get("account_id", f"task_{i}"))
        print(f"[{i + 1}/{total}] Running task {task_id}...", end=" ", flush=True)

        # Build variables from input columns
        variables = {}
        for col in input_columns:
            val = task.get(col, "")
            variables[col] = str(val) if val is not None else ""

        # Build expected output
        expected = {}
        for col in output_columns:
            expected[col] = task.get(col, "")

        # Run Proceda
        collector = CollectorEventSink()
        start_time = time.time()
        try:
            agent = Agent.from_path(str(skill_dir), config=config)
            result = agent.run(variables=variables, event_sinks=[collector])
            execution_time = time.time() - start_time
            success = True
            error = None
            run_event_log_path = getattr(result, "event_log_path", None)
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error = str(e)
            run_event_log_path = None

        # Extract output
        if success:
            predicted = extract_output(collector.events, output_columns)
        else:
            predicted = {}

        # Compare
        is_correct = compare_decisions(predicted, expected) if success else False
        status = "success" if is_correct else "fail"
        if not success:
            status = "error"

        print(f"{'PASS' if is_correct else 'FAIL'} ({execution_time:.1f}s)")
        if not is_correct and predicted:
            for col in output_columns:
                p = predicted.get(col, "<missing>")
                e = expected.get(col, "")
                if str(p).lower().strip() != str(e).lower().strip():
                    print(f"  {col}: predicted={p}, expected={e}")

        # Save trace
        save_trace(domain, task_id, status, collector, predicted, expected, run_event_log_path)

        results.append(
            {
                "task_id": task_id,
                "success": success,
                "is_correct": is_correct,
                "predicted": predicted,
                "expected": expected,
                "execution_time": execution_time,
                "error": error,
            }
        )

    # Calculate metrics
    num_tasks = len(results)
    num_completed = sum(1 for r in results if r["success"])
    num_correct = sum(1 for r in results if r["is_correct"])

    tsr = num_correct / num_tasks if num_tasks > 0 else 0.0
    ecr = num_completed / num_tasks if num_tasks > 0 else 0.0
    c_tsr = num_correct / num_completed if num_completed > 0 else 0.0

    metrics = {
        "domain": domain,
        "num_tasks": num_tasks,
        "num_completed": num_completed,
        "num_correct": num_correct,
        "tsr": tsr,
        "ecr": ecr,
        "c_tsr": c_tsr,
        "timestamp": datetime.now().isoformat(),
    }

    # Print summary
    print(f"\n{'=' * 50}")
    print(f"Results for {domain}")
    print(f"{'=' * 50}")
    print(f"Tasks:     {num_tasks}")
    print(f"Completed: {num_completed} (ECR: {ecr:.1%})")
    print(f"Correct:   {num_correct} (TSR: {tsr:.1%})")
    print(f"C-TSR:     {c_tsr:.1%}")
    print(f"{'=' * 50}")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_path = RESULTS_DIR / f"{domain}_results.json"
    with open(results_path, "w") as f:
        json.dump({"metrics": metrics, "tasks": results}, f, indent=2)
    print(f"Results saved to {results_path}")

    # Save per-task CSV
    csv_path = RESULTS_DIR / f"{domain}_detailed.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["task_id", "success", "is_correct", "execution_time", "error"],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "task_id": r["task_id"],
                    "success": r["success"],
                    "is_correct": r["is_correct"],
                    "execution_time": f"{r['execution_time']:.2f}",
                    "error": r["error"] or "",
                }
            )
    print(f"Detailed CSV saved to {csv_path}")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="SOP-Bench evaluation harness for Proceda")
    parser.add_argument("--domain", required=True, help="Benchmark domain name")
    parser.add_argument(
        "--data-dir",
        default=str(Path.home() / "repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data"),
        help="Path to SOP-Bench benchmarks/data/",
    )
    parser.add_argument("--max-tasks", type=int, default=None, help="Limit number of tasks")
    args = parser.parse_args()

    run_evaluation(args.domain, args.data_dir, args.max_tasks)


if __name__ == "__main__":
    main()

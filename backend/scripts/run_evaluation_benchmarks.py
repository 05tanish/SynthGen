"""Run reproducible, explicitly attributed SynthGen model benchmarks."""

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import pandas as pd

from app.tools.ml_utility_evaluator import evaluate_ml_utility
from app.tools.privacy_checker import evaluate_privacy_risk
from app.tools.schema_evaluator import evaluate_schema_fidelity
from app.tools.statistical_evaluator import evaluate_statistical_quality
from app.tools.synthetic_generator import CTGANGenerator, GaussianCopulaGenerator, TVAEGenerator


SEED = 42
FIXTURE_VERSION = "1.0.0"
GENERATORS = {
    "GaussianCopula": GaussianCopulaGenerator,
    "CTGAN": CTGANGenerator,
    "TVAE": TVAEGenerator,
}


def make_fixtures(seed=SEED):
    rng = np.random.default_rng(seed)
    size = 240
    category = np.asarray([f"category_{i % 4}" for i in range(size)])
    numerical = rng.normal(loc=10, scale=3, size=size)
    binary = (numerical + rng.normal(size=size) > 10).astype(int)
    mixed = pd.DataFrame({"amount": numerical, "segment": category, "label": binary})

    missing = mixed.copy()
    missing.loc[::13, "amount"] = np.nan
    missing.loc[::17, "segment"] = None

    imbalanced_target = np.zeros(size, dtype=int)
    imbalanced_target[:12] = 1
    rng.shuffle(imbalanced_target)
    imbalanced = pd.DataFrame({"feature": rng.normal(size=size), "label": imbalanced_target})

    regression = pd.DataFrame({
        "x": rng.normal(size=size),
        "group": category,
    })
    regression["target"] = 4.5 * regression["x"] + rng.normal(scale=0.2, size=size)

    high_cardinality = pd.DataFrame({
        "record_type": [f"type_{i % 120}" for i in range(size)],
        "value": rng.normal(size=size),
        "label": (np.arange(size) % 2),
    })

    duplicate = mixed.iloc[:80].copy().reset_index(drop=True)
    duplicate = pd.concat([duplicate, duplicate.iloc[:20]], ignore_index=True)
    small = mixed.iloc[:16].copy().reset_index(drop=True)
    large = pd.DataFrame({
        "measure": rng.normal(size=5000),
        "cohort": [f"cohort_{i % 8}" for i in range(5000)],
        "target": np.arange(5000) % 3,
    })
    categorical_only = pd.DataFrame({
        "region": [f"r{i % 5}" for i in range(size)],
        "product": [f"p{i % 7}" for i in range(size)],
        "label": np.arange(size) % 2,
    })

    return {
        "numerical_only": (pd.DataFrame({"x": numerical, "y": numerical * 0.4 + rng.normal(size=size)}), None, None),
        "categorical_only": (categorical_only, "label", "classification"),
        "mixed": (mixed, "label", "classification"),
        "missing_values": (missing, "label", "classification"),
        "imbalanced_classification": (imbalanced, "label", "classification"),
        "regression": (regression, "target", "regression"),
        "high_cardinality": (high_cardinality, "label", "classification"),
        "duplicate_records": (duplicate, "label", "classification"),
        "small_dataset": (small, "label", "classification"),
        "large_dataset": (large, "target", "classification"),
    }


def dependency_versions():
    result = {}
    for package in ("sdv", "pandas", "numpy", "scipy", "scikit-learn", "torch"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result


def generator_parameters(model, epochs):
    if model == "CTGAN":
        return {"epochs": epochs, "batch_size": 128, "pac": 10, "verbose": False}
    if model == "TVAE":
        return {"epochs": epochs, "batch_size": 128, "verbose": False}
    return {}


def benchmark_run(dataset_name, frame, target, task, model_name, seed, epochs, output_rows):
    requested_parameters = generator_parameters(model_name, epochs)
    result = {
        "dataset": {
            "name": dataset_name,
            "version": FIXTURE_VERSION,
            "rows": int(len(frame)),
            "columns": int(len(frame.columns)),
            "column_names": [str(column) for column in frame.columns],
            "random_seed": int(seed),
        },
        "generator": {
            "requested_model": model_name,
            "actual_model": None,
            "fallback_reason": None,
            "requested_parameters": requested_parameters,
            "effective_parameters": None,
            "status": "PENDING",
        },
        "evaluation_configuration": {
            "target_column": target,
            "task_type": task,
            "random_seed": int(seed),
            "privacy_sample_size": 1000,
        },
        "metrics": {},
        "errors": [],
    }

    generation_started = time.perf_counter()
    try:
        generator = GENERATORS[model_name](parameters=requested_parameters)
        fit_start = time.perf_counter()
        generator.fit(frame)
        fit_runtime = time.perf_counter() - fit_start
        sample_start = time.perf_counter()
        synthetic = generator.generate(num_rows=output_rows, random_seed=seed)
        sample_runtime = time.perf_counter() - sample_start
        result["generator"].update({
            "actual_model": model_name,
            "effective_parameters": generator.effective_parameters,
            "sampling_seed_applied": bool(getattr(generator, "random_seed_applied", False)),
            "status": "COMPLETED",
            "fit_runtime_seconds": fit_runtime,
            "sampling_runtime_seconds": sample_runtime,
            "generated_rows": int(len(synthetic)),
            "generated_columns": int(len(synthetic.columns)),
        })
    except Exception as exc:
        safe_error = f"{type(exc).__name__}: {exc}".replace(sys.prefix, "<python-env>")
        result["generator"].update({
            "status": "FAILED",
            "runtime_seconds": time.perf_counter() - generation_started,
            "error": safe_error,
        })
        result["errors"].append({"component": "generation", "message": result["generator"]["error"]})
        return result

    metric_functions = {
        "schema_fidelity": lambda: evaluate_schema_fidelity(frame, synthetic),
        "statistical_fidelity": lambda: evaluate_statistical_quality(frame, synthetic),
        "privacy_risk": lambda: evaluate_privacy_risk(frame, synthetic, sample_size=1000, random_seed=seed),
        "ml_utility": lambda: evaluate_ml_utility(
            frame, synthetic, target_column=target, task_type=task, random_seed=seed
        ) if target and task else {
            "status": "INCOMPLETE",
            "metrics": {},
            "errors": [{"component": "ml_utility", "message": "Fixture has no configured target/task."}],
        },
    }
    for component, evaluate in metric_functions.items():
        try:
            result["metrics"][component] = evaluate()
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            result["metrics"][component] = {
                "status": "FAILED",
                "errors": [{"component": component, "message": message}],
            }
            result["errors"].append({"component": component, "message": message})
    return result


def markdown_report(document):
    lines = [
        "# SynthGen benchmark run",
        "",
        f"- Run timestamp (UTC): `{document['timestamp_utc']}`",
        f"- Fixture version: `{document['fixture_version']}`",
        f"- Dependency versions: `{json.dumps(document['dependency_versions'], sort_keys=True)}`",
        "- No overall quality score is calculated; dimensions remain separate.",
        "",
        "| Dataset | Requested model | Actual model | Generation status | Runtime seconds | Error |",
        "|---|---|---|---|---:|---|",
    ]
    for run in document["runs"]:
        generator = run["generator"]
        error = str(generator.get("error", "")).replace("|", "&#124;").replace("\n", " ")[:180]
        lines.append(
            f"| {run['dataset']['name']} | {generator['requested_model']} | "
            f"{generator.get('actual_model') or 'Unavailable'} | {generator['status']} | "
            f"{generator.get('runtime_seconds', generator.get('fit_runtime_seconds', '—'))} | {error} |"
        )
    lines += [
        "",
        "Detailed raw metrics and errors are in the paired JSON file. Failed model runs are not attributed to a fallback generator.",
        "No differential-privacy or anonymity claim is made by these benchmarks.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=sorted(GENERATORS), required=True)
    parser.add_argument("--fixtures", nargs="+", default=["mixed"])
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--output-rows", type=int, default=240)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results"))
    args = parser.parse_args()
    if args.epochs < 1 or args.output_rows < 1:
        parser.error("epochs and output-rows must be positive")

    fixtures = make_fixtures(args.seed)
    unknown = sorted(set(args.fixtures) - set(fixtures))
    if unknown:
        parser.error(f"unknown fixtures: {', '.join(unknown)}")
    document = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_version": FIXTURE_VERSION,
        "benchmark_seed": args.seed,
        "dependency_versions": dependency_versions(),
        "runtime_environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "logical_cpu_count": __import__("os").cpu_count(),
            "memory_usage": "not measured (psutil is not a declared dependency)",
        },
        "configuration": {
            "epochs": args.epochs,
            "output_rows": args.output_rows,
            "models": args.models,
            "fixtures": args.fixtures,
        },
        "runs": [],
    }
    for fixture_name in args.fixtures:
        frame, target, task = fixtures[fixture_name]
        for model in args.models:
            print(f"Running {model} on {fixture_name} ({len(frame)} rows)...", flush=True)
            run = benchmark_run(
                fixture_name, frame, target, task, model, args.seed, args.epochs, args.output_rows
            )
            document["runs"].append(run)
            print(f"  generator status: {run['generator']['status']}", flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = args.output_dir / f"benchmark_{stamp}.json"
    markdown_path = args.output_dir / f"benchmark_{stamp}.md"
    json_path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")
    markdown_path.write_text(markdown_report(document))
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()

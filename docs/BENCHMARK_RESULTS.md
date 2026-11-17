# Benchmark results

## Latest attempted run

- Timestamp: 2026-11-17 12:42:45 UTC
- Fixture: `mixed`, fixture version `1.0.0` (240 rows, 3 columns)
- Seed: 42
- Requested models: GaussianCopula, CTGAN, TVAE
- Requested CTGAN/TVAE epochs: 2
- Result: all three model initialization attempts failed before fitting or sampling. **No model metrics were produced and there is no valid model comparison.**
- Actual model: none for all three attempts. No fallback occurred.

The shared failure was a local PyTorch dynamic-library import error: the installed `torch` package could not load `libtorch_cpu.dylib`. The run recorded package versions, runtime environment, per-attempt runtime, requested model/parameters, and the error. This is evidence of an environment limitation, not evidence about generator quality or performance.

- [Machine-readable run JSON](../backend/benchmark_results/benchmark_20261117T124246Z.json)
- [Generated run summary](../backend/benchmark_results/benchmark_20261117T124246Z.md)

## Reproducing benchmarks

From the repository root:

```bash
cd backend
./venv/bin/python -m scripts.run_evaluation_benchmarks \
  --models GaussianCopula CTGAN TVAE \
  --fixtures mixed \
  --epochs 10 \
  --seed 42 \
  --output-dir benchmark_results
```

The harness writes a JSON record and Markdown summary for each run. It records an actual model only after that requested model successfully fits and generates. If a generator fails, its result contains the error and the metrics remain unavailable; the harness does not substitute another model.

Fixtures available via `--fixtures` are `numerical_only`, `categorical_only`, `mixed`, `missing_values`, `imbalanced_classification`, `regression`, `high_cardinality`, `duplicate_records`, `small_dataset`, and `large_dataset`. CTGAN/TVAE fit times vary substantially with runtime, row count, feature cardinality, and epoch settings; run resource-intensive fixtures deliberately.

No resume or portfolio performance claim should be based on this failed run. A successful run is required before comparing model metrics.

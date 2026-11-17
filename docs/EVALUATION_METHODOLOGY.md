# SynthGen evaluation methodology

This document describes the implemented evaluation protocol. It reports empirical properties of the provided real and synthetic tables; it does not certify a generator or guarantee privacy.

## Independent components

The report contains four independent dimensions and execution metadata. It does not calculate a weighted overall percentage.

| Component | Main result | Direction | Main limitation |
|---|---|---|---|
| Schema fidelity | Names, dimensions, type families, duplicate labels, nullability, missing rates, empty/all-null columns | Structural mismatches are exposed; no universal pass threshold | Type-family compatibility does not prove semantic equivalence |
| Statistical fidelity | Numeric summaries and Wasserstein distance; categorical total variation; missingness; pair relationships | Distances and differences lower/closer; correlation values are compared by absolute change | Empirical and sample-size dependent; numeric distances use original units |
| Privacy-risk indicators | Exact matches and sampled mixed-type nearest-record distances | Exact matches are directly observed; smaller distance means greater similarity, without a universal risk cutoff | These measurements do not prove anonymity or differential privacy |
| ML utility | TRTR and TSTR task metrics on a shared real holdout | Higher accuracy/F1/AUC and R²; lower MAE/RMSE | Depends on the selected target, split, and random forest model family |

Each component carries a status. `INCOMPLETE` means the component could not produce all requested measurements or required configuration. A completed measurement does not mean quality acceptance. `quality_accepted` remains null until an explicit acceptance policy is defined.

## Schema fidelity

`evaluate_schema_fidelity(real, synthetic)` aligns fields by column name and preserves source order. It identifies missing and extra columns, repeated labels, row/column counts, broad type-family compatibility, per-column null counts/rates, nullable state, and all-null/empty columns.

Integer and floating point values share the numeric family. Boolean and datetime values are distinct. Object/string/category values share the categorical family. This checks storage representation, not meaning. Null-rate differences are synthetic rate minus real rate. Equal rates do not mean missing values occur on the same records.

## Column-level statistical fidelity

### Numeric columns

- **Mean, standard deviation, median:** reported separately for real and synthetic samples, plus absolute differences in original units. Standard deviation is the sample standard deviation (`ddof=1`) and is unavailable with fewer than two finite values.
- **Quantiles:** 1st, 25th, 50th, 75th, and 99th percentiles are computed on finite values. Differences are `synthetic − real` and remain in original units.
- **Wasserstein-1 distance:** in one dimension, this is the integral of the absolute difference between empirical cumulative distribution functions. It is nonnegative and zero for identical empirical distributions. Its units match the feature units, so distances cannot be averaged across differently scaled fields without a defined normalization.
- **Missingness:** reports null rate in each table and the signed difference `synthetic − real`. Non-finite numeric values are separately counted and excluded from numeric distribution summaries.

The Kolmogorov–Smirnov p-value is intentionally not used. A p-value is evidence under a hypothesis-test null, not a measure of closeness, and changes with sample size.

Datetime and other unsupported statistical dtype families are marked unavailable with a reason; they are not coerced into arbitrary numeric values.

### Categorical columns

- **Empirical distribution:** each value is represented with its scalar type to avoid conflating, for example, an integer label and its string representation. Missing values form an explicit category.
- **Total variation distance (TVD):** `TVD(P,Q) = ½ Σₖ |P(k) − Q(k)|`. It ranges from 0 to 1; lower is closer and 0 means identical empirical frequencies.
- **Unseen categories:** synthetic distinct values absent from real data are counted and examples are reported. The example list is capped at 50. Distribution detail is capped at 1,000 categories per column and reports omitted counts; TVD is calculated over all categories.

Category frequencies are sample estimates. This module does not compare semantic similarity between labels.

## Relationship fidelity

- **Numeric/numeric:** Pearson correlation is computed on pairwise complete finite rows. It ranges from −1 to 1 and captures linear association only. The report includes the real and synthetic values and their absolute difference. Correlation is unavailable for constant or insufficient observations.
- **Categorical/categorical:** uncorrected Cramér’s V is `sqrt(χ² / (n × min(r−1,c−1)))`, where `r` and `c` are observed category counts. It ranges from 0 to 1, but can be biased for small/sparse samples. Tables above 100,000 cells are explicitly unavailable.
- **Categorical/numeric:** correlation ratio η² is between-group numeric sum of squares divided by total numeric sum of squares. It ranges from 0 to 1 and measures the share of numeric variance associated with category groups. It can be optimistic for many sparse categories and is not causal evidence.

Missing rows are excluded pairwise in numeric and mixed calculations; missing categories remain an explicit category in categorical/categorical association.

## Privacy-risk indicators

Exact matching canonicalizes typed row values across the full aligned schema and counts fixed-size BLAKE2 digests; null matches null in the same field. It reports (1) synthetic row count with at least one real match, (2) matched-row proportion, (3) distinct matching record values, and (4) total matching pairs using duplicate multiplicities. Column order in the synthetic table may differ; duplicate column labels, missing/extra fields, incompatible types, or empty tables yield `INCOMPLETE` instead of a partial comparison. As with any digest-based equality key, collision probability is negligible for this use but not mathematically zero.

Nearest-record distances use deterministic samples (default maximum 1,000 rows from each table; seed 42) and chunked comparison. Numeric differences are absolute differences divided by the sampled real range and capped at 1. Categorical differences are 0/1. For a given field, both missing is 0 and one-sided missing is 1; non-finite numeric values are handled as missing for distance only. Field distances are equally averaged, producing a Gower-style distance in [0,1]. The report contains quantiles and sample configuration, not a cutoff or aggregate privacy score.

This measurement depends on feature scales, equal field weighting, the sample, and the real sample's numeric range. It does not estimate an attacker's success probability. Membership and attribute disclosure tests are not implemented because SynthGen has no explicit member/non-member reference split or configured quasi-identifiers/sensitive attributes. No differential-privacy mechanism is implemented or claimed.

## Downstream ML utility

The caller must configure both `target_column` and `task_type` (`classification` or `regression`). If not configured or ambiguous, the evaluator returns `INCOMPLETE`; it never chooses the final column or infers task type from cardinality. API clients may provide `evaluation_target` and `evaluation_task` during upload or prompt-based generation.

TRTR (Train-on-Real/Test-on-Real) and TSTR (Train-on-Synthetic/Test-on-Real) use the same deterministic holdout rows from the real dataset. TRTR trains on the real training partition. TSTR trains on synthetic rows and tests on the same untouched real holdout. Separate preprocessing pipelines are fit only on each respective training set:

- Numeric features use median imputation.
- Categorical features are converted to typed tokens, imputed with an explicit missing marker, and one-hot encoded. Unknown test categories are ignored by the one-hot encoder and do not change the fitted vocabulary.
- Classification labels are encoded from the real training labels only. Synthetic target classes absent from that training partition are counted and excluded.

The default model is a deterministic random forest (100 estimators, `random_state=42`, single-threaded). Classification reports accuracy, weighted precision/recall/F1, confusion matrix, and ROC-AUC when class coverage and probabilities support it. Regression reports MAE, RMSE, and unbounded R². R² may be negative; it is not clipped. R² is unavailable for a constant test target. MAPE is omitted because zero and near-zero target values make it unsuitable without additional policy.

Five real target rows and two synthetic target rows are the minimum for the implemented split/training protocol. This is an operational minimum, not evidence of statistical power. Results depend on the chosen target, split, and model family. TSTR is not a privacy metric.

## Reproducibility and runtime

Evaluation metadata records a UTC timestamp, runtime, dataset dimensions, configured target/task/seed, requested and actual generator, fallback reason, effective generation parameters, SDV version, and relevant Python package versions where available. Privacy uses a fixed seed. ML split/model seeds are explicit. Generator sampling uses an SDV random-state hook when exposed by the installed SDV 1.x implementation; this hook is internal and reported seed scope states that model fitting may still use framework randomness.

Evaluation runs in the existing worker workflow, which has a 900-second outer timeout. Privacy nearest-neighbor comparison is chunked to bound working memory. Association tables and categorical details have explicit caps. No per-component cancellation/timeout is currently available.

## Running

From the repository root:

```bash
cd backend
./venv/bin/python -m pytest -q tests
./venv/bin/python -m scripts.run_evaluation_benchmarks \
  --models GaussianCopula CTGAN TVAE --fixtures mixed --epochs 10 --seed 42
```

Benchmark outputs are written to `backend/benchmark_results/` by default. The latest attempted run and its actual result are documented in `docs/BENCHMARK_RESULTS.md`.

To configure utility evaluation in the API, provide both fields:

```json
{
  "evaluation_target": "churned",
  "evaluation_task": "classification"
}
```

For file upload, send `evaluation_target` and `evaluation_task` as multipart fields. Omitting them intentionally leaves ML utility `INCOMPLETE`; it does not affect schema, statistical, or privacy reporting.

## Interpretation boundaries

These components describe observed structural, statistical, disclosure-risk, and predictive-utility behavior under the configured protocol. They do not prove that synthetic data is representative for every use, safe for release, anonymous, differentially private, legally compliant, or suitable for a particular deployment. An acceptance decision requires a separately defined use case and policy.

"""Raw statistical fidelity metrics; deliberately does not produce one score."""

from itertools import combinations
from typing import Any, Dict, List, Tuple


_QUANTILES = (0.01, 0.25, 0.50, 0.75, 0.99)
_MAX_ASSOCIATION_CELLS = 100_000
_MAX_UNSEEN_VALUES = 50
_MAX_CATEGORY_DISTRIBUTION_ENTRIES = 1_000


def _family(series) -> str:
    import pandas as pd

    if pd.api.types.is_bool_dtype(series.dtype):
        return "categorical"
    if pd.api.types.is_numeric_dtype(series.dtype):
        return "numeric"
    if (
        pd.api.types.is_string_dtype(series.dtype)
        or pd.api.types.is_object_dtype(series.dtype)
        or isinstance(series.dtype, pd.CategoricalDtype)
    ):
        return "categorical"
    return "unsupported"


def _value_key(value: Any, is_null: bool = False) -> str:
    import json

    if is_null:
        return json.dumps(["missing", "<NA>"])
    return json.dumps([
        f"{type(value).__module__}.{type(value).__qualname__}",
        repr(value),
    ], ensure_ascii=False)


def _category_counts(series) -> Tuple[Dict[str, int], Dict[str, str]]:
    counts: Dict[str, int] = {}
    display: Dict[str, str] = {}
    for value in series.array:
        try:
            is_null = bool(__import__("pandas").isna(value))
        except (TypeError, ValueError):
            is_null = False
        key = _value_key(value, is_null)
        counts[key] = counts.get(key, 0) + 1
        if key not in display:
            display[key] = "<MISSING>" if is_null else repr(value)
    return counts, display


def _missing_rate(series) -> float:
    return float(series.isna().mean()) if len(series) else None


def _numeric_metrics(real_series, synthetic_series) -> Dict[str, Any]:
    import numpy as np
    import pandas as pd
    from scipy.stats import wasserstein_distance

    real_numeric = pd.to_numeric(real_series, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    synthetic_numeric = pd.to_numeric(synthetic_series, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    real_values = real_numeric[np.isfinite(real_numeric)]
    synthetic_values = synthetic_numeric[np.isfinite(synthetic_numeric)]
    result: Dict[str, Any] = {
        "status": "COMPLETED",
        "metric_directions": {
            "mean_difference": "absolute difference; lower is closer, in original units",
            "standard_deviation_difference": "absolute difference; lower is closer, in original units",
            "median_difference": "absolute difference; lower is closer, in original units",
            "quantile_differences": "synthetic minus real; zero is exact, in original units",
            "wasserstein_distance": "lower is closer; in original units",
        },
        "real_non_null_count": int(len(real_series) - real_series.isna().sum()),
        "synthetic_non_null_count": int(len(synthetic_series) - synthetic_series.isna().sum()),
        "real_finite_count": int(len(real_values)),
        "synthetic_finite_count": int(len(synthetic_values)),
        "real_missing_rate": _missing_rate(real_series),
        "synthetic_missing_rate": _missing_rate(synthetic_series),
        "missing_rate_difference": (
            _missing_rate(synthetic_series) - _missing_rate(real_series)
            if _missing_rate(synthetic_series) is not None and _missing_rate(real_series) is not None
            else None
        ),
        "non_finite_real_count": int(
            len(real_series) - real_series.isna().sum() - len(real_values)
        ),
        "non_finite_synthetic_count": int(
            len(synthetic_series) - synthetic_series.isna().sum() - len(synthetic_values)
        ),
        "real_mean": None,
        "synthetic_mean": None,
        "mean_difference": None,
        "real_standard_deviation": None,
        "synthetic_standard_deviation": None,
        "standard_deviation_difference": None,
        "real_median": None,
        "synthetic_median": None,
        "median_difference": None,
        "quantiles": {},
        "wasserstein_distance": None,
        "unavailable_metrics": [],
    }
    if not len(real_values) or not len(synthetic_values):
        result["status"] = "INCOMPLETE"
        result["unavailable_metrics"].append({
            "metric": "numeric_distribution",
            "reason": "At least one dataset has no finite numeric observations.",
        })
        return result

    real_mean = float(np.mean(real_values))
    synthetic_mean = float(np.mean(synthetic_values))
    real_std = float(np.std(real_values, ddof=1)) if len(real_values) > 1 else None
    synthetic_std = float(np.std(synthetic_values, ddof=1)) if len(synthetic_values) > 1 else None
    real_median = float(np.median(real_values))
    synthetic_median = float(np.median(synthetic_values))
    result.update({
        "real_mean": real_mean,
        "synthetic_mean": synthetic_mean,
        "mean_difference": abs(synthetic_mean - real_mean),
        "real_standard_deviation": real_std,
        "synthetic_standard_deviation": synthetic_std,
        "standard_deviation_difference": (
            abs(synthetic_std - real_std)
            if synthetic_std is not None and real_std is not None
            else None
        ),
        "real_median": real_median,
        "synthetic_median": synthetic_median,
        "median_difference": abs(synthetic_median - real_median),
        "quantiles": {
            str(q): {
                "real": float(np.quantile(real_values, q)),
                "synthetic": float(np.quantile(synthetic_values, q)),
                "difference": float(np.quantile(synthetic_values, q) - np.quantile(real_values, q)),
            }
            for q in _QUANTILES
        },
        "wasserstein_distance": float(wasserstein_distance(real_values, synthetic_values)),
    })
    if real_std is None or synthetic_std is None:
        result["unavailable_metrics"].append({
            "metric": "standard_deviation_difference",
            "reason": "Sample standard deviation requires at least two finite observations per dataset.",
        })
    return result


def _categorical_metrics(real_series, synthetic_series) -> Dict[str, Any]:
    real_counts, real_display = _category_counts(real_series)
    synthetic_counts, synthetic_display = _category_counts(synthetic_series)
    real_n = len(real_series)
    synthetic_n = len(synthetic_series)
    categories = sorted(set(real_counts) | set(synthetic_counts))
    total_variation = 0.5 * sum(
        abs(real_counts.get(key, 0) / real_n - synthetic_counts.get(key, 0) / synthetic_n)
        for key in categories
    ) if real_n and synthetic_n else None
    real_non_missing = set(real_counts) - {_value_key(None, True)}
    synthetic_non_missing = set(synthetic_counts) - {_value_key(None, True)}
    unseen = sorted(synthetic_non_missing - real_non_missing)
    ranked_categories = sorted(
        categories,
        key=lambda key: (-(real_counts.get(key, 0) + synthetic_counts.get(key, 0)), key),
    )
    shown_categories = ranked_categories[:_MAX_CATEGORY_DISTRIBUTION_ENTRIES]
    real_missing_rate = _missing_rate(real_series)
    synthetic_missing_rate = _missing_rate(synthetic_series)
    return {
        "status": "COMPLETED" if real_n and synthetic_n else "INCOMPLETE",
        "total_variation_distance": float(total_variation) if total_variation is not None else None,
        "total_variation_distance_range": [0.0, 1.0],
        "total_variation_direction": "lower is closer; 0 means identical empirical distributions",
        "real_category_count": int(len(real_non_missing)),
        "synthetic_category_count": int(len(synthetic_non_missing)),
        "unseen_synthetic_category_count": len(unseen),
        "unseen_synthetic_categories": [synthetic_display[key] for key in unseen[:_MAX_UNSEEN_VALUES]],
        "unseen_category_list_truncated": len(unseen) > _MAX_UNSEEN_VALUES,
        "category_distribution_entry_count": len(categories),
        "category_distribution_omitted_count": max(0, len(categories) - len(shown_categories)),
        "category_distribution_truncated": len(categories) > _MAX_CATEGORY_DISTRIBUTION_ENTRIES,
        "real_missing_rate": real_missing_rate,
        "synthetic_missing_rate": synthetic_missing_rate,
        "missing_rate_difference": (
            synthetic_missing_rate - real_missing_rate
            if real_n and synthetic_n else None
        ),
        "category_distribution": [
            {
                "category_key": key,
                "display_value": real_display.get(key, synthetic_display.get(key, key)),
                "real_probability": real_counts.get(key, 0) / real_n if real_n else None,
                "synthetic_probability": synthetic_counts.get(key, 0) / synthetic_n if synthetic_n else None,
            }
            for key in shown_categories
        ],
        "limitations": [
            "Empirical category frequencies depend on sample size and do not measure semantic similarity between categories.",
        ],
    }


def _numeric_correlations(data, columns) -> Dict[Tuple[Any, Any], Any]:
    import numpy as np
    import pandas as pd

    result = {}
    for left, right in combinations(columns, 2):
        pair = data[[left, right]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(pair) < 2 or pair[left].nunique() < 2 or pair[right].nunique() < 2:
            result[(left, right)] = None
        else:
            result[(left, right)] = float(pair[left].corr(pair[right], method="pearson"))
    return result


def _categorical_key_series(series):
    import pandas as pd

    values = []
    for value in series.array:
        try:
            is_null = bool(pd.isna(value))
        except (TypeError, ValueError):
            is_null = False
        values.append(_value_key(value, is_null))
    return pd.Series(values, index=series.index, dtype="object")


def _categorical_association(frame, left, right):
    import numpy as np
    import pandas as pd
    from scipy.stats import chi2_contingency

    x = _categorical_key_series(frame[left])
    y = _categorical_key_series(frame[right])
    contingency_shape = (int(x.nunique()), int(y.nunique()))
    if contingency_shape[0] * contingency_shape[1] > _MAX_ASSOCIATION_CELLS:
        return None, "Contingency table exceeds configured cell limit."
    table = pd.crosstab(x, y)
    n = int(table.to_numpy().sum())
    rows, cols = table.shape
    if n == 0 or min(rows, cols) < 2:
        return None, "Association requires at least two observed categories per variable."
    chi2 = float(chi2_contingency(table, correction=False)[0])
    value = float(np.sqrt(chi2 / (n * min(rows - 1, cols - 1))))
    return value, None


def _mixed_association(frame, categorical, numerical):
    import numpy as np
    import pandas as pd

    categories = _categorical_key_series(frame[categorical])
    numbers = pd.to_numeric(frame[numerical], errors="coerce").replace([np.inf, -np.inf], np.nan)
    paired = pd.DataFrame({"category": categories, "number": numbers}).dropna()
    if len(paired) < 2 or paired["number"].nunique() < 2:
        return None, "Association requires at least two paired rows and non-constant numeric values."
    grand_mean = float(paired["number"].mean())
    total = float(((paired["number"] - grand_mean) ** 2).sum())
    if total == 0:
        return None, "Association is undefined for a constant numeric variable."
    between = sum(
        len(group) * (float(group.mean()) - grand_mean) ** 2
        for _, group in paired.groupby("category", sort=True)["number"]
    )
    return float(between / total), None


def _relationships(real_data, synthetic_data, compatible_columns):
    numeric = [c for c in compatible_columns if _family(real_data[c]) == "numeric"]
    categorical = [c for c in compatible_columns if _family(real_data[c]) == "categorical"]
    records = []

    real_corr = _numeric_correlations(real_data, numeric)
    synthetic_corr = _numeric_correlations(synthetic_data, numeric)
    for pair in combinations(numeric, 2):
        real_value, synthetic_value = real_corr[pair], synthetic_corr[pair]
        records.append({
            "columns": [str(pair[0]), str(pair[1])],
            "method": "pearson_correlation",
            "range": [-1.0, 1.0],
            "direction": "absolute change closer to 0 means better preservation",
            "real_value": real_value,
            "synthetic_value": synthetic_value,
            "absolute_difference": abs(real_value - synthetic_value) if real_value is not None and synthetic_value is not None else None,
            "status": "COMPLETED" if real_value is not None and synthetic_value is not None else "UNAVAILABLE",
            "reason": None if real_value is not None and synthetic_value is not None else "Correlation undefined for insufficient or constant observations.",
        })

    for left, right in combinations(categorical, 2):
        real_value, real_reason = _categorical_association(real_data, left, right)
        synthetic_value, synthetic_reason = _categorical_association(synthetic_data, left, right)
        records.append({
            "columns": [str(left), str(right)],
            "method": "cramers_v",
            "range": [0.0, 1.0],
            "direction": "absolute change closer to 0 means better preservation; higher values mean stronger association",
            "real_value": real_value,
            "synthetic_value": synthetic_value,
            "absolute_difference": abs(real_value - synthetic_value) if real_value is not None and synthetic_value is not None else None,
            "status": "COMPLETED" if real_value is not None and synthetic_value is not None else "UNAVAILABLE",
            "reason": real_reason or synthetic_reason,
        })

    for categorical_column in categorical:
        for numerical_column in numeric:
            real_value, real_reason = _mixed_association(real_data, categorical_column, numerical_column)
            synthetic_value, synthetic_reason = _mixed_association(synthetic_data, categorical_column, numerical_column)
            records.append({
                "columns": [str(categorical_column), str(numerical_column)],
                "method": "correlation_ratio_eta_squared",
                "range": [0.0, 1.0],
                "direction": "absolute change closer to 0 means better preservation; value measures numeric variance explained by categories",
                "real_value": real_value,
                "synthetic_value": synthetic_value,
                "absolute_difference": abs(real_value - synthetic_value) if real_value is not None and synthetic_value is not None else None,
                "status": "COMPLETED" if real_value is not None and synthetic_value is not None else "UNAVAILABLE",
                "reason": real_reason or synthetic_reason,
            })
    return records


def evaluate_statistical_quality(
    real_data, synthetic_data, schema_result: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Return per-column and relationship metrics with units and limitations.

    No aggregate score is returned. Numeric Wasserstein distances and moments
    are in original units; categorical TVD is dimensionless in [0, 1].
    """
    from app.tools.schema_evaluator import evaluate_schema_fidelity

    schema = schema_result or evaluate_schema_fidelity(real_data, synthetic_data)
    real_positions = {name: i for i, name in enumerate(real_data.columns) if list(real_data.columns).count(name) == 1}
    synthetic_positions = {name: i for i, name in enumerate(synthetic_data.columns) if list(synthetic_data.columns).count(name) == 1}
    columns = {}
    compatible = []
    duplicate_names = set(schema["duplicate_real_columns"]) | set(schema["duplicate_synthetic_columns"])
    checks = {check["column"]: check for check in schema["columns"]}

    for name in real_data.columns:
        key = str(name)
        if key in columns:
            continue
        if key in duplicate_names:
            columns[key] = {
                "status": "UNAVAILABLE",
                "reason": "Duplicate column labels make name-based comparison ambiguous.",
            }
            continue
        if name not in synthetic_positions:
            columns[key] = {"status": "UNAVAILABLE", "reason": "Column is missing from synthetic data."}
            continue
        check = checks.get(key, {})
        if check.get("type_compatible") is not True:
            columns[key] = {
                "status": "UNAVAILABLE",
                "reason": "Real and synthetic column types are incompatible.",
                "schema_check": check,
            }
            continue
        real_series = real_data.iloc[:, real_positions[name]]
        synthetic_series = synthetic_data.iloc[:, synthetic_positions[name]]
        family = _family(real_series)
        if family == "numeric":
            metrics = _numeric_metrics(real_series, synthetic_series)
        elif family == "categorical":
            metrics = _categorical_metrics(real_series, synthetic_series)
        else:
            columns[key] = {
                "status": "UNAVAILABLE",
                "reason": f"Unsupported statistical type family: {family}.",
            }
            continue
        columns[key] = {"type": family, **metrics}
        if metrics["status"] == "COMPLETED":
            compatible.append(name)

    relationships = _relationships(real_data, synthetic_data, compatible)
    has_unavailable_column = any(
        metrics.get("status") != "COMPLETED" for metrics in columns.values()
    )
    has_unavailable_relationship = any(
        relationship.get("status") != "COMPLETED" for relationship in relationships
    )
    status = (
        "INCOMPLETE"
        if len(real_data) == 0 or len(synthetic_data) == 0
        or has_unavailable_column or has_unavailable_relationship
        else "COMPLETED"
    )
    return {
        "status": status,
        "columns": columns,
        "relationships": relationships,
        "configuration": {
            "quantiles": list(_QUANTILES),
            "maximum_association_cells": _MAX_ASSOCIATION_CELLS,
            "maximum_category_distribution_entries": _MAX_CATEGORY_DISTRIBUTION_ENTRIES,
        },
        "limitations": [
            "Wasserstein distance and moment differences use original feature units, so magnitudes are not comparable across differently scaled columns.",
            "Empirical distances and category frequencies depend on sample size; a small distance does not prove the generating distributions are equal.",
            "Constant numeric columns have zero correlation with other variables by definition; affected relationship metrics are reported unavailable.",
            "Pearson correlation measures linear association only.",
            "Cramer's V is uncorrected for finite-sample bias; high-cardinality associations can be unavailable due to a configured contingency-table limit.",
            "Correlation ratio can be optimistic with many sparse categories and is an association measure, not a causal relationship.",
        ],
    }

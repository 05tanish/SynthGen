"""Schema and structural compatibility checks for real/synthetic tables."""

from typing import Any, Dict, List


def _type_family(series) -> str:
    import pandas as pd

    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if (
        pd.api.types.is_string_dtype(dtype)
        or pd.api.types.is_object_dtype(dtype)
        or isinstance(dtype, pd.CategoricalDtype)
    ):
        return "categorical"
    return "unsupported"


def _positions(columns) -> Dict[Any, List[int]]:
    positions: Dict[Any, List[int]] = {}
    for index, name in enumerate(columns):
        positions.setdefault(name, []).append(index)
    return positions


def evaluate_schema_fidelity(real_data, synthetic_data) -> Dict[str, Any]:
    """Compare table structure without silently dropping schema differences.

    Type families are intentionally broad: integer/float are compatible numeric
    representations, while booleans and datetimes remain distinct. The result
    describes compatibility; it does not coerce either input.
    """
    real_positions = _positions(real_data.columns)
    synthetic_positions = _positions(synthetic_data.columns)
    real_names = set(real_positions)
    synthetic_names = set(synthetic_positions)
    duplicate_real = [str(name) for name, positions in real_positions.items() if len(positions) > 1]
    duplicate_synthetic = [
        str(name) for name, positions in synthetic_positions.items() if len(positions) > 1
    ]

    common_names = [name for name in real_data.columns if name in synthetic_names]
    column_checks = []
    for name in common_names:
        if len(real_positions[name]) != 1 or len(synthetic_positions[name]) != 1:
            column_checks.append({
                "column": str(name),
                "status": "UNAVAILABLE",
                "reason": "Duplicate column labels make name-based comparison ambiguous.",
            })
            continue
        real_series = real_data.iloc[:, real_positions[name][0]]
        synthetic_series = synthetic_data.iloc[:, synthetic_positions[name][0]]
        real_family = _type_family(real_series)
        synthetic_family = _type_family(synthetic_series)
        compatible = real_family == synthetic_family or {
            real_family, synthetic_family
        } <= {"numeric"}
        real_null_count = int(real_series.isna().sum())
        synthetic_null_count = int(synthetic_series.isna().sum())
        real_null_rate = real_null_count / len(real_series) if len(real_series) else None
        synthetic_null_rate = (
            synthetic_null_count / len(synthetic_series) if len(synthetic_series) else None
        )
        column_checks.append({
            "column": str(name),
            "status": "COMPLETED" if compatible else "INCOMPATIBLE",
            "type_compatible": compatible,
            "real_type": str(real_series.dtype),
            "synthetic_type": str(synthetic_series.dtype),
            "real_type_family": real_family,
            "synthetic_type_family": synthetic_family,
            "real_null_count": real_null_count,
            "synthetic_null_count": synthetic_null_count,
            "real_nullable": real_null_count > 0,
            "synthetic_nullable": synthetic_null_count > 0,
            "nullability_matches": (real_null_count > 0) == (synthetic_null_count > 0),
            "real_missing_rate": real_null_rate,
            "synthetic_missing_rate": synthetic_null_rate,
            "missing_rate_difference": (
                synthetic_null_rate - real_null_rate
                if real_null_rate is not None and synthetic_null_rate is not None
                else None
            ),
            "real_all_null": bool(len(real_series) > 0 and real_null_count == len(real_series)),
            "synthetic_all_null": bool(
                len(synthetic_series) > 0 and synthetic_null_count == len(synthetic_series)
            ),
            "real_empty": len(real_series) == 0,
            "synthetic_empty": len(synthetic_series) == 0,
        })

    issues = []
    if real_names - synthetic_names:
        issues.append("missing_columns")
    if synthetic_names - real_names:
        issues.append("unexpected_columns")
    if duplicate_real or duplicate_synthetic:
        issues.append("duplicate_columns")
    if any(check.get("type_compatible") is False for check in column_checks):
        issues.append("incompatible_types")
    if any(check.get("nullability_matches") is False for check in column_checks):
        issues.append("nullability_mismatch")
    if len(real_data) == 0 or len(synthetic_data) == 0:
        issues.append("empty_dataset")

    return {
        "status": "COMPLETED",
        "valid": not issues,
        "issues": issues,
        "real_row_count": int(len(real_data)),
        "synthetic_row_count": int(len(synthetic_data)),
        "row_count_difference": int(len(synthetic_data) - len(real_data)),
        "real_column_count": int(len(real_data.columns)),
        "synthetic_column_count": int(len(synthetic_data.columns)),
        "column_count_difference": int(len(synthetic_data.columns) - len(real_data.columns)),
        "missing_columns": [str(name) for name in real_data.columns if name not in synthetic_names],
        "unexpected_columns": [
            str(name) for name in synthetic_data.columns if name not in real_names
        ],
        "duplicate_real_columns": duplicate_real,
        "duplicate_synthetic_columns": duplicate_synthetic,
        "columns": column_checks,
        "configuration": {
            "numeric_type_family": "integer and floating-point dtypes are compatible",
            "categorical_type_family": "string, object, and categorical dtypes are compatible",
            "boolean_is_distinct": True,
            "datetime_is_distinct": True,
            "column_alignment": "column names, source order retained",
        },
        "limitations": [
            "Type families describe representation compatibility, not semantic equivalence.",
            "A zero missing-rate difference does not imply that missing values occur on the same rows.",
        ],
    }

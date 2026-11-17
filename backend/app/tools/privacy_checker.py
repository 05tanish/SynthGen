"""Empirical privacy-risk indicators (not formal privacy guarantees)."""

from collections import Counter
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, Optional


def _is_null(value) -> bool:
    import pandas as pd

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _is_numeric_missing(value) -> bool:
    import numpy as np

    if _is_null(value):
        return True
    try:
        return not bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return True


def _scalar_token(value, family: str) -> str:
    if _is_null(value):
        return "<MISSING>"
    if family == "numeric":
        return f"numeric:{Decimal(str(value)).normalize()}"
    if family == "boolean":
        return f"boolean:{bool(value)}"
    return f"{type(value).__module__}.{type(value).__qualname__}:{value!r}"


def _row_keys(frame, columns, families):
    keys = []
    for row in range(len(frame)):
        canonical_values = [
            _scalar_token(frame.iloc[row, col_index], families[column])
            for col_index, column in enumerate(columns)
        ]
        payload = json.dumps(canonical_values, ensure_ascii=False, separators=(",", ":"))
        keys.append(hashlib.blake2b(payload.encode("utf-8"), digest_size=20).hexdigest())
    return keys


def _sample_positions(length: int, limit: int, seed: int):
    import numpy as np

    if length <= limit:
        return np.arange(length, dtype=int)
    return np.sort(np.random.default_rng(seed).choice(length, size=limit, replace=False))


def _gower_nearest_distances(real, synthetic, columns, families, real_positions, synth_positions, batch_size):
    """Compute chunked Gower-style mixed distances with O(batch * real) memory."""
    import numpy as np

    real_values = [real.iloc[real_positions][column].to_numpy(dtype=object) for column in columns]
    synthetic_values = [synthetic.iloc[synth_positions][column].to_numpy(dtype=object) for column in columns]
    numeric_ranges = {}
    for index, column in enumerate(columns):
        if families[column] == "numeric":
            values = np.asarray([
                float(value) for value in real_values[index]
                if not _is_numeric_missing(value)
            ], dtype=float)
            span = float(np.max(values) - np.min(values)) if len(values) else 0.0
            numeric_ranges[column] = span

    minima = np.full(len(synth_positions), np.inf, dtype=float)
    for start in range(0, len(synth_positions), batch_size):
        stop = min(start + batch_size, len(synth_positions))
        batch_min = np.full(stop - start, np.inf, dtype=float)
        for feature_index, column in enumerate(columns):
            real_column = real_values[feature_index]
            synth_column = synthetic_values[feature_index][start:stop]
            if families[column] == "numeric":
                real_null = np.asarray([_is_numeric_missing(value) for value in real_column])
                synth_null = np.asarray([_is_numeric_missing(value) for value in synth_column])
                real_num = np.asarray([0.0 if missing else float(value) for value, missing in zip(real_column, real_null)])
                synth_num = np.asarray([0.0 if missing else float(value) for value, missing in zip(synth_column, synth_null)])
                span = numeric_ranges[column]
                if span == 0.0:
                    difference = (real_num[None, :] != synth_num[:, None]).astype(float)
                else:
                    difference = np.minimum(
                        np.abs(synth_num[:, None] - real_num[None, :]) / span, 1.0
                    )
                difference = np.where(
                    synth_null[:, None] == real_null[None, :], difference, 1.0
                )
                difference = np.where(synth_null[:, None] & real_null[None, :], 0.0, difference)
            else:
                real_tokens = np.asarray([_scalar_token(value, families[column]) for value in real_column], dtype=object)
                synth_tokens = np.asarray([_scalar_token(value, families[column]) for value in synth_column], dtype=object)
                difference = (synth_tokens[:, None] != real_tokens[None, :]).astype(float)
            batch_min = np.minimum(batch_min, difference.min(axis=1))
        minima[start:stop] = batch_min / max(len(columns), 1)
    return minima, numeric_ranges


def evaluate_privacy_risk(
    real_data,
    synthetic_data,
    *,
    sample_size: int = 1000,
    random_seed: int = 42,
    batch_size: int = 64,
) -> Dict[str, Any]:
    """Report exact matching and raw mixed-type nearest-real-record distances.

    The distance is Gower-style: categorical mismatches are 0/1; numeric
    absolute differences are divided by the sampled real range and capped at 1;
    missing-value agreement is 0 for both missing and 1 for one-sided missing.
    Per-feature distances are averaged, so the final range is [0, 1].
    """
    import numpy as np
    import pandas as pd
    from app.tools.schema_evaluator import _type_family

    if sample_size < 1 or batch_size < 1:
        raise ValueError("sample_size and batch_size must be positive integers")
    duplicate_real = real_data.columns.duplicated().any()
    duplicate_synthetic = synthetic_data.columns.duplicated().any()
    if duplicate_real or duplicate_synthetic:
        return {
            "status": "INCOMPLETE",
            "metrics": {},
            "errors": [{"component": "privacy", "message": "Duplicate column labels prevent unambiguous record comparison."}],
            "limitations": ["No privacy-risk distance or match count was produced."],
        }

    columns = [column for column in real_data.columns if column in synthetic_data.columns]
    if not columns:
        return {
            "status": "INCOMPLETE",
            "metrics": {},
            "errors": [{"component": "privacy", "message": "No common columns are available for record comparison."}],
            "limitations": ["No privacy-risk distance or match count was produced."],
        }
    extra_or_missing = set(real_data.columns) != set(synthetic_data.columns)
    columns = list(real_data.columns)
    families = {column: _type_family(real_data[column]) for column in columns}
    incompatible = [
        column for column in columns
        if column in synthetic_data.columns
        and _type_family(real_data[column]) != _type_family(synthetic_data[column])
    ]
    if incompatible or extra_or_missing:
        return {
            "status": "INCOMPLETE",
            "metrics": {},
            "errors": [{
                "component": "privacy",
                "message": "Record comparison requires identical columns and compatible type families.",
                "incompatible_columns": [str(column) for column in incompatible],
                "missing_columns": [str(column) for column in real_data.columns if column not in synthetic_data.columns],
                "unexpected_columns": [str(column) for column in synthetic_data.columns if column not in real_data.columns],
            }],
            "limitations": ["No privacy-risk distance or match count was produced because schemas differ."],
        }
    if not len(real_data) or not len(synthetic_data):
        return {
            "status": "INCOMPLETE",
            "metrics": {},
            "errors": [{"component": "privacy", "message": "Both datasets must contain at least one row."}],
            "limitations": ["No privacy-risk distance or match count was produced."],
        }

    # Align by the real table's order; column order in the synthetic table may differ.
    real_aligned = real_data.loc[:, columns]
    synthetic_aligned = synthetic_data.loc[:, columns]
    real_families = {column: ("boolean" if pd.api.types.is_bool_dtype(real_aligned[column].dtype) else families[column]) for column in columns}
    real_keys = _row_keys(real_aligned, columns, real_families)
    synthetic_keys = _row_keys(synthetic_aligned, columns, real_families)
    real_counts = Counter(real_keys)
    synthetic_counts = Counter(synthetic_keys)
    matching_keys = set(real_counts) & set(synthetic_counts)
    matched_synthetic_rows = sum(synthetic_counts[key] for key in matching_keys)
    total_matching_pairs = sum(real_counts[key] * synthetic_counts[key] for key in matching_keys)

    real_sample_positions = _sample_positions(len(real_data), sample_size, random_seed)
    synthetic_sample_positions = _sample_positions(len(synthetic_data), sample_size, random_seed + 1)
    distances, numeric_ranges = _gower_nearest_distances(
        real_aligned,
        synthetic_aligned,
        columns,
        real_families,
        real_sample_positions,
        synthetic_sample_positions,
        batch_size,
    )
    quantiles = {str(q): float(np.quantile(distances, q)) for q in (0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0)}
    return {
        "status": "COMPLETED",
        "metrics": {
            "exact_match": {
                "synthetic_rows_with_real_match": int(matched_synthetic_rows),
                "synthetic_row_match_rate": float(matched_synthetic_rows / len(synthetic_data)),
                "unique_matching_record_values": int(len(matching_keys)),
                "total_matching_pairs": int(total_matching_pairs),
                "real_unique_record_values": int(len(real_counts)),
                "synthetic_unique_record_values": int(len(synthetic_counts)),
                "risk_category": "DIRECT_DISCLOSURE_OBSERVED" if matched_synthetic_rows else "NO_EXACT_MATCH_OBSERVED",
                "interpretation": "Exact equality across all shared schema columns; duplicate multiplicities are reported separately. No observed exact match does not establish anonymity.",
                "recommended_mitigation": "Review generator memorization, training-row duplication, and model configuration when exact matches occur; assess the use context even when none are observed.",
            },
            "nearest_neighbor_distance": {
                "name": "sampled synthetic-to-real Gower-style distance",
                "range": [0.0, 1.0],
                "direction": "smaller means more similar to a real record; no universal risk cutoff is applied",
                "risk_category": "NOT_CLASSIFIED_NO_UNIVERSAL_THRESHOLD",
                "recommended_mitigation": "Investigate the closest sampled records and review the release context; do not interpret a distance value as a calibrated safe/unsafe threshold.",
                "distance_quantiles": quantiles,
                "sampled_synthetic_rows": int(len(synthetic_sample_positions)),
                "sampled_real_rows": int(len(real_sample_positions)),
                "sample_seed": int(random_seed),
                "numeric_real_sample_ranges": {str(column): value for column, value in numeric_ranges.items()},
                "batch_size": int(batch_size),
                "preprocessing": "Numeric absolute differences are divided by sampled real range and capped at one; categorical mismatches are zero/one; missing agreement is explicit; feature distances are equally averaged.",
            },
        },
        "configuration": {
            "sample_size_per_dataset": int(sample_size),
            "random_seed": int(random_seed),
            "batch_size": int(batch_size),
            "column_order": [str(column) for column in columns],
        },
        "limitations": [
            "These are empirical disclosure-risk indicators, not anonymity or differential-privacy guarantees.",
            "Exact matching checks the full aligned table; missing values match only other missing values in the same column.",
            "Nearest-neighbor distances are sampled, depend on real-sample numeric ranges and equal feature weighting, and are not calibrated to an attack success probability.",
            "No membership or attribute disclosure attack is performed; those require a separate defensible member/non-member or quasi-identifier protocol.",
        ],
    }

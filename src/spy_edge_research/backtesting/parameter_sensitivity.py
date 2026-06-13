"""Research-only parameter sensitivity helpers.

These helpers evaluate how descriptive research metrics vary across explicit
parameter combinations. They do not optimize parameters, select strategy rules,
create signals, or claim edge.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

import itertools

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    json_safe_mapping as _json_safe_mapping,
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)


PARAMETER_GRID_ID_COLUMN = "parameter_set_id"
PARAMETER_GRID_VALUE_COLUMN = "parameters"

PARAMETER_SENSITIVITY_SUMMARY_COLUMNS: list[str] = [
    "metric_column",
    "parameter_set_count",
    "non_missing_count",
    "metric_min",
    "metric_max",
    "metric_range",
    "metric_mean",
    "metric_std",
    "relative_range",
    "sensitivity_flag",
    "caveats",
]


def build_parameter_grid(
    parameter_values: Mapping[str, Iterable[Any]],
    *,
    parameter_set_prefix: str = "params",
) -> pd.DataFrame:
    """Build a deterministic cartesian parameter grid."""
    if not isinstance(parameter_values, Mapping):
        raise TypeError("parameter_values must be a mapping")
    if not isinstance(parameter_set_prefix, str) or not parameter_set_prefix:
        raise ValueError("parameter_set_prefix must be a non-empty string")
    if not parameter_values:
        raise ValueError("parameter_values must contain at least one parameter")

    names = list(parameter_values.keys())
    if not all(isinstance(name, str) and name for name in names):
        raise ValueError("parameter names must be non-empty strings")
    values_by_name = {name: list(values) for name, values in parameter_values.items()}
    empty = [name for name, values in values_by_name.items() if not values]
    if empty:
        raise ValueError(f"parameter values must not be empty: {empty}")

    rows = []
    for index, combination in enumerate(
        itertools.product(*(values_by_name[name] for name in names)),
        start=1,
    ):
        parameters = dict(zip(names, combination))
        rows.append(
            {
                PARAMETER_GRID_ID_COLUMN: f"{parameter_set_prefix}_{index:03d}",
                PARAMETER_GRID_VALUE_COLUMN: _json_safe_mapping(parameters),
                **parameters,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[PARAMETER_GRID_ID_COLUMN, PARAMETER_GRID_VALUE_COLUMN, *names],
    )


def evaluate_parameter_grid(
    parameter_grid: pd.DataFrame,
    evaluator: Callable[[dict[str, Any]], Mapping[str, Any] | pd.Series],
    *,
    metric_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Evaluate every parameter set with a caller-supplied research evaluator."""
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    _require_columns(parameter_grid, [PARAMETER_GRID_ID_COLUMN, PARAMETER_GRID_VALUE_COLUMN])
    metrics = _normalize_columns(metric_columns, "metric_columns") if metric_columns else None

    rows = []
    for grid_row in parameter_grid.to_dict("records"):
        parameters = _coerce_parameter_mapping(grid_row[PARAMETER_GRID_VALUE_COLUMN])
        result = evaluator(dict(parameters))
        if isinstance(result, pd.Series):
            result = result.to_dict()
        if not isinstance(result, Mapping):
            raise TypeError("evaluator must return a mapping or pandas Series")
        result_record = dict(result)
        if metrics is not None:
            missing = [metric for metric in metrics if metric not in result_record]
            if missing:
                raise ValueError(f"evaluator result missing metric columns: {missing}")
            result_record = {metric: result_record[metric] for metric in metrics}
        rows.append({**grid_row, **result_record})
    return pd.DataFrame(rows).reset_index(drop=True)


def summarize_parameter_sensitivity(
    sensitivity_results: pd.DataFrame,
    metric_columns: Iterable[str],
    *,
    group_columns: Iterable[str] | None = None,
    low_sensitivity_relative_range: float = 0.1,
    high_sensitivity_relative_range: float = 0.5,
) -> pd.DataFrame:
    """Summarize metric variation across evaluated parameter sets."""
    metrics = _normalize_columns(metric_columns, "metric_columns")
    groups = _normalize_columns(group_columns, "group_columns") if group_columns else []
    _require_columns(sensitivity_results, [*groups, *metrics])
    _validate_non_negative_number(
        low_sensitivity_relative_range,
        "low_sensitivity_relative_range",
    )
    _validate_non_negative_number(
        high_sensitivity_relative_range,
        "high_sensitivity_relative_range",
    )
    if high_sensitivity_relative_range < low_sensitivity_relative_range:
        raise ValueError(
            "high_sensitivity_relative_range must be greater than or equal to "
            "low_sensitivity_relative_range"
        )

    rows = []
    grouped = (
        sensitivity_results.groupby(groups, dropna=False, sort=True)
        if groups
        else [((), sensitivity_results)]
    )
    for keys, group in grouped:
        key_values = keys if isinstance(keys, tuple) else (keys,)
        group_record = dict(zip(groups, key_values))
        for metric in metrics:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            rows.append(
                {
                    **group_record,
                    **_summarize_metric_values(
                        metric,
                        values,
                        parameter_set_count=len(group),
                        low_sensitivity_relative_range=low_sensitivity_relative_range,
                        high_sensitivity_relative_range=high_sensitivity_relative_range,
                    ),
                }
            )
    columns = [*groups, *PARAMETER_SENSITIVITY_SUMMARY_COLUMNS]
    return pd.DataFrame(rows, columns=columns)


def compare_parameter_sensitivity_to_reference(
    sensitivity_results: pd.DataFrame,
    reference_parameter_set_id: str,
    metric_columns: Iterable[str],
) -> pd.DataFrame:
    """Add differences from a designated reference parameter set."""
    if not isinstance(reference_parameter_set_id, str) or not reference_parameter_set_id:
        raise ValueError("reference_parameter_set_id must be a non-empty string")
    metrics = _normalize_columns(metric_columns, "metric_columns")
    _require_columns(sensitivity_results, [PARAMETER_GRID_ID_COLUMN, *metrics])
    reference_rows = sensitivity_results.loc[
        sensitivity_results[PARAMETER_GRID_ID_COLUMN].eq(reference_parameter_set_id)
    ]
    if len(reference_rows) != 1:
        raise ValueError("reference_parameter_set_id must match exactly one row")

    compared = sensitivity_results.copy()
    reference = reference_rows.iloc[0]
    for metric in metrics:
        compared[f"{metric}_minus_reference"] = (
            pd.to_numeric(compared[metric], errors="coerce")
            - pd.to_numeric(pd.Series([reference[metric]]), errors="coerce").iloc[0]
        )
    compared["reference_parameter_set_id"] = reference_parameter_set_id
    compared["comparison_caveat"] = "reference_comparison_is_descriptive_only"
    return compared


def _summarize_metric_values(
    metric: str,
    values: pd.Series,
    *,
    parameter_set_count: int,
    low_sensitivity_relative_range: float,
    high_sensitivity_relative_range: float,
) -> dict[str, Any]:
    non_missing_count = int(values.count())
    caveats = ["parameter_sensitivity_is_descriptive_only"]
    if non_missing_count == 0:
        caveats.append("no_numeric_metric_values")
        return {
            "metric_column": metric,
            "parameter_set_count": parameter_set_count,
            "non_missing_count": non_missing_count,
            "metric_min": np.nan,
            "metric_max": np.nan,
            "metric_range": np.nan,
            "metric_mean": np.nan,
            "metric_std": np.nan,
            "relative_range": np.nan,
            "sensitivity_flag": "insufficient_data",
            "caveats": caveats,
        }

    metric_min = float(values.min())
    metric_max = float(values.max())
    metric_range = metric_max - metric_min
    metric_mean = float(values.mean())
    metric_std = np.nan if non_missing_count < 2 else float(values.std(ddof=1))
    denominator = max(abs(metric_mean), 1e-12)
    relative_range = float(abs(metric_range) / denominator)
    if relative_range <= low_sensitivity_relative_range:
        sensitivity_flag = "low_variation"
    elif relative_range >= high_sensitivity_relative_range:
        sensitivity_flag = "high_variation"
    else:
        sensitivity_flag = "moderate_variation"
    return {
        "metric_column": metric,
        "parameter_set_count": parameter_set_count,
        "non_missing_count": non_missing_count,
        "metric_min": metric_min,
        "metric_max": metric_max,
        "metric_range": metric_range,
        "metric_mean": metric_mean,
        "metric_std": metric_std,
        "relative_range": relative_range,
        "sensitivity_flag": sensitivity_flag,
        "caveats": caveats,
    }


def _coerce_parameter_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("parameter grid parameters column must contain mappings")
    return dict(value)


def _validate_non_negative_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative number")


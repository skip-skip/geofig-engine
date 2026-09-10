"""EQuIS format conversion utilities (Phase 17 — io subpackage).

Converts between the EQuIS "flat" long format (one row per parameter result
per sample), a wide per-sample frame, and the EQuIS cross-tab Excel layout.

Contracts are documented and deterministic: pure-pandas, no new required
dependencies, and input frames are never mutated (conversions read only).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Unit-suffix parsing for cross-tab column names
# ---------------------------------------------------------------------------

#: Unit alternatives recognised in cross-tab column suffixes (longest first so
#: ``mg_kg`` beats ``kg``, ``mg/L`` beats ``mg``, ...).
UNIT_ALTERNATION = (
    r"µg/L|ug/L|ng/L|mg/L|g/L|meq/L|mg_kg|mg/kg|ppb|ppm|mg|kg|g|%"
)

#: ``"NO3_mg/L"`` — underscore-separated unit suffix.
UNIT_SUFFIX_RE = re.compile(rf"^(?P<param>.+?)_(?P<unit>{UNIT_ALTERNATION})$")

#: ``"Ca (mg/L)"`` — parenthesized unit suffix.
UNIT_PAREN_RE = re.compile(rf"^(?P<param>.+?)\s*\((?P<unit>{UNIT_ALTERNATION})\)$")


def _coerce_sample_keys(sample_keys: Sequence[str] | str) -> tuple[str, ... | None]:
    """Normalize ``sample_keys`` to a tuple of strings."""
    if isinstance(sample_keys, str):
        sample_keys = (sample_keys,)
    return tuple(sample_keys)


def _check_columns(frame: pd.DataFrame, required: Sequence[str], what: str) -> None:
    """Raise ``ValueError`` listing any missing required columns."""
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"{what} is missing required columns: {sorted(set(missing))}")


def equisflat_to_sample_df(
    flat: pd.DataFrame,
    sample_keys: Sequence[str] | str = ("Location",),
    parameter_col: str = "Parameter",
    value_col: str = "Result",
    extra_cols: Sequence[str] | str = (),
    drop_na: bool = True,
) -> pd.DataFrame:
    """Pivot a long EQuIS flat frame to a wide per-sample frame.

    Args:
        flat: Long-form frame with one row per parameter result per sample.
        sample_keys: Column(s) identifying each sample. The wide frame keeps
            these as its leading columns.
        parameter_col: Column naming the parameter/analyte.
        value_col: Column holding the numeric result.
        extra_cols: Additional sample-level columns to carry into the wide
            frame. Each must be constant per sample, else ``ValueError``.
        drop_na: Drop rows whose ``value_col`` is NaN before pivoting.

    Returns:
        Wide frame: one row per sample, one column per parameter
        (first-appearance order), cells = results. Columns outside
        ``sample_keys`` / ``parameter_col`` / ``value_col`` / ``extra_cols``
        are dropped.

    Raises:
        ValueError: A ``(sample, parameter)`` pair appears more than once, an
            ``extra_cols`` value varies within a sample, or a required column
            is missing. Messages are informative.
    """
    if isinstance(extra_cols, str):
        extra_cols = (extra_cols,)
    sample_keys_t = _coerce_sample_keys(sample_keys)
    required = [*sample_keys_t, parameter_col, value_col, *extra_cols]
    _check_columns(flat, required, "flat")

    work = flat
    if drop_na:
        work = work[work[value_col].notna()]

    dup_mask = work.duplicated(subset=[*sample_keys_t, parameter_col])
    if dup_mask.any():
        example = work.loc[dup_mask, [*sample_keys_t, parameter_col]].iloc[0]
        where = ", ".join(f"{k}={example[k]!r}" for k in sample_keys_t)
        raise ValueError(
            f"duplicate result for parameter {example[parameter_col]!r} in sample "
            f"({where}); aggregate or deduplicate before pivoting"
        )

    pivoted = work.pivot(
        index=list(sample_keys_t),
        columns=parameter_col,
        values=value_col,
    ).reset_index()

    first_appearance = list(dict.fromkeys(work[parameter_col].tolist()))
    pivoted = pivoted.reindex(columns=[*sample_keys_t, *first_appearance])

    if extra_cols:
        varying = work.groupby(list(sample_keys_t), sort=False)[list(extra_cols)].nunique()
        bad = varying[(varying > 1).any(axis=1)]
        if not bad.empty:
            example = bad.index[0]
            bad_cols = [c for c in extra_cols if varying.loc[example, c] > 1]
            where = ", ".join(f"{k}={example[i]!r}" for i, k in enumerate(sample_keys_t))
            raise ValueError(
                f"extra_cols not constant per sample: {bad_cols} for sample ({where})"
            )
        extras = work.groupby(list(sample_keys_t), sort=False)[list(extra_cols)].first()
        extras = extras.reset_index()
        pivoted = pivoted.merge(extras, on=list(sample_keys_t), how="left")

    return pivoted


def sample_df_to_equisflat(
    sample_df: pd.DataFrame,
    sample_keys: Sequence[str] | str = ("Location",),
    parameter_col: str = "Parameter",
    value_col: str = "Result",
    extra_cols: Sequence[str] | str = (),
    drop_na: bool = True,
) -> pd.DataFrame:
    """Melt a wide per-sample frame back to the long EQuIS flat format.

    Inverse of :func:`equisflat_to_sample_df`: wide parameter columns become
    ``parameter_col`` rows, one row per ``(sample, parameter)``.

    Args:
        sample_df: Wide frame as produced by ``equisflat_to_sample_df``.
        sample_keys: Sample-identifying columns (used as id vars).
        parameter_col: Name for the melted parameter column.
        value_col: Name for the melted result column.
        extra_cols: Additional id vars carried per sample.
        drop_na: Drop melted rows whose value is NaN.

    Returns:
        Long flat frame. ``sample_keys`` / ``extra_cols`` come first, then
        ``parameter_col`` and ``value_col``.
    """
    if isinstance(extra_cols, str):
        extra_cols = (extra_cols,)
    sample_keys_t = _coerce_sample_keys(sample_keys)
    _check_columns(sample_df, [*sample_keys_t, *extra_cols], "sample_df")

    id_vars = [*sample_keys_t, *extra_cols]
    param_cols = [c for c in sample_df.columns if c not in id_vars]
    melted = sample_df.melt(
        id_vars=id_vars,
        value_vars=param_cols,
        var_name=parameter_col,
        value_name=value_col,
    )
    if drop_na:
        melted = melted[melted[value_col].notna()]
    return melted


def equis_crosstab_to_flat(
    path_or_df: str | Path | pd.DataFrame,
    sample_keys: Sequence[str] | str = ("Location",),
    parameter_col: str = "Parameter",
    value_col: str = "Result",
    unit_col: str = "Result_Unit",
) -> pd.DataFrame:
    """Parse an EQuIS cross-tab (wide, rows = samples) into the long flat form.

    Args:
        path_or_df: A ``pd.DataFrame`` already read from a cross-tab, or an
            Excel file path / ``Path`` (read via ``pd.read_excel``; the engine
            auto-selects — ``openpyxl`` is only needed by callers/tests that
            exercise Excel files).
        sample_keys: Sample-identifying columns, kept on every output row.
        parameter_col / value_col / unit_col: Output column names for the
            parameter, the numeric result, and the parsed unit.

    Column-name parsing is documented by ``UNIT_SUFFIX_RE``
    (``"NO3_mg/L"``) and ``UNIT_PAREN_RE`` (``"Ca (mg/L)"``). Columns with a
    matching unit suffix become parameter rows; a matching column's cells are
    coerced with ``pd.to_numeric(errors="coerce")`` (non-numeric → NaN).
    Columns with neither a unit suffix nor a sample key are treated as row
    metadata and broadcast onto every output row. Non-string column names
    are always treated as metadata.

    Raises:
        ValueError: A sample-key column is missing, or no unit-suffixed
            analyte column was found.
    """
    sample_keys_t = _coerce_sample_keys(sample_keys)
    if isinstance(path_or_df, (str, Path)):
        frame = pd.read_excel(path_or_df)
    else:
        frame = path_or_df
    _check_columns(frame, sample_keys_t, "cross-tab frame")

    parts: list[pd.DataFrame] = []
    metadata_cols: list[Any] = []
    for col in frame.columns:
        if col in sample_keys_t:
            continue
        if isinstance(col, str):
            match = UNIT_SUFFIX_RE.match(col) or UNIT_PAREN_RE.match(col)
            if match:
                param = match.group("param")
                unit = match.group("unit")
                s = pd.to_numeric(frame[col], errors="coerce").to_frame(value_col)
                s[parameter_col] = param
                s[unit_col] = unit
                for key in reversed(sample_keys_t):
                    s.insert(0, key, frame[key].to_numpy())
                parts.append(s)
                continue
        metadata_cols.append(col)

    if not parts:
        raise ValueError(
            "no analyte columns with unit suffixes found in the cross-tab frame "
            "(expected names like 'NO3_mg/L' or 'Ca (mg/L)')"
        )

    result = pd.concat(parts, ignore_index=False)
    if metadata_cols:
        n_parts = len(parts)
        for col in metadata_cols:
            # Positional broadcast: every part has one row per original row,
            # in original row order.
            result[col] = np.tile(frame[col].to_numpy(), n_parts)

    out_cols = [
        *sample_keys_t,
        parameter_col,
        value_col,
        unit_col,
        *metadata_cols,
    ]
    return result[out_cols]
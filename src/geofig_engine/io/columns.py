"""Column-level data utilities (Phase 17 — io subpackage).

Parses Ecesis-style column names with embedded units into a wide sample
frame with a two-level ``(analyte, unit)`` column index, and bins numeric or
datetime columns into deterministic categoricals.

Contracts are documented and deterministic: pure-pandas, no new required
dependencies, and input frames/series are never mutated.
"""

from __future__ import annotations

import re
from typing import Any, Optional, Sequence

import pandas as pd

# ---------------------------------------------------------------------------
# Ecesis column-name parsing
# ---------------------------------------------------------------------------

#: Unit alternatives recognised in Ecesis column suffixes (mirrors
#: ``geofig_engine.io.equis.UNIT_ALTERNATION``; longest first so ``mg_kg``
#: beats ``kg``, ``mg/L`` beats ``mg``, ...).
DEFAULT_UNIT_ALTERNATION = (
    r"µg/L|ug/L|ng/L|mg/L|g/L|meq/L|mg_kg|mg/kg|ppb|ppm|mg|kg|g|%"
)

#: ``"NO3_mg/L"`` — underscore-separated unit suffix.
UNIT_SUFFIX_RE = re.compile(
    rf"^(?P<param>.+?)_(?P<unit>{DEFAULT_UNIT_ALTERNATION})$"
)

#: ``"Ca (mg/L)"`` — parenthesized unit suffix.
UNIT_PAREN_RE = re.compile(
    rf"^(?P<param>.+?)\s*\((?P<unit>{DEFAULT_UNIT_ALTERNATION})\)$"
)


def _resolve_pattern(unit_pattern: Optional[Any]) -> Any:
    """Normalize ``unit_pattern`` to a compiled regex (or the default pair).

    A ``str`` pattern is compiled. A compiled regex is used as-is and must
    expose named groups ``param`` and ``unit`` for any match.
    """
    if unit_pattern is None:
        return None
    if isinstance(unit_pattern, str):
        return re.compile(unit_pattern)
    if not hasattr(unit_pattern, "match"):
        raise TypeError(
            "unit_pattern must be a compiled regex or a pattern string; "
            f"got {type(unit_pattern).__name__}"
        )
    return unit_pattern


def _match_unit(column: str, pattern: Any) -> Optional[re.Match[str]]:
    """Match an Ecesis column name, returning ``(param, unit)`` or ``None``."""
    if pattern is None:
        return UNIT_SUFFIX_RE.match(column) or UNIT_PAREN_RE.match(column)
    match = pattern.match(column)
    if match is None:
        return None
    missing = [g for g in ("param", "unit") if g not in match.re.groupindex]
    if missing:
        raise ValueError(
            "unit_pattern must define named groups 'param' and 'unit'; "
            f"missing: {missing}"
        )
    return match


def ecesis_to_sample_df(
    frame: pd.DataFrame,
    unit_pattern: Optional[Any] = None,
    drop_na: bool = True,
) -> pd.DataFrame:
    """Parse Ecesis-style column names into a wide frame with unit columns.

    Args:
        frame: Wide frame whose column names may embed units in Ecesis form,
            either ``"NO3_mg/L"`` (underscore-separated) or ``"Ca (mg/L)"``
            (parenthesized). Plain columns (``"Sample_ID"``, ``"pH"``) are
            kept as-is with an empty unit level.
        unit_pattern: Optional compiled regex (or pattern string) overriding
            the default unit suffix set. A matching regex must define named
            groups ``param`` and ``unit``; only that regex is consulted.
        drop_na: Drop rows where *every* parsed numeric cell is NaN. Rows
            with at least one parsed value (or only plain columns) are kept.

    Returns:
        A new frame with the same index and column order, a two-level
        ``(analyte, unit)`` column index, parsed columns coerced with
        ``pd.to_numeric(errors="coerce")``, and plain columns carried
        verbatim (unit level ``""``). The input frame is never mutated.

    Raises:
        ValueError: Two input columns parse to the same ``(analyte, unit)``
            key (informative message), or ``unit_pattern`` matches without
            the ``param``/``unit`` groups.
    """
    pattern = _resolve_pattern(unit_pattern)

    parsed: list[tuple[Any, str, str]] = []   # (source col, param, unit)
    plain: list[Any] = []
    for col in frame.columns:
        if isinstance(col, str):
            match = _match_unit(col, pattern)
            if match is not None:
                parsed.append((col, match.group("param"), match.group("unit")))
                continue
        plain.append(col)

    keys = [(p, u) for _, p, u in parsed] + [(c, "") for c in plain]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise ValueError(
            "duplicate (analyte, unit) column keys after parsing: "
            f"{duplicates}; rename or deduplicate the input columns"
        )

    out: dict[tuple[Any, str], Any] = {}
    for col, param, unit in parsed:
        out[(param, unit)] = pd.to_numeric(frame[col], errors="coerce")
    for col in plain:
        out[(col, "")] = frame[col]

    result = pd.DataFrame(out, index=frame.index)
    result.columns = pd.MultiIndex.from_tuples(result.columns)

    if parsed and drop_na:
        keep = result[[(p, u) for _, p, u in parsed]].notna().any(axis=1)
        result = result[keep.values]

    return result


# ---------------------------------------------------------------------------
# Categorical binning
# ---------------------------------------------------------------------------


def create_bins(
    series: pd.Series,
    bins: Any,
    strategy: str = "range",
    labels: Optional[Sequence[Any]] = None,
    include_lowest: bool = True,
    right: bool = True,
) -> pd.Series:
    """Bin a numeric or datetime series into a categorical series.

    Args:
        series: Numeric or datetime series to bin.
        bins: For ``strategy="range"`` — an int (that many equal-width bins
            across the observed min–max) or an explicit sorted sequence of
            edges. For ``strategy="quantile"`` — the number of equal-frequency
            bins.
        strategy: ``"range"`` (equal-width via :func:`pandas.cut`) or
            ``"quantile"`` (equal-frequency via :func:`pandas.qcut`).
        labels: Optional labels for the bins (as accepted by cut/qcut).
        include_lowest: Whether the first interval is closed on the left
            (range strategy only).
        right: Whether intervals are closed on the right (range strategy
            only).

    Returns:
        A categorical series with the same index and name as ``series``.
        NaN input values map to NaN categories. Deterministic — identical
        input produces identical category dtype and ordering.

    Raises:
        ValueError: Unknown ``strategy``, or an invalid bin specification
            surfaced by cut/qcut (e.g. wrong label count, non-unique
            quantile edges).
    """
    if strategy == "range":
        out = pd.cut(
            series,
            bins=bins,
            labels=labels,
            include_lowest=include_lowest,
            right=right,
        )
    elif strategy == "quantile":
        out = pd.qcut(series, q=bins, labels=labels, duplicates="drop")
    else:
        raise ValueError(
            f"unknown strategy {strategy!r}; expected 'range' or 'quantile'"
        )
    return pd.Series(out, index=series.index, name=series.name)
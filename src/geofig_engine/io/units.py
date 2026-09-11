"""SI-prefix unit normalization for EQuIS-style flat frames.

Utilities for normalizing SI prefixes (nano → kilo) *within each analyte
group* so that all results for one parameter share a single unit string.
Pure pandas + stdlib; no new required dependencies.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

__all__ = ["equisflat_normalize_units", "SI_PREFIXES"]

#: SI prefix → power-of-ten exponent. An unprefixed unit string (bare base)
#: has exponent 0. Both the micro sign (U+00B5) and the Greek mu (U+03BC)
#: are accepted for 1e-6.
SI_PREFIXES: dict[str, int] = {
    "n": -9,
    "u": -6,
    "µ": -6,
    "μ": -6,
    "m": -3,
    "c": -2,
    "d": -1,
    "k": 3,
    "M": 6,
    "G": 9,
}

#: Unit bases that may carry an SI prefix. A unit in this set written without
#: a prefix is treated as the unscaled base unit (exponent 0). Examples:
#: ``g``, ``L``, ``mol/L``, ``g/kg`` (also spelled ``g_kg``), ``eq/L``.
ALLOWED_BASES: frozenset[str] = frozenset(
    {
        "g",
        "L",
        "mol",
        "eq",
        "N",
        "g/L",
        "g/kg",
        "g_kg",
        "mol/L",
        "mol/kg",
        "eq/L",
        "cc",
        "cm3",
        "m3",
    }
)


def _parse_unit(unit: object) -> Optional[int]:
    """Return the SI exponent of ``unit``, or ``None`` if unrecognized.

    A recognized unit is either a bare `ALLOWED_BASES` base (exponent 0) or a
    single `SI_PREFIXES` prefix followed by an allowed base. Non-string or
    empty values are never recognized.
    """
    if not isinstance(unit, str) or not unit:
        return None
    first = unit[0]
    if first in SI_PREFIXES:
        base = unit[1:]
        if base in ALLOWED_BASES:
            return SI_PREFIXES[first]
    if unit in ALLOWED_BASES:
        return 0
    return None


def _check_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(
            f"missing required columns: {', '.join(missing)}; "
            f"got {list(frame.columns)}"
        )


def equisflat_normalize_units(
    flat: pd.DataFrame,
    parameter_col: str = "Parameter",
    value_col: str = "Result",
    unit_col: str = "Result_Unit",
    inplace: bool = False,
) -> pd.DataFrame:
    """Normalize SI prefixes within each parameter group of ``flat``.

    All results for one parameter end up sharing a single unit string: the
    most frequent *recognized* unit in the group (ties → lexicographically
    smallest unit string), with every value rescaled by

        value * 10 ** (prefix_exponent(row_unit) - prefix_exponent(canonical))

    Recognized units are a bare `ALLOWED_BASES` base (exponent 0) or a single
    `SI_PREFIXES` prefix followed by an allowed base. Unrecognized unit
    strings pass through untouched (value and unit unchanged), as do groups
    without any recognized unit and rows whose value is not numeric.

    Returns a new frame by default; ``inplace=True`` mutates and returns the
    input frame.
    """
    _check_columns(flat, (parameter_col, value_col, unit_col))
    frame = flat if inplace else flat.copy()

    exponents = frame[unit_col].map(_parse_unit)
    recognized = exponents.notna()

    # Canonical unit per parameter group: the most frequent recognized unit
    # string; ties → lexicographically smallest. Groups with no recognized
    # unit are left untouched.
    canonical_units: dict[object, str] = {}
    for param, param_idx in frame.groupby(parameter_col, sort=False).groups.items():
        param_idx = pd.Index(param_idx)
        rec_idx = param_idx[recognized.loc[param_idx].to_numpy()]
        if len(rec_idx) == 0:
            continue
        counts = frame.loc[rec_idx, unit_col].value_counts()
        max_count = counts.max()
        canonical_units[param] = sorted(
            unit for unit, n in counts.items() if n == max_count
        )[0]

    if not canonical_units:
        return frame

    canonical_exponent = {p: _parse_unit(u) for p, u in canonical_units.items()}
    group_canonical = frame[parameter_col].map(canonical_units)
    group_exponent = frame[parameter_col].map(canonical_exponent)
    scaleable = recognized & group_exponent.notna()

    if scaleable.any():
        numeric = pd.to_numeric(frame[value_col], errors="coerce")
        factor = 10.0 ** (exponents - group_exponent)
        scaled = numeric * factor
        if pd.api.types.is_float_dtype(frame[value_col]):
            values = numeric.copy()
        else:
            values = frame[value_col].astype(object)
        values[scaleable] = scaled[scaleable]

        frame[value_col] = values
        frame[unit_col] = frame[unit_col].where(~scaleable, group_canonical)

    return frame
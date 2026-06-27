"""Position adjustment utilities for MatplotlibRenderer."""

from __future__ import annotations


def dodge_positions(
    group_center: float,
    series_idx: int,
    n_series: int,
    total_width: float,
) -> tuple[float, float]:
    """Compute (x_position, adjusted_width) for a series within a dodge group.

    Parameters
    ----------
    group_center : float
        Center position of the group (e.g. 1, 2, 3...).
    series_idx : int
        Index of the current series within the group (0-based).
    n_series : int
        Total number of series in the dodge group.
    total_width : float
        Total width allocated for the full group.

    Returns
    -------
    position : float
        The x-position for this series' mark.
    width : float
        The rendered width of this series' mark (85% of series slot).
    """
    series_width = total_width / n_series
    offset = (series_idx - (n_series - 1) / 2) * series_width
    return group_center + offset, series_width * 0.85

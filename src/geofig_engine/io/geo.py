import numpy as np
import pandas as pd


def haversine(
    lon1: float | pd.Series,
    lat1: float | pd.Series,
    lon2: float | pd.Series,
    lat2: float | pd.Series,
) -> float | pd.Series:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def path_distance(
    lon: pd.Series,
    lat: pd.Series,
    cumulative: bool = True,
) -> pd.Series:
    if len(lon) < 2:
        return pd.Series(0.0, index=lon.index)
    segs = haversine(lon.values[:-1], lat.values[:-1], lon.values[1:], lat.values[1:])
    if cumulative:
        dists = np.zeros(len(lon))
        dists[1:] = np.cumsum(segs)
        return pd.Series(dists, index=lon.index)
    return pd.Series(np.concatenate([[0], segs]), index=lon.index)

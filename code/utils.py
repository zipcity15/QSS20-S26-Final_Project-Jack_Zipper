"""
utils.py — shared helper functions for the DRC humanitarian aid project.

Import in any notebook with:
    import sys; sys.path.insert(0, '/Users/jackzipper/QSS20/final_project/code')
    from utils import fill_deaths, assign_admin_level
"""

import numpy as np
import geopandas as gpd
from pathlib import Path

# ── Project-wide paths ─────────────────────────────────────────────────────
PROJECT_ROOT = Path('/Users/jackzipper/QSS20/final_project')
DATA_DIR     = PROJECT_ROOT / 'final_project_data'
OUT_DIR      = PROJECT_ROOT / 'output'

# ── Project-wide constants ─────────────────────────────────────────────────
EASTERN_PROVINCES = ['Nord-kivu', 'Sud-kivu', 'Ituri']
SMALL_CONSTANT    = 0.5   # substituted for zero deaths after 6+ consecutive zero months


# ── Shared functions ───────────────────────────────────────────────────────

def fill_deaths(series):
    """Carry-forward last known death count for up to 5 months of zeros;
    fall back to SMALL_CONSTANT after 6+ consecutive zero months or at series start.

    Used in: 07_aid+violence_scatter, 09_choropleth_map.
    """
    s = series.astype(float).values.copy()
    last_nonzero, streak = None, 0
    out = np.empty_like(s)
    for i, v in enumerate(s):
        if v > 0:
            last_nonzero, streak, out[i] = v, 0, v
        else:
            streak += 1
            out[i] = SMALL_CONSTANT if (last_nonzero is None or streak >= 6) else last_nonzero
    return out


def assign_admin_level(gdf_points, boundaries, name_col, max_distance_m=55_000):
    """Point-in-polygon spatial join with a nearest-neighbour fallback.

    Parameters
    ----------
    gdf_points   : GeoDataFrame of aid/conflict points, projected to metres CRS.
    boundaries   : GeoDataFrame of admin polygons, same CRS.
    name_col     : Column in `boundaries` containing the admin name.
    max_distance_m : Maximum distance (m) for the nearest-neighbour fallback.

    Returns
    -------
    Series of admin names (NaN where no polygon within max_distance_m).
    """
    # Exact point-in-polygon
    joined = gpd.sjoin(gdf_points, boundaries[[name_col, 'geometry']],
                       how='left', predicate='within')
    names = joined[name_col].copy()

    # Nearest-neighbour fallback for border/unmatched points
    na_mask = names.isna()
    if na_mask.any():
        gdf_na = gdf_points[na_mask].copy()
        nearest = gpd.sjoin_nearest(
            gdf_na, boundaries[[name_col, 'geometry']],
            how='left', max_distance=max_distance_m
        )
        names.loc[na_mask] = nearest[name_col].values

    return names

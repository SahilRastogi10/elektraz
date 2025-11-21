# src/features/engineer.py
"""Feature engineering for candidate sites."""

import geopandas as gpd
import pandas as pd
import numpy as np
from typing import Optional, Tuple

from src.common.geo import to_crs


def _vectorized_nearest_distance(source_geom: gpd.GeoSeries, target_gdf: gpd.GeoDataFrame) -> np.ndarray:
    """Calculate nearest distance from each source point to target geometries efficiently."""
    if target_gdf is None or len(target_gdf) == 0:
        return np.full(len(source_geom), np.nan)
    
    target_sindex = target_gdf.sindex
    distances = []
    
    for geom in source_geom:
        nearest_idx = list(target_sindex.nearest(geom, 5))
        if nearest_idx:
            min_dist = target_gdf.iloc[nearest_idx].distance(geom).min()
        else:
            min_dist = target_gdf.distance(geom).min() if len(target_gdf) > 0 else np.nan
        distances.append(min_dist)
    
    return np.array(distances)


def _buffer_aggregate(candidates: gpd.GeoDataFrame, data_gdf: gpd.GeoDataFrame, 
                      radius_m: float, agg_col: str, agg_func: str = "sum") -> pd.Series:
    """Aggregate values within buffer radius of each candidate."""
    if data_gdf is None or len(data_gdf) == 0 or agg_col not in data_gdf.columns:
        return pd.Series(0.0, index=candidates.index)
    
    results = []
    data_sindex = data_gdf.sindex
    
    for idx, geom in enumerate(candidates.geometry):
        buffer = geom.buffer(radius_m)
        possible_matches_idx = list(data_sindex.query(buffer, predicate="intersects"))
        
        if possible_matches_idx:
            matches = data_gdf.iloc[possible_matches_idx]
            if agg_func == "sum":
                val = matches[agg_col].sum()
            elif agg_func == "mean":
                val = matches[agg_col].mean()
            elif agg_func == "max":
                val = matches[agg_col].max()
            elif agg_func == "count":
                val = len(matches)
            else:
                val = matches[agg_col].sum()
        else:
            val = 0.0
        results.append(val)
    
    return pd.Series(results, index=candidates.index)


def engineer_features(
    candidates: gpd.GeoDataFrame,
    afdc: gpd.GeoDataFrame,
    aadt: gpd.GeoDataFrame,
    ejscreen_df: Optional[pd.DataFrame] = None,
    nfhl: Optional[gpd.GeoDataFrame] = None,
    acs_zcta: Optional[pd.DataFrame] = None,
    zcta_polygons: Optional[gpd.GeoDataFrame] = None,
    substations: Optional[gpd.GeoDataFrame] = None,
    transmission: Optional[gpd.GeoDataFrame] = None,
    crime_pts: Optional[gpd.GeoDataFrame] = None,
    radii_m: Tuple[int, ...] = (500, 1500, 5000),
    crs_proj: int = 26912
) -> gpd.GeoDataFrame:
    """Build model features per candidate site."""
    
    C = to_crs(candidates.copy(), crs_proj)
    if "cand_id" not in C.columns:
        C["cand_id"] = np.arange(len(C))
    
    # Convert layers
    AF = to_crs(afdc, crs_proj) if afdc is not None and len(afdc) > 0 else None
    AA = to_crs(aadt, crs_proj) if aadt is not None and len(aadt) > 0 else None
    NF = to_crs(nfhl, crs_proj) if nfhl is not None and len(nfhl) > 0 else None
    
    # Filter for DCFC
    AF_dcfc = AF
    if AF is not None and "dcfc_ports" in AF.columns:
        AF_dcfc = AF[AF["dcfc_ports"].fillna(0) > 0].copy()
    
    # Distance features
    C["dist_m_nearest_dcfc"] = _vectorized_nearest_distance(C.geometry, AF_dcfc)
    C["dist_m_nearest_station"] = _vectorized_nearest_distance(C.geometry, AF)
    
    # AADT density
    aadt_col = "AADT" if AA is not None and "AADT" in AA.columns else None
    for r in radii_m:
        col_name = f"aadt_sum_{r}m"
        if aadt_col and AA is not None:
            C[col_name] = _buffer_aggregate(C, AA, r, aadt_col, "sum")
        else:
            C[col_name] = 0.0
    
    # Floodplain
    if NF is not None and len(NF) > 0:
        nfhl_union = NF.unary_union
        C["in_floodplain"] = C.geometry.apply(
            lambda g: nfhl_union.intersects(g.buffer(30)) if nfhl_union else False
        )
    else:
        C["in_floodplain"] = False
    
    # Defaults for missing data
    C["equity_score"] = 0.5
    C["median_income"] = 50000
    C["crime_ct_500m"] = 0
    
    # Derived scores
    dcfc_dist = C["dist_m_nearest_dcfc"].fillna(10000)
    C["grid_conflict_score"] = (dcfc_dist / 10000).clip(0, 2)
    C["safety_score"] = C["in_floodplain"].astype(int) * 0.5
    
    max_aadt = C["aadt_sum_1500m"].max() if C["aadt_sum_1500m"].max() > 0 else 1
    C["accessibility_score"] = (C["aadt_sum_1500m"] / max_aadt).clip(0, 1)
    
    C["x"] = C.geometry.x
    C["y"] = C.geometry.y
    
    return C


def compute_equity_bonus(candidates: gpd.GeoDataFrame, 
                        income_col: str = "median_income") -> np.ndarray:
    """Compute equity bonus score favoring underserved areas."""
    scores = np.zeros(len(candidates))
    if income_col in candidates.columns:
        income = candidates[income_col].fillna(50000)
        income_score = 1 - (income / income.max()).clip(0, 1)
        scores += income_score
    return scores

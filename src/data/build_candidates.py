import geopandas as gpd, pandas as pd, numpy as np
from shapely.ops import nearest_points
from shapely.geometry import Point
from src.common.geo import to_crs

def candidates_from_sources(adot_roads: gpd.GeoDataFrame,
                            aadt: gpd.GeoDataFrame,
                            pr_sites: gpd.GeoDataFrame,
                            rest_areas: gpd.GeoDataFrame,
                            afc_corridors: gpd.GeoDataFrame,
                            crs_proj=26912) -> gpd.GeoDataFrame:
    """
    Build candidate site points prioritizing:
    - AFC 1-mi buffers (interchange vicinity)
    - ADOT rest areas
    - Park & Ride lots
    - High-AADT nodes (top quantiles)
    """
    roads = to_crs(adot_roads, crs_proj)
    aadtp = to_crs(aadt, crs_proj)
    prp = to_crs(pr_sites, crs_proj)
    rap = to_crs(rest_areas, crs_proj)
    afcp = to_crs(afc_corridors, crs_proj)

    # 1) Rest areas & P&R as candidates
    c_pr = prp.copy(); c_pr["src"]="parkride"
    c_ra = rap.copy(); c_ra["src"]="restarea"

    # 2) High AADT midpoints as candidates
    q = aadtp["AADT"].quantile(0.90)
    aadt_hi = aadtp[aadtp["AADT"]>=q].copy()
    aadt_pts = aadt_hi.geometry.interpolate(0.5, normalized=True)
    c_aadt = gpd.GeoDataFrame(
        {"src": ["aadt_hi"] * len(aadt_pts)},
        geometry=aadt_pts.values,
        crs=aadtp.crs
    )

    # 3) Snap to AFC buffer (within ~1 mi)
    afc_buf = afcp.buffer(1600)  # ~1 mile in meters
    union = gpd.GeoSeries(afc_buf.unary_union, crs=afcp.crs)
    c_all = pd.concat([c_pr, c_ra, c_aadt], ignore_index=True)
    c_all["in_afc"] = c_all.geometry.within(union.iloc[0])

    # Deduplicate by 800 m
    c_all["x"] = c_all.geometry.x; c_all["y"] = c_all.geometry.y
    # simple grid-based de-dupe
    c_all["gx"] = (c_all["x"]/800).round().astype(int)
    c_all["gy"] = (c_all["y"]/800).round().astype(int)
    cand = c_all.drop_duplicates(subset=["gx","gy"]).drop(columns=["gx","gy","x","y"])
    cand["cand_id"] = np.arange(len(cand))
    return cand

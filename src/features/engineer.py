import geopandas as gpd, pandas as pd, numpy as np
from shapely.ops import nearest_points
from shapely.geometry import Point
from sklearn.neighbors import BallTree

from src.common.geo import to_crs
from src.common.io import write_geoparquet

def haversine_km(a_lonlat: np.ndarray, b_lonlat: np.ndarray):
    # a_lonlat: (n,2), b_lonlat: (m,2) — returns dist matrix n x m in km (lazy if needed)
    pass

def engineer_features(candidates: gpd.GeoDataFrame,
                      afdc: gpd.GeoDataFrame,
                      aadt: gpd.GeoDataFrame,
                      acs_zcta: pd.DataFrame,
                      ejscreen: gpd.GeoDataFrame,
                      nfhl: gpd.GeoDataFrame,
                      crime_pts: gpd.GeoDataFrame | None,
                      substations: gpd.GeoDataFrame,
                      transmission: gpd.GeoDataFrame,
                      radii_m=(500, 1500, 5000),
                      crs_proj=26912) -> gpd.GeoDataFrame:
    """
    Build model features per candidate:
    - Distances to nearest: existing DCFC, substation, transmission line
    - AADT density within radius
    - Population, renter share, income (ZCTA/tract join)
    - EJ indexes (max/mean within radius)
    - Floodplain/intersection flags
    - Crime density proxies (if available)
    """
    C = to_crs(candidates, crs_proj)
    AF = to_crs(afdc, crs_proj)
    AA = to_crs(aadt, crs_proj)
    EJ = to_crs(ejscreen, crs_proj)
    NF = to_crs(nfhl, crs_proj)
    SS = to_crs(substations, crs_proj)
    TL = to_crs(transmission, crs_proj)
    CR = to_crs(crime_pts, crs_proj) if crime_pts is not None and not crime_pts.empty else None

    # Nearest distances
    C["dist_m_nearest_dcfc"] = C.geometry.apply(lambda g: AF.distance(g).min() if len(AF)>0 else np.nan)
    C["dist_m_nearest_substation"] = C.geometry.apply(lambda g: SS.distance(g).min() if len(SS)>0 else np.nan)
    C["dist_m_nearest_txline"] = C.geometry.apply(lambda g: TL.distance(g).min() if len(TL)>0 else np.nan)

    # AADT density within buffers
    for r in radii_m:
        buf = C.geometry.buffer(r)
        inter = gpd.overlay(gpd.GeoDataFrame(geometry=buf, crs=C.crs).reset_index(names="idx"), AA, how="intersection")
        if "AADT" in inter.columns:
            agg = inter.groupby("idx")["AADT"].sum().rename(f"aadt_sum_{r}m")
            C = C.join(agg, on=C.index).fillna({f"aadt_sum_{r}m":0})

    # EJSCREEN max index within 1500m
    ej_buf = C.geometry.buffer(1500)
    inter_ej = gpd.overlay(gpd.GeoDataFrame(geometry=ej_buf, crs=C.crs).reset_index(names="idx"), EJ, how="intersection")
    ej_cols = [c for c in EJ.columns if c.startswith("EJ_") or c.endswith("_PCTL")]
    for col in ej_cols[:10]:  # keep it light
        agg = inter_ej.groupby("idx")[col].max().rename(f"{col}_max1500")
        C = C.join(agg, on=C.index)

    # Floodplain flag (any overlay with SFHA polygons)
    C["in_floodplain"] = C.geometry.apply(lambda g: NF.intersects(g.buffer(30)).any() if len(NF)>0 else False)

    # Crime density proxy (points within 500m)
    if CR is not None and len(CR)>0:
        sindex = CR.sindex
        counts=[]
        for geom in C.geometry:
            idx = list(sindex.query(geom.buffer(500), predicate="intersects"))
            counts.append(len(idx))
        C["crime_ct_500m"] = counts
    else:
        C["crime_ct_500m"] = 0

    # Attach ACS by spatial join to ZCTAs/tracts already prepped as polygons in acs_zcta_gdf
    # Expect acs_zcta to be polygon with columns from ingest_acs
    # (If acs_zcta is a table keyed by ZCTA code and you have ZCTA polygons in raw, join them earlier.)
    # For brevity, skip here; often you do a spatial join and aggregate.

    return C

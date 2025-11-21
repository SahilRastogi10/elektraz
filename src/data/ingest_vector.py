# src/data/ingest_vector.py
import requests
import geopandas as gpd
from typing import Optional

def _read_arcgis_layer(url: str, where: str = "1=1", out_sr: int = 4326, page: int = 2000) -> gpd.GeoDataFrame:
    """
    Generic ArcGIS FeatureServer reader to GeoJSON (paged).
    Example URL (layer 0): https://maps.azdot.gov/arcgis/rest/services/Traffic/AADT_2024/FeatureServer/0
    """
    feats, offset = [], 0
    while True:
        params = {
            "where": where,
            "outFields": "*",
            "outSR": out_sr,
            "returnGeometry": "true",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page,
        }
        r = requests.get(f"{url}/query", params=params, timeout=120)
        r.raise_for_status()
        js = r.json()
        batch = js.get("features", [])
        if not batch:
            break
        feats.extend(batch)
        offset += page
    return gpd.GeoDataFrame.from_features(feats, crs=f"EPSG:{out_sr}") if feats else gpd.GeoDataFrame(geometry=[], crs=f"EPSG:{out_sr}")

def load_aadt(url: str, where: str = "1=1") -> gpd.GeoDataFrame:
    """
    Load ADOT AADT layer directly from its ArcGIS FeatureServer URL.
    """
    return _read_arcgis_layer(url, where=where, out_sr=4326)

def load_nfhl(url: str, where: str = "1=1") -> gpd.GeoDataFrame:
    """
    Load FEMA NFHL polygons directly from the public MapServer/FeatureServer URL.
    """
    return _read_arcgis_layer(url, where=where, out_sr=4326)

def load_service_area(url: str, where: str = "1=1") -> gpd.GeoDataFrame:
    """
    Generic loader for any ArcGIS FeatureServer layer (e.g., Park & Ride, corridors).
    """
    return _read_arcgis_layer(url, where=where, out_sr=4326)

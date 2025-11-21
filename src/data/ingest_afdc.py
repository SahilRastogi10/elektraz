# src/data/ingest_afdc.py
import os
import json
import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Optional
from src.common.config import AppSettings
from src.common.io import write_geoparquet

AFDC_URL_TMPL = "{base}/api/alt-fuel-stations/v1.json"

def _parse_afdc_json(data: dict) -> gpd.GeoDataFrame:
    stations = data.get("fuel_stations", []) or []
    rows = []
    for s in stations:
        lat, lon = s.get("latitude"), s.get("longitude")
        if lat is None or lon is None:
            continue
        rows.append({
            "station_id": s.get("id"),
            "name": s.get("station_name"),
            "network": s.get("ev_network"),
            # AFDC does not directly provide kW per connector; this is a placeholder count
            "dcfc_ports": s.get("ev_dc_fast_num"),
            "connectors": "|".join(s.get("ev_connector_types") or []),
            "access_days": s.get("access_days_time"),
            "street": s.get("street_address"),
            "city": s.get("city"),
            "county": s.get("county"),
            "zip": s.get("zip"),
            "lon": lon,
            "lat": lat,
            "open_date": s.get("date_opened"),
            "status": s.get("status_code"),
        })
    if not rows:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326"
    )
    return gdf

def fetch_afdc_elec_az(save_json_to: Optional[str] = None) -> gpd.GeoDataFrame:
    """
    Fetch public EV stations for Arizona directly from NREL AFDC API.
    If `save_json_to` is provided, the raw JSON is saved (optional).
    Returns a GeoDataFrame in EPSG:4326.
    """
    env = AppSettings()
    base = os.getenv("AFDC_URL", AFDC_URL_TMPL.format(base=env.NREL_API_BASE))
    url = base if base.endswith(".json") else AFDC_URL_TMPL.format(base=env.NREL_API_BASE)

    params = {
        "api_key": env.NREL_API_KEY or "DEMO_KEY",
        "fuel_type": "ELEC",
        "state": "AZ",
        "access": "public",
        "status": "E",   # use "all" if you want planned/temporarily unavailable too
        "limit": 20000,
        "f": "json",
    }
    r = requests.get(url, params=params, timeout=90)
    r.raise_for_status()
    data = r.json()

    if save_json_to:
        Path(save_json_to).parent.mkdir(parents=True, exist_ok=True)
        with open(save_json_to, "w") as f:
            json.dump(data, f)

    return _parse_afdc_json(data)

# Backward-compat helper (if you still call parse_afdc(json_path))
def parse_afdc(json_path: str) -> gpd.GeoDataFrame:
    with open(json_path, "r") as f:
        data = json.load(f)
    return _parse_afdc_json(data)

def ingest_afdc_to_interim(out_parquet: str = "data/interim/afdc_az.parquet") -> str:
    """
    Convenience: fetch & persist to interim parquet for reproducibility.
    """
    gdf = fetch_afdc_elec_az()
    write_geoparquet(gdf, out_parquet)
    return out_parquet

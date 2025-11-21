# src/data/ingest_acs.py
import os
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from src.common.config import AppSettings

# Example: vehicles per household, income, tenure at ZCTA
ACS_TABLES: Dict[str, str] = {
    "B08201_001E": "HH_total",
    "B08201_002E": "HH_no_vehicle",
    "B19013_001E": "median_income",
    "B25003_002E": "owner_occ",
    "B25003_003E": "renter_occ",
    "B25024_010E": "units_5plus",
}

def fetch_acs_zcta(year: int = 2023,
                   tables: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """
    Pull ACS 5-year ZCTA attributes via Census API and return a DataFrame.
    No local files required. Key is optional (higher limits with key).
    """
    env = AppSettings()
    tbl = tables or ACS_TABLES
    cols = ",".join(tbl.keys())
    base = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": f"NAME,{cols}",
        "for": "zip code tabulation area:*"
    }
    if env.CENSUS_API_KEY:
        params["key"] = env.CENSUS_API_KEY

    r = requests.get(base, params=params, timeout=90)
    r.raise_for_status()
    rows = r.json()
    header, data = rows[0], rows[1:]
    df = pd.DataFrame(data, columns=header)
    df.rename(columns=tbl, inplace=True)
    df["ZCTA5"] = df["zip code tabulation area"]
    return df[[c for c in df.columns if c not in ("NAME", "zip code tabulation area")]]

def ingest_acs_zcta_to_interim(year: int = 2023,
                               out_parquet: str = "data/interim/acs_5yr_zcta.parquet") -> str:
    """
    Convenience: fetch & persist to interim parquet for reproducibility.
    """
    df = fetch_acs_zcta(year=year)
    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_parquet, index=False)
    return out_parquet

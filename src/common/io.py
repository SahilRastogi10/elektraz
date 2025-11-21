from pathlib import Path
import json, pandas as pd, geopandas as gpd

def read_parquet(p: str | Path) -> pd.DataFrame:
    return pd.read_parquet(p)

def write_parquet(df: pd.DataFrame, p: str | Path):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)

def read_gpkg(p: str | Path, layer=None) -> gpd.GeoDataFrame:
    return gpd.read_file(p, layer=layer) if layer else gpd.read_file(p)

def write_geoparquet(gdf: gpd.GeoDataFrame, p: str | Path):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(p, index=False)

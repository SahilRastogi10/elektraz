# src/utils/remote.py
import os, io, zipfile, requests, pandas as pd, geopandas as gpd, requests_cache

# cache http responses for 24h (fast reruns)
requests_cache.install_cache("remote_cache", expire_after=24*3600)

def read_arcgis_layer(url: str, where: str="1=1", out_sr: int=4326, page: int=2000) -> gpd.GeoDataFrame:
    """
    Generic ArcGIS FeatureServer reader to GeoJSON (paged).
    Example url: https://maps.azdot.gov/arcgis/rest/services/Traffic/AADT_2024/FeatureServer/0
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
        r = requests.get(f"{url}/query", params=params, timeout=90)
        r.raise_for_status()
        js = r.json()
        batch = js.get("features", [])
        if not batch:
            break
        feats.extend(batch)
        offset += page
    return gpd.GeoDataFrame.from_features(feats, crs=f"EPSG:{out_sr}") if feats else gpd.GeoDataFrame(geometry=[], crs=f"EPSG:{out_sr}")

def read_csv_zip(url: str) -> pd.DataFrame:
    """
    Stream a zipped CSV directly (e.g., EPA EJSCREEN CSV bundle).
    """
    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    first_csv = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
    return pd.read_csv(zf.open(first_csv))

def get_afdc_az(nrel_key: str | None = None) -> gpd.GeoDataFrame:
    """
    DOE/NREL AFDC stations for AZ (public access only).
    """
    base = os.getenv("AFDC_URL", "https://developer.nrel.gov/api/alt-fuel-stations/v1.json")
    key = nrel_key or os.getenv("NREL_API_KEY", "DEMO_KEY")
    params = {"api_key": key, "fuel_type": "ELEC", "state": "AZ", "access": "public", "limit": 20000, "f": "json"}
    r = requests.get(base, params=params, timeout=90)
    r.raise_for_status()
    stations = r.json().get("fuel_stations", [])
    if not stations:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    df = pd.DataFrame(stations)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326")
    return gdf

def get_acs_zcta(year: int = 2023, census_key: str | None = None, variables: dict | None = None) -> pd.DataFrame:
    """
    Pull ACS 5-year ZCTA attributes via Census API (table fragments → DataFrame).
    """
    variables = variables or {
        "B08201_001E": "HH_total",
        "B08201_002E": "HH_no_vehicle",
        "B19013_001E": "median_income",
        "B25003_002E": "owner_occ",
        "B25003_003E": "renter_occ",
        "B25024_010E": "units_5plus",
    }
    cols = ",".join(variables.keys())
    key = census_key or os.getenv("CENSUS_API_KEY", "")
    url = f"https://api.census.gov/data/{year}/acs/acs5?get=NAME,{cols}&for=zip%20code%20tabulation%20area:*"
    if key:
        url += f"&key={key}"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    rows = r.json()
    header, data = rows[0], rows[1:]
    df = pd.DataFrame(data, columns=header)
    df.rename(columns=variables, inplace=True)
    df["ZCTA5"] = df["zip code tabulation area"]
    keep = ["ZCTA5"] + list(variables.values())
    return df[keep]

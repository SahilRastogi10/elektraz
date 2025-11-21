# src/data/dataloader.py
"""Automatic data loading system with caching."""

import os
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import pandas as pd
import geopandas as gpd
import requests
import requests_cache
from requests.exceptions import ConnectionError, Timeout, RequestException
from datetime import datetime, timedelta

from src.common.config import AppSettings, load_yaml
from src.common.io import write_geoparquet, write_parquet

logger = logging.getLogger(__name__)


# Install request cache for efficiency
requests_cache.install_cache(
    "data_cache",
    expire_after=timedelta(hours=24),
    allowable_methods=["GET", "POST"]
)


@dataclass
class DataSource:
    """Configuration for a data source."""
    name: str
    url: str
    source_type: str  # arcgis, nrel_afdc, census_acs, csv_zip, geojson
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    required: bool = True
    cache_hours: int = 24


class DataLoader:
    """Automatic data loader with caching and refresh capabilities."""
    
    def __init__(self, config_path: str = "configs/default.yaml"):
        self.config = load_yaml(config_path)
        self.env = AppSettings()
        self.cache_dir = Path("data/interim")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Define data sources
        self.sources = self._init_sources()
        
        # Track load status
        self.load_status: Dict[str, Dict] = {}
    
    def _init_sources(self) -> Dict[str, DataSource]:
        """Initialize data sources from config."""
        d = self.config.get("data", {})
        
        # Use ArcGIS Online hosted service as primary (maps.azdot.gov often unavailable)
        # Alternative: "https://maps.azdot.gov/arcgis/rest/services/Traffic/AADT_2024/FeatureServer/0"
        sources = {
            "adot_aadt": DataSource(
                name="adot_aadt",
                url=d.get("adot_aadt_url", "https://services6.arcgis.com/clPWQMwZfdWn4MQZ/arcgis/rest/services/AADT_2020_gdb/FeatureServer/0"),
                source_type="arcgis",
                description="ADOT Traffic Volumes (AADT)"
            ),
            "nfhl": DataSource(
                name="nfhl",
                url=d.get("nfhl_url", "https://services.arcgis.com/2gdL2gxYNFY2TOUb/arcgis/rest/services/FEMA_National_Flood_Hazard_Layer/FeatureServer/0"),
                source_type="arcgis",
                description="FEMA Flood Hazard Zones",
                required=False  # Optional - server availability varies
            ),
            "park_ride": DataSource(
                name="park_ride",
                url=d.get("valley_metro_pr_url", "https://maps.phoenix.gov/pub/rest/services/Public/ParkAndRide/MapServer/0"),
                source_type="arcgis",
                description="Park & Ride Locations (Phoenix)",
                required=False  # Optional - Phoenix metro area only
            ),
            "afdc_az": DataSource(
                name="afdc_az",
                url=d.get("afdc_url", "https://developer.nrel.gov/api/alt-fuel-stations/v1.json"),
                source_type="nrel_afdc",
                description="NREL AFDC EV Stations (Arizona)",
                params={"state": "AZ", "fuel_type": "ELEC", "access": "public"}
            ),
            "acs_zcta": DataSource(
                name="acs_zcta",
                url="https://api.census.gov/data/2023/acs/acs5",
                source_type="census_acs",
                description="Census ACS 5-Year ZCTA Demographics"
            ),
            "ejscreen": DataSource(
                name="ejscreen",
                url=d.get("ejscreen_csv_zip", "https://zenodo.org/records/14767363/files/EJSCREEN_2024_StatePctile.csv.zip"),
                source_type="csv_zip",
                description="EPA EJSCREEN Equity Indicators (Zenodo Archive)",
                required=False
            )
        }
        
        return sources

    def _request_with_retry(self, method: str, url: str, max_retries: int = 4,
                            initial_delay: float = 2.0, **kwargs) -> requests.Response:
        """Make HTTP request with exponential backoff retry logic.

        Args:
            method: HTTP method (get, post, etc.)
            url: URL to request
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (doubles each retry)
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            RequestException: If all retries fail
        """
        last_exception = None
        delay = initial_delay

        for attempt in range(max_retries + 1):
            try:
                response = getattr(requests, method)(url, **kwargs)
                response.raise_for_status()
                return response
            except (ConnectionError, Timeout) as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
            except RequestException as e:
                # Non-retryable errors (4xx, 5xx that aren't connection issues)
                last_exception = e
                logger.error(f"Request failed with non-retryable error: {e}")
                raise

        raise last_exception

    def get_cache_path(self, source_name: str) -> Path:
        """Get cache file path for a source."""
        return self.cache_dir / f"{source_name}.parquet"
    
    def is_cached(self, source_name: str) -> bool:
        """Check if data is cached and fresh."""
        cache_path = self.get_cache_path(source_name)
        if not cache_path.exists():
            return False
        
        # Check age
        source = self.sources.get(source_name)
        if source:
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age = datetime.now() - mtime
            return age < timedelta(hours=source.cache_hours)
        
        return True
    
    def get_cache_info(self, source_name: str) -> Dict:
        """Get cache status information."""
        cache_path = self.get_cache_path(source_name)
        source = self.sources.get(source_name)
        
        info = {
            "name": source_name,
            "cached": cache_path.exists(),
            "path": str(cache_path),
            "description": source.description if source else "",
            "required": source.required if source else True
        }
        
        if cache_path.exists():
            stat = cache_path.stat()
            info["size_mb"] = stat.st_size / (1024 * 1024)
            info["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            info["age_hours"] = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds() / 3600
        
        return info
    
    def load_arcgis(self, url: str, where: str = "1=1", out_sr: int = 4326) -> gpd.GeoDataFrame:
        """Load data from ArcGIS FeatureServer."""
        feats, offset, page = [], 0, 2000

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
            r = self._request_with_retry("get", f"{url}/query", params=params, timeout=120)
            js = r.json()
            batch = js.get("features", [])
            if not batch:
                break
            feats.extend(batch)
            offset += page

        if feats:
            return gpd.GeoDataFrame.from_features(feats, crs=f"EPSG:{out_sr}")
        return gpd.GeoDataFrame(geometry=[], crs=f"EPSG:{out_sr}")
    
    def load_nrel_afdc(self, url: str, params: Dict) -> gpd.GeoDataFrame:
        """Load EV stations from NREL AFDC API."""
        api_params = {
            "api_key": self.env.NREL_API_KEY or "DEMO_KEY",
            "limit": 20000,
            **params
        }

        r = self._request_with_retry("get", url, params=api_params, timeout=90)
        stations = r.json().get("fuel_stations", [])
        
        if not stations:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        
        rows = []
        for s in stations:
            lat, lon = s.get("latitude"), s.get("longitude")
            if lat is None or lon is None:
                continue
            rows.append({
                "station_id": s.get("id"),
                "name": s.get("station_name"),
                "network": s.get("ev_network"),
                "dcfc_ports": s.get("ev_dc_fast_num"),
                "city": s.get("city"),
                "zip": s.get("zip"),
                "lat": lat,
                "lon": lon,
                "status": s.get("status_code"),
            })
        
        df = pd.DataFrame(rows)
        return gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs="EPSG:4326"
        )
    
    def load_census_acs(self, url: str, year: int = 2023) -> pd.DataFrame:
        """Load Census ACS data."""
        variables = {
            "B08201_001E": "HH_total",
            "B08201_002E": "HH_no_vehicle",
            "B19013_001E": "median_income",
            "B25003_002E": "owner_occ",
            "B25003_003E": "renter_occ",
        }
        
        cols = ",".join(variables.keys())
        params = {
            "get": f"NAME,{cols}",
            "for": "zip code tabulation area:*"
        }
        
        if self.env.CENSUS_API_KEY:
            params["key"] = self.env.CENSUS_API_KEY

        r = self._request_with_retry("get", url, params=params, timeout=90)
        rows = r.json()
        header, data = rows[0], rows[1:]
        
        df = pd.DataFrame(data, columns=header)
        df.rename(columns=variables, inplace=True)
        df["ZCTA5"] = df["zip code tabulation area"]
        
        return df[[c for c in df.columns if c not in ("NAME", "zip code tabulation area")]]
    
    def load_csv_zip(self, url: str) -> pd.DataFrame:
        """Load data from zipped CSV."""
        import io
        import zipfile

        r = self._request_with_retry("get", url, stream=True, timeout=180)
        
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        
        if csv_files:
            return pd.read_csv(zf.open(csv_files[0]))
        return pd.DataFrame()
    
    def load(self, source_name: str, force_refresh: bool = False) -> Optional[pd.DataFrame | gpd.GeoDataFrame]:
        """Load a data source (from cache or fetch)."""
        source = self.sources.get(source_name)
        if not source:
            raise ValueError(f"Unknown source: {source_name}")

        cache_path = self.get_cache_path(source_name)

        # Use cache if available and fresh
        if not force_refresh and self.is_cached(source_name):
            try:
                if source.source_type in ["arcgis", "nrel_afdc"]:
                    return gpd.read_parquet(cache_path)
                else:
                    return pd.read_parquet(cache_path)
            except Exception:
                pass  # Fall through to fetch

        # Fetch data
        start_time = time.time()
        try:
            if source.source_type == "arcgis":
                data = self.load_arcgis(source.url)
            elif source.source_type == "nrel_afdc":
                data = self.load_nrel_afdc(source.url, source.params)
            elif source.source_type == "census_acs":
                data = self.load_census_acs(source.url)
            elif source.source_type == "csv_zip":
                data = self.load_csv_zip(source.url)
            else:
                raise ValueError(f"Unknown source type: {source.source_type}")

            # Cache
            if isinstance(data, gpd.GeoDataFrame):
                write_geoparquet(data, cache_path)
            else:
                write_parquet(data, cache_path)

            elapsed = time.time() - start_time
            self.load_status[source_name] = {
                "status": "success",
                "rows": len(data),
                "elapsed_s": elapsed,
                "timestamp": datetime.now().isoformat()
            }

            return data

        except (ConnectionError, Timeout, RequestException) as e:
            # Network error - try to fall back to cached data (even if stale)
            if cache_path.exists():
                logger.warning(
                    f"Network error loading '{source_name}': {e}. "
                    f"Falling back to cached data."
                )
                try:
                    if source.source_type in ["arcgis", "nrel_afdc"]:
                        data = gpd.read_parquet(cache_path)
                    else:
                        data = pd.read_parquet(cache_path)

                    self.load_status[source_name] = {
                        "status": "cached_fallback",
                        "rows": len(data),
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    return data
                except Exception as cache_error:
                    logger.error(f"Failed to load cached data: {cache_error}")

            # No cache available - report error
            error_msg = (
                f"Failed to load '{source_name}' from {source.url}: {e}. "
                f"No cached data available. Please check your network connection."
            )
            self.load_status[source_name] = {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            if source.required:
                raise ConnectionError(error_msg) from e
            return None

        except Exception as e:
            self.load_status[source_name] = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            if source.required:
                raise
            return None
    
    def load_all(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load all data sources."""
        results = {}
        for name in self.sources:
            try:
                results[name] = self.load(name, force_refresh)
            except Exception as e:
                if self.sources[name].required:
                    raise
                results[name] = None
        return results
    
    def get_status(self) -> pd.DataFrame:
        """Get status of all data sources."""
        rows = []
        for name in self.sources:
            info = self.get_cache_info(name)
            status = self.load_status.get(name, {})
            rows.append({
                "Source": name,
                "Description": info["description"],
                "Cached": "Yes" if info["cached"] else "No",
                "Size (MB)": f"{info.get('size_mb', 0):.2f}" if info["cached"] else "-",
                "Age (hrs)": f"{info.get('age_hours', 0):.1f}" if info["cached"] else "-",
                "Last Status": status.get("status", "not loaded"),
                "Required": "Yes" if info["required"] else "No"
            })
        return pd.DataFrame(rows)
    
    def add_source(self, name: str, url: str, source_type: str, 
                   description: str = "", params: Dict = None, required: bool = True):
        """Add a custom data source."""
        self.sources[name] = DataSource(
            name=name,
            url=url,
            source_type=source_type,
            description=description,
            params=params or {},
            required=required
        )
    
    def clear_cache(self, source_name: str = None):
        """Clear cached data."""
        if source_name:
            cache_path = self.get_cache_path(source_name)
            if cache_path.exists():
                cache_path.unlink()
        else:
            for name in self.sources:
                cache_path = self.get_cache_path(name)
                if cache_path.exists():
                    cache_path.unlink()


# Convenience function
def get_dataloader(config_path: str = "configs/default.yaml") -> DataLoader:
    """Get a configured DataLoader instance."""
    return DataLoader(config_path)

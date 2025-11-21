import geopandas as gpd
from shapely.geometry import Point
from pyproj import CRS

def to_crs(gdf: gpd.GeoDataFrame, epsg: int) -> gpd.GeoDataFrame:
    return gdf.to_crs(epsg=epsg)

def from_lonlat(df, lon_col="lon", lat_col="lat", epsg=4326):
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs=f"EPSG:{epsg}")
    return gdf

def buffer_m(gdf: gpd.GeoDataFrame, meters: float) -> gpd.GeoSeries:
    return gdf.buffer(meters)

def centroids(gdf: gpd.GeoDataFrame):
    return gdf.geometry.centroid

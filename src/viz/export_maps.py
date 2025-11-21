import geopandas as gpd
from src.common.io import write_geoparquet

def export_map_layers(candidates_gdf, selected_gdf, out_gpkg="artifacts/reports/selected_sites.gpkg"):
    candidates_gdf.to_file(out_gpkg, layer="candidates", driver="GPKG")
    selected_gdf.to_file(out_gpkg, layer="selected", driver="GPKG")

# app/pages/3_Map_View.py
"""Interactive map visualization."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Map View", page_icon="🗺️", layout="wide")

st.title("🗺️ Interactive Map View")
st.markdown("Visualize candidates, existing stations, and optimization results.")

# Load data
@st.cache_data
def load_map_data():
    data = {}
    
    processed_path = Path("data/processed")
    interim_path = Path("data/interim")
    artifacts_path = Path("artifacts/reports")
    
    if (artifacts_path / "selected_sites.parquet").exists():
        data["selected"] = gpd.read_parquet(artifacts_path / "selected_sites.parquet").to_crs(4326)
    
    for name, path in [
        ("candidates", processed_path / "features_scored_pv.parquet"),
        ("candidates", processed_path / "features_scored.parquet"),
        ("candidates", processed_path / "features.parquet"),
        ("candidates", interim_path / "candidates.parquet"),
    ]:
        if path.exists() and name not in data:
            data[name] = gpd.read_parquet(path).to_crs(4326)
            break
    
    if (interim_path / "afdc_az.parquet").exists():
        data["existing"] = gpd.read_parquet(interim_path / "afdc_az.parquet").to_crs(4326)
    
    if (interim_path / "adot_aadt.parquet").exists():
        data["aadt"] = gpd.read_parquet(interim_path / "adot_aadt.parquet").to_crs(4326)
    
    return data

data = load_map_data()

if not data:
    st.warning("No data available. Run the pipeline first.")
    st.code("python cli.py run-all")
    st.stop()

# Sidebar controls
st.sidebar.header("Map Controls")

# Layer toggles
st.sidebar.subheader("Layers")
show_selected = st.sidebar.checkbox("Selected Sites", value=True, disabled="selected" not in data)
show_candidates = st.sidebar.checkbox("Candidates", value=False, disabled="candidates" not in data)
show_existing = st.sidebar.checkbox("Existing Stations", value=True, disabled="existing" not in data)
show_aadt = st.sidebar.checkbox("AADT Roads", value=False, disabled="aadt" not in data)

# Color by
if "candidates" in data:
    color_options = ["None"] + [c for c in data["candidates"].columns 
                               if c not in ["geometry", "cand_id"] and 
                               data["candidates"][c].dtype in ["int64", "float64"]]
    color_by = st.sidebar.selectbox("Color candidates by", color_options)
else:
    color_by = "None"

# Create map
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# Center on Arizona
m = folium.Map(location=[34.0, -111.5], zoom_start=7, tiles="CartoDB positron")

# Add tile layer options
folium.TileLayer("OpenStreetMap").add_to(m)
folium.TileLayer("CartoDB dark_matter", name="Dark").add_to(m)

# Add AADT roads
if show_aadt and "aadt" in data:
    aadt = data["aadt"]
    if len(aadt) > 0:
        # Simplify for performance
        aadt_sample = aadt.head(1000)
        for idx, row in aadt_sample.iterrows():
            if row.geometry.geom_type in ["LineString", "MultiLineString"]:
                coords = []
                if row.geometry.geom_type == "LineString":
                    coords = [[p[1], p[0]] for p in row.geometry.coords]
                else:
                    for line in row.geometry.geoms:
                        coords.extend([[p[1], p[0]] for p in line.coords])
                
                aadt_val = row.get("AADT", 0)
                weight = max(1, min(5, aadt_val / 20000))
                
                folium.PolyLine(
                    coords,
                    weight=weight,
                    color="orange",
                    opacity=0.5,
                    popup=f"AADT: {aadt_val:,.0f}"
                ).add_to(m)

# Add existing stations
if show_existing and "existing" in data:
    existing = data["existing"]
    existing_group = folium.FeatureGroup(name="Existing Stations")
    
    for idx, row in existing.iterrows():
        if row.geometry.geom_type == "Point":
            popup_text = f"""
            <b>{row.get('name', 'Station')}</b><br>
            Network: {row.get('network', 'N/A')}<br>
            DCFC Ports: {row.get('dcfc_ports', 'N/A')}<br>
            City: {row.get('city', 'N/A')}
            """
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=4,
                color="gray",
                fill=True,
                fillColor="gray",
                fillOpacity=0.6,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(existing_group)
    
    existing_group.add_to(m)

# Add candidates
if show_candidates and "candidates" in data:
    candidates = data["candidates"]
    cand_group = folium.FeatureGroup(name="Candidates")
    
    # Color scale
    if color_by != "None" and color_by in candidates.columns:
        values = candidates[color_by].fillna(0)
        vmin, vmax = values.min(), values.max()
        
        def get_color(val):
            if pd.isna(val) or vmax == vmin:
                return "blue"
            norm = (val - vmin) / (vmax - vmin)
            # Handle edge cases where norm could be NaN or out of range
            if pd.isna(norm) or norm < 0 or norm > 1:
                return "blue"
            # Blue to red gradient
            r = int(255 * norm)
            b = int(255 * (1 - norm))
            return f"#{r:02x}00{b:02x}"
    else:
        get_color = lambda x: "blue"
    
    # Limit for performance
    for idx, row in candidates.head(500).iterrows():
        if row.geometry.geom_type == "Point":
            color = get_color(row.get(color_by, 0)) if color_by != "None" else "blue"
            
            popup_text = f"""
            <b>Candidate {row.get('cand_id', idx)}</b><br>
            Source: {row.get('src', 'N/A')}<br>
            In AFC: {row.get('in_afc', 'N/A')}<br>
            """
            if "pred_daily_kwh" in row:
                popup_text += f"Pred. Daily kWh: {row['pred_daily_kwh']:.1f}<br>"
            if "pv_kw_sized" in row:
                popup_text += f"PV Size: {row['pv_kw_sized']:.0f} kW<br>"
            
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=4,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.5,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(cand_group)
    
    cand_group.add_to(m)

# Add selected sites
if show_selected and "selected" in data:
    selected = data["selected"]
    selected_group = folium.FeatureGroup(name="Selected Sites")
    
    for idx, row in selected.iterrows():
        if row.geometry.geom_type == "Point":
            popup_text = f"""
            <b>Selected Site {row.get('cand_id', idx)}</b><br>
            Ports: {row.get('ports', 'N/A')}<br>
            PV: {row.get('pv_kw', row.get('pv_kw_sized', 'N/A'))} kW<br>
            Storage: {row.get('storage_kwh', 'N/A')} kWh<br>
            """
            if "pred_daily_kwh" in row:
                popup_text += f"Pred. Daily kWh: {row['pred_daily_kwh']:.1f}<br>"
            if "net_capex" in row:
                popup_text += f"Net CapEx: ${row['net_capex']:,.0f}<br>"
            if "npv" in row:
                popup_text += f"NPV: ${row['npv']:,.0f}<br>"
            
            # Size marker by ports
            radius = 6 + (row.get('ports', 4) - 4) * 2
            
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=radius,
                color="green",
                fill=True,
                fillColor="green",
                fillOpacity=0.8,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(selected_group)
            
            # Add label
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 10px; color: white; background: green; padding: 2px; border-radius: 3px;">{row.get("ports", "")}</div>'
                )
            ).add_to(selected_group)
    
    selected_group.add_to(m)

# Layer control
folium.LayerControl().add_to(m)

# Display map
st_folium(m, width=None, height=600)

# Legend
st.markdown("""
**Legend:**
- 🟢 **Selected Sites** (size = ports)
- 🔵 **Candidates**
- ⚫ **Existing Stations**
- 🟠 **AADT Roads** (width = traffic volume)
""")

# Summary stats
if "selected" in data:
    st.markdown("---")
    st.subheader("Selected Sites Summary")
    
    selected = data["selected"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sites", len(selected))
    with col2:
        if "ports" in selected.columns:
            st.metric("Total Ports", int(selected["ports"].sum()))
    with col3:
        if "pv_kw" in selected.columns:
            st.metric("Total PV (kW)", f"{selected['pv_kw'].sum():,.0f}")
        elif "pv_kw_sized" in selected.columns:
            st.metric("Total PV (kW)", f"{selected['pv_kw_sized'].sum():,.0f}")
    with col4:
        if "net_capex" in selected.columns:
            st.metric("Total Net CapEx", f"${selected['net_capex'].sum():,.0f}")

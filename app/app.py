# app/app.py
"""Elektraz - Arizona Solar EV Charging Station Optimization Dashboard."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import load_yaml

st.set_page_config(
    page_title="Elektraz - AZ Solar EV Siting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)


def load_data():
    """Load available data files."""
    data = {}
    
    # Check for processed data
    processed_path = Path("data/processed")
    interim_path = Path("data/interim")
    artifacts_path = Path("artifacts/reports")
    
    if (processed_path / "features_scored_pv.parquet").exists():
        data["candidates"] = gpd.read_parquet(processed_path / "features_scored_pv.parquet")
    elif (processed_path / "features_scored.parquet").exists():
        data["candidates"] = gpd.read_parquet(processed_path / "features_scored.parquet")
    elif (processed_path / "features.parquet").exists():
        data["candidates"] = gpd.read_parquet(processed_path / "features.parquet")
    elif (interim_path / "candidates.parquet").exists():
        data["candidates"] = gpd.read_parquet(interim_path / "candidates.parquet")
    
    if (interim_path / "afdc_az.parquet").exists():
        data["existing_stations"] = gpd.read_parquet(interim_path / "afdc_az.parquet")
    
    if (interim_path / "adot_aadt.parquet").exists():
        data["aadt"] = gpd.read_parquet(interim_path / "adot_aadt.parquet")
    
    if (artifacts_path / "selected_sites.parquet").exists():
        data["selected_sites"] = gpd.read_parquet(artifacts_path / "selected_sites.parquet")
    
    return data


def main():
    # Header
    st.markdown('<p class="main-header">⚡ Elektraz</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Arizona Solar EV Charging Station Placement Optimization</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Load data
    data = load_data()
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if "candidates" in data:
            st.metric("Candidate Sites", len(data["candidates"]))
        else:
            st.metric("Candidate Sites", "N/A")
    
    with col2:
        if "existing_stations" in data:
            st.metric("Existing Stations", len(data["existing_stations"]))
        else:
            st.metric("Existing Stations", "N/A")
    
    with col3:
        if "selected_sites" in data:
            st.metric("Selected Sites", len(data["selected_sites"]))
        else:
            st.metric("Selected Sites", "N/A")
    
    with col4:
        if "selected_sites" in data and "ports" in data["selected_sites"].columns:
            st.metric("Total Ports", int(data["selected_sites"]["ports"].sum()))
        else:
            st.metric("Total Ports", "N/A")
    
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🗺️ Quick Map", "📈 Quick Stats"])
    
    with tab1:
        st.subheader("Project Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### Objective
            Optimize placement of solar-powered DC fast charging (DCFC) stations across Arizona to:
            - Maximize access and equity for EV drivers
            - Minimize lifecycle costs
            - Ensure reliability under Arizona heat
            - Comply with NEVI corridor requirements
            - Leverage solar resources
            
            ### Methodology
            1. **Data Ingestion** - Pull from public APIs (ADOT, NREL, Census, EPA)
            2. **Candidate Generation** - Identify potential sites from rest areas, P&R, high-traffic areas
            3. **Feature Engineering** - Compute accessibility, equity, safety scores
            4. **ML Prediction** - Ensemble models predict daily energy demand
            5. **PV Sizing** - Size solar arrays via PVWatts API
            6. **Optimization** - MILP facility location with budget/spacing constraints
            """)
        
        with col2:
            st.markdown("""
            ### Key Constraints
            - **Budget**: $15,000,000
            - **Max Sites**: 40
            - **Min Spacing**: 50 km (NEVI requirement)
            - **Ports/Site**: 4-8 (150 kW each)
            - **PV Range**: 50-300 kW per site
            - **Storage**: 0-500 kWh per site
            
            ### Navigation
            Use the sidebar to navigate between pages:
            - **Data Explorer** - View and analyze datasets
            - **Configuration** - Adjust costs and parameters
            - **Map View** - Interactive map visualization
            - **Run Optimization** - Execute the pipeline
            - **Results** - View selected sites and reports
            - **ML Insights** - SHAP explanations
            """)
        
        # Data status
        st.subheader("Data Status")
        
        status_data = []
        for name, display in [
            ("candidates", "Candidate Sites"),
            ("existing_stations", "Existing Stations"),
            ("aadt", "AADT Traffic Data"),
            ("selected_sites", "Optimization Results")
        ]:
            status_data.append({
                "Dataset": display,
                "Status": "✅ Available" if name in data else "❌ Not loaded",
                "Records": len(data[name]) if name in data else 0
            })
        
        st.dataframe(pd.DataFrame(status_data), width='stretch', hide_index=True)
    
    with tab2:
        st.subheader("Site Locations")
        
        if "candidates" in data or "selected_sites" in data:
            import folium
            from streamlit_folium import st_folium
            
            # Create map centered on Arizona
            m = folium.Map(location=[34.0, -111.5], zoom_start=7, tiles="CartoDB positron")
            
            # Add existing stations
            if "existing_stations" in data:
                stations = data["existing_stations"].to_crs(4326)
                for idx, row in stations.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=3,
                        color="gray",
                        fill=True,
                        fillOpacity=0.5,
                        popup=row.get("name", "Existing Station")
                    ).add_to(m)
            
            # Add selected sites
            if "selected_sites" in data:
                selected = data["selected_sites"].to_crs(4326)
                for idx, row in selected.iterrows():
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=8,
                        color="green",
                        fill=True,
                        fillColor="green",
                        fillOpacity=0.8,
                        popup=f"Site {row.get('cand_id', idx)}<br>Ports: {row.get('ports', 'N/A')}"
                    ).add_to(m)
            
            # Add candidates
            elif "candidates" in data:
                cands = data["candidates"].to_crs(4326)
                for idx, row in cands.head(500).iterrows():  # Limit for performance
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=3,
                        color="blue",
                        fill=True,
                        fillOpacity=0.3
                    ).add_to(m)
            
            st_folium(m, width=None, height=500)
            
            st.caption("🟢 Selected Sites | 🔵 Candidates | ⚫ Existing Stations")
        else:
            st.info("No data available. Run the pipeline to generate candidates.")
    
    with tab3:
        st.subheader("Quick Statistics")
        
        if "selected_sites" in data:
            selected = data["selected_sites"]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Site Configuration")
                if "ports" in selected.columns:
                    st.bar_chart(selected["ports"].value_counts().sort_index())
                
                if "pv_kw" in selected.columns:
                    st.markdown("**PV System Sizes (kW)**")
                    st.dataframe(selected["pv_kw"].describe())
            
            with col2:
                st.markdown("#### Economics (if available)")
                if "net_capex" in selected.columns:
                    total_capex = selected["net_capex"].sum()
                    st.metric("Total Net CapEx", f"${total_capex:,.0f}")
                
                if "npv" in selected.columns:
                    total_npv = selected["npv"].sum()
                    st.metric("Portfolio NPV", f"${total_npv:,.0f}")
        
        elif "candidates" in data:
            cands = data["candidates"]
            
            st.markdown("#### Candidate Distribution")
            
            if "aadt_sum_1500m" in cands.columns:
                st.markdown("**AADT Density (1500m radius)**")
                hist_data = pd.cut(cands["aadt_sum_1500m"], bins=10).value_counts().sort_index()
                hist_data.index = hist_data.index.astype(str)
                st.bar_chart(hist_data)
            
            if "pred_daily_kwh" in cands.columns:
                st.markdown("**Predicted Daily kWh**")
                st.line_chart(cands["pred_daily_kwh"].sort_values().reset_index(drop=True))
        else:
            st.info("Run the pipeline to see statistics.")


if __name__ == "__main__":
    main()

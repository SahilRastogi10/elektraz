# app/pages/7_Data_Management.py
"""Data management with automatic loading and refresh."""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.dataloader import get_dataloader, DataSource

st.set_page_config(page_title="Data Management", page_icon="🔄", layout="wide")

st.title("🔄 Data Management")
st.markdown("Manage data sources, refresh data, and retrain models on updated data.")

# Initialize dataloader
@st.cache_resource
def init_loader():
    return get_dataloader()

loader = init_loader()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Sources", "➕ Add Source", "🔄 Refresh Data", "🧠 Retrain Models"])

with tab1:
    st.subheader("Configured Data Sources")
    
    # Show status
    status_df = loader.get_status()
    
    # Color code status
    def color_status(val):
        if val == "Yes":
            return "background-color: #90EE90"
        elif val == "No":
            return "background-color: #FFB6C1"
        return ""
    
    styled_df = status_df.style.map(
        color_status, subset=["Cached"]
    )

    st.dataframe(styled_df, width='stretch', hide_index=True)
    
    # Source details
    st.markdown("---")
    st.subheader("Source Details")
    
    selected_source = st.selectbox("Select source for details", list(loader.sources.keys()))
    
    if selected_source:
        source = loader.sources[selected_source]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Name:** {source.name}")
            st.markdown(f"**Type:** {source.source_type}")
            st.markdown(f"**Description:** {source.description}")
            st.markdown(f"**Required:** {'Yes' if source.required else 'No'}")
        
        with col2:
            st.markdown(f"**URL:**")
            st.code(source.url, language=None)
            
            if source.params:
                st.markdown("**Parameters:**")
                st.json(source.params)
        
        # Cache info
        cache_info = loader.get_cache_info(selected_source)
        
        if cache_info["cached"]:
            st.success(f"✅ Cached: {cache_info['size_mb']:.2f} MB, Age: {cache_info['age_hours']:.1f} hours")
        else:
            st.warning("⏳ Not cached")

with tab2:
    st.subheader("Add Custom Data Source")
    
    st.markdown("Add a new data source to the loader.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_name = st.text_input("Source Name", placeholder="my_custom_data")
        new_url = st.text_input("URL", placeholder="https://...")
        new_type = st.selectbox("Source Type", [
            "arcgis",
            "nrel_afdc", 
            "census_acs",
            "csv_zip",
            "geojson"
        ])
    
    with col2:
        new_desc = st.text_input("Description", placeholder="My custom data source")
        new_required = st.checkbox("Required", value=False)
        new_params = st.text_area("Parameters (JSON)", placeholder='{"key": "value"}')
    
    if st.button("➕ Add Source"):
        if new_name and new_url:
            try:
                params = {}
                if new_params:
                    import json
                    params = json.loads(new_params)
                
                loader.add_source(
                    name=new_name,
                    url=new_url,
                    source_type=new_type,
                    description=new_desc,
                    params=params,
                    required=new_required
                )
                st.success(f"Added source: {new_name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding source: {e}")
        else:
            st.error("Name and URL are required")

with tab3:
    st.subheader("Refresh Data")
    
    st.markdown("Load or refresh data from sources. Cached data will be used unless you force refresh.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Load Individual Source")
        
        source_to_load = st.selectbox("Select source", list(loader.sources.keys()), key="load_source")
        force_refresh_single = st.checkbox("Force refresh", key="force_single")
        
        if st.button("📥 Load Source"):
            with st.spinner(f"Loading {source_to_load}..."):
                try:
                    data = loader.load(source_to_load, force_refresh=force_refresh_single)
                    if data is not None:
                        st.success(f"Loaded {len(data)} records")
                        
                        # Show preview
                        with st.expander("Preview data"):
                            if hasattr(data, "drop"):
                                st.dataframe(data.drop(columns=["geometry"], errors="ignore").head(10))
                            else:
                                st.dataframe(data.head(10))
                    else:
                        st.warning("No data returned")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with col2:
        st.markdown("#### Load All Sources")
        
        force_refresh_all = st.checkbox("Force refresh all", key="force_all")
        
        if st.button("📥 Load All Sources"):
            progress = st.progress(0)
            status_area = st.empty()
            
            sources = list(loader.sources.keys())
            for i, name in enumerate(sources):
                status_area.text(f"Loading {name}...")
                try:
                    data = loader.load(name, force_refresh=force_refresh_all)
                    if data is not None:
                        status_area.text(f"✅ {name}: {len(data)} records")
                except Exception as e:
                    status_area.text(f"❌ {name}: {e}")
                
                progress.progress((i + 1) / len(sources))
            
            st.success("All sources loaded!")
            st.rerun()
    
    st.markdown("---")
    st.markdown("#### Clear Cache")
    
    col1, col2 = st.columns(2)
    
    with col1:
        source_to_clear = st.selectbox("Select source to clear", ["All"] + list(loader.sources.keys()))
        
        if st.button("🗑️ Clear Cache"):
            if source_to_clear == "All":
                loader.clear_cache()
                st.success("All caches cleared!")
            else:
                loader.clear_cache(source_to_clear)
                st.success(f"Cache cleared for {source_to_clear}")
            st.rerun()

with tab4:
    st.subheader("Retrain Models on Updated Data")
    
    st.markdown("""
    After refreshing data, you can retrain the ML models and re-run the optimization
    to get updated results based on the new data.
    """)
    
    # Check current status
    models_exist = Path("artifacts/models/ensemble.joblib").exists()
    features_exist = Path("data/processed/features.parquet").exists()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Current Status")
        
        if features_exist:
            st.success("✅ Features computed")
        else:
            st.warning("⏳ Features not computed")
        
        if models_exist:
            st.success("✅ Models trained")
            model_time = datetime.fromtimestamp(
                Path("artifacts/models/ensemble.joblib").stat().st_mtime
            )
            st.caption(f"Last trained: {model_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.warning("⏳ Models not trained")
    
    with col2:
        st.markdown("#### Retrain Options")
        
        compute_shap = st.checkbox("Compute SHAP explanations", value=True)
        
        if st.button("🔄 Re-engineer Features", disabled=not any(
            loader.get_cache_path(s).exists() for s in loader.sources
        )):
            with st.spinner("Re-engineering features..."):
                import subprocess
                result = subprocess.run(
                    ["python", "cli.py", "features"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Features re-engineered!")
                    st.code(result.stdout)
                else:
                    st.error(f"Error: {result.stderr}")
        
        if st.button("🧠 Retrain ML Models", disabled=not features_exist):
            with st.spinner("Retraining models..."):
                import subprocess
                cmd = ["python", "cli.py", "train", "--retrain"]
                if compute_shap:
                    cmd.append("--save-shap")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    st.success("Models retrained!")
                    st.code(result.stdout)
                else:
                    st.error(f"Error: {result.stderr}")
        
        if st.button("☀️ Re-size PV Systems", disabled=not Path("data/processed/features_scored.parquet").exists()):
            with st.spinner("Re-sizing PV systems..."):
                import subprocess
                result = subprocess.run(
                    ["python", "cli.py", "pvsize"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("PV sizing complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Error: {result.stderr}")
        
        if st.button("📊 Re-run Optimization", disabled=not Path("data/processed/features_scored_pv.parquet").exists()):
            with st.spinner("Running optimization..."):
                import subprocess
                result = subprocess.run(
                    ["python", "cli.py", "optimize"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Optimization complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Error: {result.stderr}")
    
    st.markdown("---")
    st.markdown("#### Quick Actions")
    
    if st.button("🚀 Full Pipeline (Load + Retrain + Optimize)", type="primary"):
        with st.spinner("Running full pipeline..."):
            import subprocess
            result = subprocess.run(
                ["python", "cli.py", "run-all", "--force-refresh"],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode == 0:
                st.success("Full pipeline complete!")
                st.code(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
                st.balloons()
            else:
                st.error(f"Error: {result.stderr}")

# API Key Status
st.markdown("---")
st.subheader("API Configuration")

from src.common.config import AppSettings
env = AppSettings()

col1, col2 = st.columns(2)

with col1:
    if env.NREL_API_KEY and env.NREL_API_KEY != "DEMO_KEY":
        st.success("✅ NREL API Key configured")
    else:
        st.warning("⚠️ Using DEMO_KEY for NREL (rate limited)")
        st.markdown("Get a key at: https://developer.nrel.gov/signup/")

with col2:
    if env.CENSUS_API_KEY:
        st.success("✅ Census API Key configured")
    else:
        st.warning("⚠️ Census API Key not set (may hit rate limits)")
        st.markdown("Get a key at: https://api.census.gov/data/key_signup.html")

st.markdown("Set keys in `.env` file or environment variables.")

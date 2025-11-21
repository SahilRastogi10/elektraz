# app/pages/1_Data_Explorer.py
"""Data Explorer page."""

import streamlit as st
import pandas as pd
import geopandas as gpd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Data Explorer", page_icon="📊", layout="wide")

st.title("📊 Data Explorer")
st.markdown("Explore and analyze the datasets used in the optimization.")

# Data paths
interim_path = Path("data/interim")
processed_path = Path("data/processed")
artifacts_path = Path("artifacts/reports")


def load_dataset(path):
    """Load parquet file as GeoDataFrame or DataFrame."""
    if path.suffix == ".parquet":
        try:
            return gpd.read_parquet(path)
        except:
            return pd.read_parquet(path)
    return None


# Sidebar - dataset selection
st.sidebar.header("Dataset Selection")

datasets = {}

# Scan for available datasets
for p in interim_path.glob("*.parquet"):
    datasets[f"interim/{p.stem}"] = p
for p in processed_path.glob("*.parquet"):
    datasets[f"processed/{p.stem}"] = p
for p in artifacts_path.glob("*.parquet"):
    datasets[f"reports/{p.stem}"] = p

if not datasets:
    st.warning("No datasets found. Run the data ingestion pipeline first.")
    st.code("python cli.py ingest-remote")
    st.stop()

selected = st.sidebar.selectbox("Select Dataset", list(datasets.keys()))
path = datasets[selected]

# Load data
with st.spinner(f"Loading {selected}..."):
    df = load_dataset(path)

if df is None:
    st.error(f"Failed to load {selected}")
    st.stop()

# Display info
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Rows", len(df))
with col2:
    st.metric("Columns", len(df.columns))
with col3:
    st.metric("Type", "GeoDataFrame" if isinstance(df, gpd.GeoDataFrame) else "DataFrame")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Preview", "📊 Statistics", "🔍 Filter", "📈 Visualize"])

with tab1:
    st.subheader("Data Preview")
    
    # Column selection
    all_cols = [c for c in df.columns if c != "geometry"]
    default_cols = all_cols[:10] if len(all_cols) > 10 else all_cols
    
    selected_cols = st.multiselect("Select columns to display", all_cols, default=default_cols)
    
    if selected_cols:
        st.dataframe(df[selected_cols].head(100), use_container_width=True)
    else:
        st.dataframe(df.drop(columns=["geometry"], errors="ignore").head(100), use_container_width=True)
    
    # Download
    csv = df.drop(columns=["geometry"], errors="ignore").to_csv(index=False)
    st.download_button("Download CSV", csv, f"{selected.split('/')[-1]}.csv", "text/csv")

with tab2:
    st.subheader("Column Statistics")
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        stats = df[numeric_cols].describe().T
        stats["null_pct"] = (df[numeric_cols].isnull().sum() / len(df) * 100).values
        st.dataframe(stats, use_container_width=True)
    else:
        st.info("No numeric columns found")
    
    # Data types
    st.subheader("Column Types")
    dtypes = pd.DataFrame({
        "Column": df.columns,
        "Type": df.dtypes.astype(str).values,
        "Non-Null": df.notnull().sum().values,
        "Null %": (df.isnull().sum() / len(df) * 100).round(2).values
    })
    st.dataframe(dtypes, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Filter Data")
    
    # Simple filtering
    col1, col2 = st.columns(2)
    
    with col1:
        filter_col = st.selectbox("Filter by column", ["None"] + all_cols)
    
    if filter_col != "None":
        with col2:
            if df[filter_col].dtype in ["int64", "float64"]:
                min_val, max_val = float(df[filter_col].min()), float(df[filter_col].max())
                range_vals = st.slider("Value range", min_val, max_val, (min_val, max_val))
                filtered = df[(df[filter_col] >= range_vals[0]) & (df[filter_col] <= range_vals[1])]
            else:
                unique_vals = df[filter_col].dropna().unique()[:100]
                selected_vals = st.multiselect("Select values", unique_vals)
                if selected_vals:
                    filtered = df[df[filter_col].isin(selected_vals)]
                else:
                    filtered = df
        
        st.metric("Filtered rows", len(filtered))
        st.dataframe(filtered.drop(columns=["geometry"], errors="ignore").head(100), use_container_width=True)
    else:
        st.info("Select a column to filter")

with tab4:
    st.subheader("Quick Visualizations")
    
    import numpy as np
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        col1, col2 = st.columns(2)
        
        with col1:
            hist_col = st.selectbox("Histogram column", numeric_cols)
            if hist_col:
                st.bar_chart(pd.cut(df[hist_col].dropna(), bins=20).value_counts().sort_index())
        
        with col2:
            if len(numeric_cols) >= 2:
                scatter_x = st.selectbox("Scatter X", numeric_cols, index=0)
                scatter_y = st.selectbox("Scatter Y", numeric_cols, index=min(1, len(numeric_cols)-1))
                
                scatter_data = df[[scatter_x, scatter_y]].dropna().head(1000)
                st.scatter_chart(scatter_data, x=scatter_x, y=scatter_y)
    else:
        st.info("No numeric columns for visualization")

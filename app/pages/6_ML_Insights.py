# app/pages/6_ML_Insights.py
"""ML model insights and SHAP explanations."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import joblib
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="ML Insights", page_icon="🤖", layout="wide")

st.title("🤖 ML Model Insights")
st.markdown("Explore feature importance and SHAP explanations.")

# Paths
models_path = Path("artifacts/models")
processed_path = Path("data/processed")

# Load models
model_path = models_path / "ensemble.joblib"
if not model_path.exists():
    st.warning("No trained models found. Run the training step first.")
    st.page_link("pages/4_Run_Optimization.py", label="Go to Run Optimization", icon="🚀")
    st.stop()

# Load data
features_path = processed_path / "features_scored.parquet"
if not features_path.exists():
    features_path = processed_path / "features.parquet"

if features_path.exists():
    features = gpd.read_parquet(features_path)
else:
    st.error("No feature data found.")
    st.stop()

# Model info
st.subheader("Model Information")

try:
    models = joblib.load(model_path)
    st.success(f"Loaded {len(models)} models: {', '.join(models.keys())}")
except Exception as e:
    st.error(f"Error loading models: {e}")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Feature Importance", "🔍 SHAP Analysis", "📈 Predictions"])

with tab1:
    st.subheader("Feature Importance")
    
    # Check for saved SHAP results
    shap_files = list(models_path.glob("shap_*.parquet"))
    
    if shap_files:
        st.markdown("#### SHAP-based Feature Importance")
        
        for shap_file in shap_files:
            model_name = shap_file.stem.replace("shap_", "")
            importance_df = pd.read_parquet(shap_file)
            
            st.markdown(f"**{model_name.upper()}**")
            
            # Bar chart
            top_n = min(15, len(importance_df))
            chart_data = importance_df.head(top_n).set_index("feature")
            st.bar_chart(chart_data["importance"])
            
            # Table
            with st.expander("View all features"):
                st.dataframe(importance_df, use_container_width=True, hide_index=True)
    else:
        st.info("SHAP importance not computed. Re-run training with --save-shap flag.")
        
        # Show basic feature importance from models
        st.markdown("#### Model-based Feature Importance")
        
        for name, pipe in models.items():
            model = pipe.named_steps["model"]
            
            if hasattr(model, "feature_importances_"):
                # Get feature names from preprocessor
                prep = pipe.named_steps["prep"]
                feature_names = []
                for trans_name, trans, cols in prep.transformers_:
                    if trans_name == "num":
                        feature_names.extend(cols)
                
                if len(feature_names) == len(model.feature_importances_):
                    importance_df = pd.DataFrame({
                        "feature": feature_names,
                        "importance": model.feature_importances_
                    }).sort_values("importance", ascending=False)
                    
                    st.markdown(f"**{name.upper()}**")
                    st.bar_chart(importance_df.set_index("feature")["importance"])

with tab2:
    st.subheader("SHAP Analysis")
    
    st.markdown("""
    SHAP (SHapley Additive exPlanations) values show how each feature contributes 
    to individual predictions.
    """)
    
    # Check if SHAP is available
    try:
        import shap
        shap_available = True
    except ImportError:
        shap_available = False
        st.warning("SHAP not installed. Install with: pip install shap")
    
    if shap_available and shap_files:
        model_select = st.selectbox(
            "Select model",
            [f.stem.replace("shap_", "") for f in shap_files]
        )
        
        # Load SHAP data
        shap_df = pd.read_parquet(models_path / f"shap_{model_select}.parquet")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Top Important Features")
            st.dataframe(shap_df.head(10), use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### Feature Impact")
            st.bar_chart(shap_df.head(10).set_index("feature")["importance"])
        
        # Compute live SHAP for a sample
        if st.button("🔄 Compute SHAP for Sample"):
            with st.spinner("Computing SHAP values..."):
                try:
                    from src.ml.tabular_sklearn import compute_shap_values
                    
                    # Prepare data
                    num_cols = ["aadt_sum_500m", "aadt_sum_1500m", "aadt_sum_5000m", "dist_m_nearest_dcfc"]
                    X = features[num_cols].copy().fillna(0)
                    
                    shap_results = compute_shap_values(models, X, sample_size=500)
                    
                    for name, res in shap_results.items():
                        if "feature_importance" in res:
                            st.markdown(f"**{name.upper()} - Updated SHAP**")
                            st.dataframe(res["feature_importance"].head(10))
                    
                    st.success("SHAP computation complete!")
                except Exception as e:
                    st.error(f"Error computing SHAP: {e}")
    
    elif shap_available:
        st.info("Run training with --save-shap to generate SHAP explanations.")

with tab3:
    st.subheader("Prediction Analysis")
    
    if "pred_daily_kwh" in features.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Prediction Distribution")
            st.bar_chart(
                pd.cut(features["pred_daily_kwh"], bins=20).value_counts().sort_index()
            )
            
            st.markdown("#### Prediction Statistics")
            st.dataframe(features["pred_daily_kwh"].describe())
        
        with col2:
            st.markdown("#### Predictions vs Features")
            
            # Scatter plot
            feature_select = st.selectbox(
                "Compare with feature",
                ["aadt_sum_1500m", "aadt_sum_500m", "aadt_sum_5000m", "dist_m_nearest_dcfc"]
            )
            
            if feature_select in features.columns:
                scatter_data = features[[feature_select, "pred_daily_kwh"]].dropna().head(1000)
                st.scatter_chart(scatter_data, x=feature_select, y="pred_daily_kwh")
        
        # Top predictions
        st.markdown("---")
        st.markdown("#### Top Predicted Sites")
        
        top_n = st.slider("Number of sites", 5, 50, 20)
        top_sites = features.nlargest(top_n, "pred_daily_kwh")
        
        display_cols = ["cand_id", "pred_daily_kwh", "aadt_sum_1500m", "dist_m_nearest_dcfc"]
        display_cols = [c for c in display_cols if c in top_sites.columns]
        
        st.dataframe(
            top_sites[display_cols].round(2),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No predictions available. Run the training step first.")

# Model comparison
st.markdown("---")
st.subheader("Model Comparison")

# Show CV results if available
cv_results_path = models_path / "cv_results.json"
if cv_results_path.exists():
    import json
    with open(cv_results_path) as f:
        cv_results = json.load(f)
    
    results_df = pd.DataFrame(cv_results).T
    st.dataframe(results_df, use_container_width=True)
else:
    st.info("CV results not saved. The models were trained with cross-validation.")
    
    # Show basic model comparison
    comparison_data = []
    for name, pipe in models.items():
        model = pipe.named_steps["model"]
        comparison_data.append({
            "Model": name.upper(),
            "Type": type(model).__name__,
            "Estimators": getattr(model, "n_estimators", getattr(model, "iterations", "N/A"))
        })
    
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

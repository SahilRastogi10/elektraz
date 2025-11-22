# app/pages/4_Run_Optimization.py
"""Run optimization pipeline."""

import streamlit as st
import subprocess
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Run Optimization", page_icon="🚀", layout="wide")

st.title("🚀 Run Optimization Pipeline")
st.markdown("Execute the data processing and optimization pipeline.")

# Check data status
interim_path = Path("data/interim")
processed_path = Path("data/processed")
artifacts_path = Path("artifacts/reports")

# Status indicators
st.subheader("Pipeline Status")

steps = [
    ("Ingestion", interim_path / "adot_aadt.parquet"),
    ("Candidates", interim_path / "candidates.parquet"),
    ("Features", processed_path / "features.parquet"),
    ("Training", processed_path / "features_scored.parquet"),
    ("PV Sizing", processed_path / "features_scored_pv.parquet"),
    ("Optimization", artifacts_path / "selected_sites.parquet"),
]

cols = st.columns(len(steps))
for i, (name, path) in enumerate(steps):
    with cols[i]:
        if path.exists():
            st.success(f"✅ {name}")
        else:
            st.warning(f"⏳ {name}")

st.markdown("---")

# Run options
st.subheader("Run Pipeline")

tab1, tab2 = st.tabs(["🚀 Full Pipeline", "🔧 Individual Steps"])

with tab1:
    st.markdown("""
    Run the complete optimization pipeline:
    1. **Ingest** - Download data from public APIs
    2. **Candidates** - Generate potential site locations
    3. **Features** - Engineer features for ML
    4. **Train** - Train ensemble ML models
    5. **PV Size** - Size solar arrays via PVWatts
    6. **Optimize** - Run MILP site selection
    """)
    
    config_file = st.text_input("Config file", value="configs/default.yaml")
    
    if st.button("▶️ Run Full Pipeline", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_area = st.empty()
        
        try:
            # Run the pipeline
            status_text.text("Starting pipeline...")
            
            process = subprocess.Popen(
                ["python", "cli.py", "run-all", "--config-path", config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            logs = []
            step = 0
            
            for line in iter(process.stdout.readline, ""):
                logs.append(line.strip())
                log_area.code("\n".join(logs[-20:]))  # Show last 20 lines
                
                # Update progress based on output
                if "Step" in line:
                    try:
                        step_num = int(line.split("/")[0].split()[-1])
                        progress_bar.progress(step_num / 6)
                        status_text.text(line.strip())
                    except:
                        pass
            
            process.wait()
            
            if process.returncode == 0:
                progress_bar.progress(100)
                st.success("✅ Pipeline completed successfully!")
                st.balloons()
            else:
                st.error(f"❌ Pipeline failed with return code {process.returncode}")
                
        except Exception as e:
            st.error(f"Error running pipeline: {e}")

with tab2:
    st.markdown("Run individual pipeline steps:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 1. Ingest Data"):
            with st.spinner("Ingesting data..."):
                result = subprocess.run(
                    ["python", "cli.py", "ingest-remote"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Data ingestion complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")
        
        if st.button("🏗️ 2. Build Candidates"):
            with st.spinner("Building candidates..."):
                result = subprocess.run(
                    ["python", "cli.py", "make-candidates"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Candidates built!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")
        
        if st.button("⚙️ 3. Engineer Features"):
            with st.spinner("Engineering features..."):
                result = subprocess.run(
                    ["python", "cli.py", "features"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Features engineered!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")
    
    with col2:
        if st.button("🧠 4a. Train ML Models"):
            with st.spinner("Training models..."):
                result = subprocess.run(
                    ["python", "cli.py", "train", "--save-shap", "--retrain"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("ML training complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")

        if st.button("🔮 4b. Predict (use trained models)"):
            with st.spinner("Running predictions..."):
                result = subprocess.run(
                    ["python", "cli.py", "predict"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Predictions complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")
        
        if st.button("☀️ 5. Size PV Systems"):
            with st.spinner("Sizing PV systems..."):
                result = subprocess.run(
                    ["python", "cli.py", "pvsize"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("PV sizing complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")
        
        if st.button("📊 6. Run Optimization"):
            with st.spinner("Running optimization..."):
                result = subprocess.run(
                    ["python", "cli.py", "optimize"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Optimization complete!")
                    st.code(result.stdout)
                else:
                    st.error(f"Failed: {result.stderr}")

# Clear data option
st.markdown("---")
st.subheader("Data Management")

col1, col2 = st.columns(2)

with col1:
    if st.button("🗑️ Clear Processed Data"):
        import shutil
        if processed_path.exists():
            shutil.rmtree(processed_path)
            processed_path.mkdir(parents=True)
        if artifacts_path.exists():
            shutil.rmtree(artifacts_path)
            artifacts_path.mkdir(parents=True)
        st.success("Processed data cleared!")
        st.rerun()

with col2:
    if st.button("🗑️ Clear All Data"):
        import shutil
        for path in [interim_path, processed_path, artifacts_path]:
            if path.exists():
                shutil.rmtree(path)
                path.mkdir(parents=True)
        st.success("All data cleared!")
        st.rerun()

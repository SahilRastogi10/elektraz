# app/pages/2_Configuration.py
"""Configuration page for adjusting optimization parameters."""

import streamlit as st
import yaml
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Configuration", page_icon="⚙️", layout="wide")

st.title("⚙️ Configuration")
st.markdown("Adjust optimization parameters, costs, and weights.")

# Load current config
config_path = Path("configs/default.yaml")
if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f)
else:
    st.error("Configuration file not found!")
    st.stop()

# Initialize session state
if "config" not in st.session_state:
    st.session_state.config = config.copy()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💰 Costs", "⚖️ Weights", "🔧 Optimization", "☀️ PV System", "🔌 Solver"])

with tab1:
    st.subheader("Cost Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Capital Costs")
        site_prep = st.number_input("Site Preparation ($)", value=50000, step=5000)
        civil_work = st.number_input("Civil Work ($)", value=75000, step=5000)
        interconnection = st.number_input("Interconnection Base ($)", value=100000, step=10000)
        charger_per_port = st.number_input("Charger per Port ($)", value=65000, step=5000)
        pv_per_kw = st.number_input("PV System ($/kW)", value=1600, step=100)
        storage_per_kwh = st.number_input("Battery Storage ($/kWh)", value=600, step=50)
    
    with col2:
        st.markdown("#### Operating Costs")
        electricity = st.number_input("Electricity ($/kWh)", value=0.12, step=0.01, format="%.3f")
        demand_charge = st.number_input("Demand Charge ($/kW/mo)", value=15.0, step=1.0)
        maintenance_pct = st.number_input("Maintenance (% of CapEx)", value=2.0, step=0.5)
        land_lease = st.number_input("Annual Land Lease ($)", value=12000, step=1000)
        
        st.markdown("#### Revenue")
        charging_price = st.number_input("Charging Price ($/kWh)", value=0.35, step=0.05, format="%.2f")
        utilization = st.number_input("Utilization Rate (%)", value=15, step=5)
    
    # Store in session state
    st.session_state.cost_params = {
        "site_prep": site_prep,
        "civil_work": civil_work,
        "interconnection": interconnection,
        "charger_per_port": charger_per_port,
        "pv_per_kw": pv_per_kw,
        "storage_per_kwh": storage_per_kwh,
        "electricity": electricity,
        "demand_charge": demand_charge,
        "maintenance_pct": maintenance_pct,
        "land_lease": land_lease,
        "charging_price": charging_price,
        "utilization": utilization / 100
    }

with tab2:
    st.subheader("Optimization Weights")
    st.markdown("Adjust the relative importance of different objectives.")
    
    weights = config["opt"]["weights"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        w_util = st.slider("Utilization Weight", 0.0, 2.0, float(weights.get("util", 1.0)), 0.1,
                          help="Higher values prioritize high-demand sites")
        w_equity = st.slider("Equity Weight", 0.0, 2.0, float(weights.get("equity", 0.25)), 0.1,
                            help="Higher values prioritize underserved areas")
    
    with col2:
        w_safety = st.slider("Safety Penalty", 0.0, 2.0, float(weights.get("safety_penalty", 0.5)), 0.1,
                            help="Higher values penalize risky locations (floodplains)")
        w_grid = st.slider("Grid Conflict Penalty", 0.0, 2.0, float(weights.get("grid_penalty", 0.3)), 0.1,
                          help="Higher values penalize distance from grid infrastructure")
        w_cost = st.slider("Cost Weight", 0.0, 2.0, float(weights.get("npc_cost", 0.8)), 0.1,
                          help="Higher values prioritize lower cost sites")
    
    st.session_state.config["opt"]["weights"] = {
        "util": w_util,
        "equity": w_equity,
        "safety_penalty": w_safety,
        "grid_penalty": w_grid,
        "npc_cost": w_cost
    }
    
    # Visual representation
    st.markdown("#### Weight Distribution")
    import pandas as pd
    weight_df = pd.DataFrame({
        "Objective": ["Utilization", "Equity", "Safety", "Grid", "Cost"],
        "Weight": [w_util, w_equity, w_safety, w_grid, w_cost]
    })
    st.bar_chart(weight_df.set_index("Objective"))

with tab3:
    st.subheader("Optimization Constraints")
    
    opt = config["opt"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Budget & Sites")
        budget = st.number_input("Total Budget ($)", value=int(opt.get("budget_usd", 15000000)), 
                                step=1000000, format="%d")
        max_sites = st.number_input("Maximum Sites", value=int(opt.get("max_sites", 40)), 
                                   min_value=1, max_value=100)
        min_spacing = st.number_input("Minimum Spacing (km)", value=int(opt.get("min_spacing_km", 50)),
                                     min_value=1, max_value=200)
    
    with col2:
        st.markdown("#### Site Configuration")
        ports_min = st.number_input("Min Ports/Site", value=int(opt.get("ports_min", 4)), min_value=1)
        ports_max = st.number_input("Max Ports/Site", value=int(opt.get("ports_max", 8)), min_value=1)
        port_power = st.number_input("Port Power (kW)", value=int(opt.get("port_power_kw", 150)))
        
        st.markdown("#### PV & Storage Ranges")
        pv_min = st.number_input("Min PV (kW)", value=int(opt.get("pv_kw_min", 50)))
        pv_max = st.number_input("Max PV (kW)", value=int(opt.get("pv_kw_max", 300)))
        storage_min = st.number_input("Min Storage (kWh)", value=int(opt.get("storage_kwh_min", 0)))
        storage_max = st.number_input("Max Storage (kWh)", value=int(opt.get("storage_kwh_max", 500)))
    
    st.session_state.config["opt"].update({
        "budget_usd": budget,
        "max_sites": max_sites,
        "min_spacing_km": min_spacing,
        "ports_min": ports_min,
        "ports_max": ports_max,
        "port_power_kw": port_power,
        "pv_kw_min": pv_min,
        "pv_kw_max": pv_max,
        "storage_kwh_min": storage_min,
        "storage_kwh_max": storage_max
    })

with tab4:
    st.subheader("PV System Defaults")
    
    pv = config["pv"]["pvwatts_system_defaults"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        module_type = st.selectbox("Module Type", [0, 1, 2], 
                                  index=int(pv.get("module_type", 1)),
                                  format_func=lambda x: ["Standard", "Premium", "Thin Film"][x])
        array_type = st.selectbox("Array Type", [0, 1, 2, 3, 4],
                                 index=int(pv.get("array_type", 2)),
                                 format_func=lambda x: ["Fixed Ground", "Fixed Roof", "1-Axis", "1-Axis Backtrack", "2-Axis"][x])
        losses = st.number_input("System Losses (%)", value=int(pv.get("losses", 14)), min_value=0, max_value=50)
    
    with col2:
        tilt = st.number_input("Tilt Angle (°)", value=int(pv.get("tilt", 15)), min_value=0, max_value=90)
        azimuth = st.number_input("Azimuth (°)", value=int(pv.get("azimuth", 180)), min_value=0, max_value=360)
        target_frac = st.slider("PV Sizing Target (%)", 0, 100, 
                               int(config["pv"].get("pv_sizing_target_fraction", 0.6) * 100))
    
    st.session_state.config["pv"]["pvwatts_system_defaults"] = {
        "module_type": module_type,
        "array_type": array_type,
        "losses": losses,
        "tilt": tilt,
        "azimuth": azimuth
    }
    st.session_state.config["pv"]["pv_sizing_target_fraction"] = target_frac / 100

with tab5:
    st.subheader("Solver Settings")
    
    solver = config["solver"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        solver_name = st.selectbox("Solver", ["highs", "cbc"], 
                                  index=0 if solver.get("name", "highs") == "highs" else 1)
        time_limit = st.number_input("Time Limit (seconds)", value=int(solver.get("time_limit_s", 600)),
                                    min_value=60, max_value=3600)
    
    with col2:
        mip_gap = st.number_input("MIP Gap (%)", value=float(solver.get("mip_gap", 0.01)) * 100,
                                 min_value=0.1, max_value=10.0, step=0.1)
    
    st.session_state.config["solver"] = {
        "name": solver_name,
        "time_limit_s": time_limit,
        "mip_gap": mip_gap / 100
    }

# Save configuration
st.markdown("---")
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("💾 Save Configuration", type="primary"):
        # Save to file
        with open(config_path, "w") as f:
            yaml.dump(st.session_state.config, f, default_flow_style=False)
        st.success("Configuration saved!")

with col2:
    if st.button("🔄 Reset to Defaults"):
        st.session_state.config = config.copy()
        st.rerun()

with col3:
    # Download config
    config_yaml = yaml.dump(st.session_state.config, default_flow_style=False)
    st.download_button("📥 Download", config_yaml, "config.yaml", "text/yaml")

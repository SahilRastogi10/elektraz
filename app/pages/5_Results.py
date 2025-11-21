# app/pages/5_Results.py
"""Results dashboard and reports."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.economics.costs import aggregate_portfolio_economics, CostParameters

st.set_page_config(page_title="Results", page_icon="📈", layout="wide")

st.title("📈 Optimization Results")
st.markdown("View selected sites, economics, and generate reports.")

# Load results
artifacts_path = Path("artifacts/reports")
selected_path = artifacts_path / "selected_sites.parquet"

if not selected_path.exists():
    st.warning("No optimization results found. Run the optimization first.")
    st.page_link("pages/4_Run_Optimization.py", label="Go to Run Optimization", icon="🚀")
    st.stop()

selected = gpd.read_parquet(selected_path)

# Calculate economics if not present
if "net_capex" not in selected.columns:
    st.info("Calculating economics...")
    params = CostParameters()
    econ = aggregate_portfolio_economics(selected, params)
    selected = selected.merge(
        econ["sites"][["cand_id", "total_capex", "net_capex", "annual_opex", "annual_revenue", "npv", "roi_pct", "payback_years"]],
        on="cand_id", how="left"
    )
    portfolio = econ["portfolio"]
else:
    # Recalculate portfolio totals
    portfolio = {
        "num_sites": len(selected),
        "total_capex": selected.get("total_capex", pd.Series(0)).sum(),
        "total_net_capex": selected.get("net_capex", pd.Series(0)).sum(),
        "total_annual_opex": selected.get("annual_opex", pd.Series(0)).sum(),
        "total_annual_revenue": selected.get("annual_revenue", pd.Series(0)).sum(),
        "total_ports": int(selected["ports"].sum()) if "ports" in selected.columns else 0,
    }
    portfolio["npv"] = selected.get("npv", pd.Series(0)).sum()

# Portfolio Summary
st.subheader("Portfolio Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Selected Sites", portfolio["num_sites"])
    st.metric("Total Ports", portfolio["total_ports"])

with col2:
    st.metric("Total CapEx", f"${portfolio['total_capex']:,.0f}")
    st.metric("Net CapEx", f"${portfolio['total_net_capex']:,.0f}")

with col3:
    st.metric("Annual OpEx", f"${portfolio['total_annual_opex']:,.0f}")
    st.metric("Annual Revenue", f"${portfolio['total_annual_revenue']:,.0f}")

with col4:
    st.metric("Portfolio NPV", f"${portfolio['npv']:,.0f}")
    annual_net = portfolio['total_annual_revenue'] - portfolio['total_annual_opex']
    payback = portfolio['total_net_capex'] / annual_net if annual_net > 0 else float('inf')
    st.metric("Payback Period", f"{payback:.1f} years" if payback < 100 else "N/A")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Site Details", "💰 Economics", "📊 Analysis", "📄 Report"])

with tab1:
    st.subheader("Selected Sites")
    
    # Display columns
    display_cols = ["cand_id", "ports", "pv_kw", "storage_kwh", "pred_daily_kwh"]
    if "pv_kw_sized" in selected.columns and "pv_kw" not in selected.columns:
        display_cols = ["cand_id", "ports", "pv_kw_sized", "storage_kwh", "pred_daily_kwh"]
    
    available_cols = [c for c in display_cols if c in selected.columns]
    if "net_capex" in selected.columns:
        available_cols.extend(["net_capex", "npv"])
    
    st.dataframe(
        selected[available_cols].round(2),
        use_container_width=True,
        hide_index=True
    )
    
    # Download
    csv = selected.drop(columns=["geometry"], errors="ignore").to_csv(index=False)
    st.download_button("📥 Download CSV", csv, "selected_sites.csv", "text/csv")

with tab2:
    st.subheader("Site Economics")
    
    if "net_capex" in selected.columns:
        # Economics breakdown
        econ_cols = ["cand_id", "total_capex", "net_capex", "annual_opex", "annual_revenue", "npv", "roi_pct"]
        econ_cols = [c for c in econ_cols if c in selected.columns]
        
        st.dataframe(
            selected[econ_cols].round(2),
            use_container_width=True,
            hide_index=True
        )
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**CapEx Distribution**")
            capex_data = selected[["cand_id", "net_capex"]].set_index("cand_id")
            st.bar_chart(capex_data)
        
        with col2:
            st.markdown("**NPV by Site**")
            if "npv" in selected.columns:
                npv_data = selected[["cand_id", "npv"]].set_index("cand_id")
                st.bar_chart(npv_data)
    else:
        st.info("Run optimization with economics enabled to see detailed breakdown.")

with tab3:
    st.subheader("Configuration Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Port Distribution**")
        if "ports" in selected.columns:
            port_dist = selected["ports"].value_counts().sort_index()
            st.bar_chart(port_dist)
        
        st.markdown("**PV System Sizes**")
        pv_col = "pv_kw" if "pv_kw" in selected.columns else "pv_kw_sized"
        if pv_col in selected.columns:
            st.bar_chart(selected[[pv_col]].sort_values(pv_col))
    
    with col2:
        st.markdown("**Storage Capacity**")
        if "storage_kwh" in selected.columns:
            st.bar_chart(selected[["storage_kwh"]].sort_values("storage_kwh"))
        
        st.markdown("**Predicted Daily Demand**")
        if "pred_daily_kwh" in selected.columns:
            st.line_chart(selected["pred_daily_kwh"].sort_values().reset_index(drop=True))
    
    # Coverage metrics
    st.markdown("---")
    st.markdown("#### Coverage Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_kw = portfolio["total_ports"] * 150
        st.metric("Total Charging Capacity", f"{total_kw:,} kW")
    
    with col2:
        if "pred_daily_kwh" in selected.columns:
            total_daily = selected["pred_daily_kwh"].sum()
            st.metric("Total Daily Demand (pred)", f"{total_daily:,.0f} kWh")
    
    with col3:
        pv_col = "pv_kw" if "pv_kw" in selected.columns else "pv_kw_sized"
        if pv_col in selected.columns:
            total_pv = selected[pv_col].sum()
            st.metric("Total PV Capacity", f"{total_pv:,.0f} kW")

with tab4:
    st.subheader("Generate Report")
    
    st.markdown("Generate a comprehensive PDF report of the optimization results.")
    
    report_title = st.text_input("Report Title", "Arizona Solar EV Charging Station Optimization")
    include_map = st.checkbox("Include Map", value=True)
    include_economics = st.checkbox("Include Economics", value=True)
    
    if st.button("📄 Generate PDF Report"):
        try:
            from fpdf import FPDF
            
            pdf = FPDF()
            pdf.add_page()
            
            # Title
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, report_title, ln=True, align="C")
            pdf.ln(10)
            
            # Summary
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Portfolio Summary", ln=True)
            pdf.set_font("Arial", "", 10)
            
            pdf.cell(0, 6, f"Total Sites: {portfolio['num_sites']}", ln=True)
            pdf.cell(0, 6, f"Total Ports: {portfolio['total_ports']}", ln=True)
            pdf.cell(0, 6, f"Total CapEx: ${portfolio['total_capex']:,.0f}", ln=True)
            pdf.cell(0, 6, f"Net CapEx: ${portfolio['total_net_capex']:,.0f}", ln=True)
            pdf.cell(0, 6, f"Portfolio NPV: ${portfolio['npv']:,.0f}", ln=True)
            pdf.ln(10)
            
            # Sites table
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Selected Sites", ln=True)
            pdf.set_font("Arial", "", 8)
            
            for idx, row in selected.iterrows():
                line = f"Site {row.get('cand_id', idx)}: {row.get('ports', 'N/A')} ports, "
                pv = row.get('pv_kw', row.get('pv_kw_sized', 0))
                line += f"{pv:.0f} kW PV"
                if "net_capex" in row:
                    line += f", ${row['net_capex']:,.0f} CapEx"
                pdf.cell(0, 5, line, ln=True)
            
            # Save
            report_path = artifacts_path / "optimization_report.pdf"
            pdf.output(str(report_path))
            
            with open(report_path, "rb") as f:
                st.download_button(
                    "📥 Download Report",
                    f.read(),
                    "optimization_report.pdf",
                    "application/pdf"
                )
            
            st.success("Report generated successfully!")
            
        except ImportError:
            st.error("FPDF not installed. Install with: pip install fpdf2")
        except Exception as e:
            st.error(f"Error generating report: {e}")

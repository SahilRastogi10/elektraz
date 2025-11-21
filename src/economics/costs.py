# src/economics/costs.py
"""Economic modeling for EV charging stations."""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class CostParameters:
    """Cost parameters for station economics."""
    # Capital costs
    site_prep_usd: float = 50000
    civil_work_usd: float = 75000
    interconnection_base_usd: float = 100000
    transformer_usd_per_kw: float = 50
    charger_usd_per_port: float = 65000
    pv_usd_per_kw: float = 1600
    storage_usd_per_kwh: float = 600
    
    # Operating costs (annual)
    maintenance_pct: float = 0.02  # % of capex
    insurance_pct: float = 0.005
    land_lease_annual: float = 12000
    network_fee_annual: float = 2400
    
    # Energy costs
    electricity_usd_per_kwh: float = 0.12
    demand_charge_usd_per_kw: float = 15
    
    # Revenue assumptions
    charging_price_usd_per_kwh: float = 0.35
    utilization_rate: float = 0.15  # 15% average
    
    # Financial parameters
    discount_rate: float = 0.08
    project_lifetime_years: int = 15
    
    # Incentives
    federal_itc_pct: float = 0.30  # 30% ITC for solar
    nevi_grant_pct: float = 0.80  # 80% NEVI coverage


def calculate_site_capex(
    ports: int,
    pv_kw: float,
    storage_kwh: float,
    port_power_kw: float = 150,
    params: Optional[CostParameters] = None
) -> Dict[str, float]:
    """Calculate capital expenditure breakdown for a site."""
    if params is None:
        params = CostParameters()
    
    total_power_kw = ports * port_power_kw
    
    costs = {
        "site_prep": params.site_prep_usd,
        "civil_work": params.civil_work_usd,
        "interconnection": params.interconnection_base_usd + params.transformer_usd_per_kw * total_power_kw,
        "chargers": ports * params.charger_usd_per_port,
        "pv_system": pv_kw * params.pv_usd_per_kw,
        "storage": storage_kwh * params.storage_usd_per_kwh,
    }
    
    costs["total_capex"] = sum(costs.values())
    
    # Apply incentives
    costs["federal_itc"] = -costs["pv_system"] * params.federal_itc_pct
    costs["nevi_grant"] = -min(costs["total_capex"] * params.nevi_grant_pct, 1000000)  # Cap at $1M
    costs["net_capex"] = costs["total_capex"] + costs["federal_itc"] + costs["nevi_grant"]
    
    return costs


def calculate_annual_opex(
    capex: float,
    annual_energy_kwh: float,
    peak_demand_kw: float,
    pv_generation_kwh: float = 0,
    storage_mitigation_kw: float = 0,
    params: Optional[CostParameters] = None
) -> Dict[str, float]:
    """Calculate annual operating expenditure breakdown."""
    if params is None:
        params = CostParameters()
    
    # Net energy from grid
    net_grid_energy = max(0, annual_energy_kwh - pv_generation_kwh)
    net_peak_demand = max(0, peak_demand_kw - storage_mitigation_kw)
    
    costs = {
        "maintenance": capex * params.maintenance_pct,
        "insurance": capex * params.insurance_pct,
        "land_lease": params.land_lease_annual,
        "network_fees": params.network_fee_annual,
        "electricity": net_grid_energy * params.electricity_usd_per_kwh,
        "demand_charges": net_peak_demand * params.demand_charge_usd_per_kw * 12,
    }
    
    costs["total_opex"] = sum(costs.values())
    
    return costs


def calculate_annual_revenue(
    annual_energy_kwh: float,
    utilization_rate: float = 0.15,
    params: Optional[CostParameters] = None
) -> Dict[str, float]:
    """Calculate annual revenue from charging."""
    if params is None:
        params = CostParameters()
    
    # Actual dispensed energy based on utilization
    dispensed_kwh = annual_energy_kwh * utilization_rate / params.utilization_rate
    
    revenue = {
        "charging_revenue": dispensed_kwh * params.charging_price_usd_per_kwh,
        "dispensed_kwh": dispensed_kwh,
    }
    
    return revenue


def calculate_npc(
    capex_breakdown: Dict[str, float],
    annual_opex: float,
    annual_revenue: float,
    params: Optional[CostParameters] = None
) -> Dict[str, float]:
    """Calculate Net Present Cost over project lifetime."""
    if params is None:
        params = CostParameters()
    
    r = params.discount_rate
    n = params.project_lifetime_years
    
    # Present value factor for annuity
    pvf = (1 - (1 + r) ** -n) / r
    
    # Net annual cash flow (negative = cost)
    annual_net = annual_revenue - annual_opex
    
    # NPV calculation
    pv_capex = capex_breakdown["net_capex"]
    pv_operations = annual_net * pvf
    npv = -pv_capex + pv_operations
    
    # Simple payback
    if annual_net > 0:
        simple_payback = capex_breakdown["net_capex"] / annual_net
    else:
        simple_payback = float("inf")
    
    # Levelized cost of charging (LCOC)
    total_dispensed = capex_breakdown.get("annual_kwh", 100000) * n
    if total_dispensed > 0:
        lcoc = (pv_capex + annual_opex * pvf) / (total_dispensed * pvf / n)
    else:
        lcoc = 0
    
    return {
        "npv": npv,
        "npc": pv_capex + annual_opex * pvf,
        "simple_payback_years": simple_payback,
        "lcoc_usd_per_kwh": lcoc,
        "annual_net_cash_flow": annual_net,
        "roi_pct": (annual_net / capex_breakdown["net_capex"] * 100) if capex_breakdown["net_capex"] > 0 else 0,
    }


def calculate_full_economics(
    ports: int,
    pv_kw: float,
    storage_kwh: float,
    pred_daily_kwh: float,
    pv_annual_kwh: float = 0,
    port_power_kw: float = 150,
    params: Optional[CostParameters] = None
) -> Dict[str, any]:
    """Calculate complete economic analysis for a site."""
    if params is None:
        params = CostParameters()
    
    # Annual energy demand
    annual_energy_kwh = pred_daily_kwh * 365
    
    # Peak demand (assume 70% simultaneity factor)
    peak_demand_kw = ports * port_power_kw * 0.7
    
    # Storage mitigation (simplified)
    storage_mitigation_kw = min(storage_kwh * 0.5, peak_demand_kw * 0.3)
    
    # Calculate components
    capex = calculate_site_capex(ports, pv_kw, storage_kwh, port_power_kw, params)
    capex["annual_kwh"] = annual_energy_kwh
    
    opex = calculate_annual_opex(
        capex["total_capex"], annual_energy_kwh, peak_demand_kw,
        pv_annual_kwh, storage_mitigation_kw, params
    )
    
    revenue = calculate_annual_revenue(annual_energy_kwh, params.utilization_rate, params)
    
    financials = calculate_npc(capex, opex["total_opex"], revenue["charging_revenue"], params)
    
    return {
        "capex": capex,
        "annual_opex": opex,
        "annual_revenue": revenue,
        "financials": financials,
        "summary": {
            "total_capex": capex["total_capex"],
            "net_capex": capex["net_capex"],
            "annual_opex": opex["total_opex"],
            "annual_revenue": revenue["charging_revenue"],
            "npv": financials["npv"],
            "payback_years": financials["simple_payback_years"],
            "roi_pct": financials["roi_pct"],
        }
    }


def aggregate_portfolio_economics(sites_df: pd.DataFrame, params: Optional[CostParameters] = None) -> Dict:
    """Aggregate economics across all selected sites."""
    if params is None:
        params = CostParameters()
    
    total_capex = 0
    total_net_capex = 0
    total_annual_opex = 0
    total_annual_revenue = 0
    site_economics = []
    
    for idx, row in sites_df.iterrows():
        econ = calculate_full_economics(
            ports=int(row.get("ports", 4)),
            pv_kw=float(row.get("pv_kw", 100)),
            storage_kwh=float(row.get("storage_kwh", 0)),
            pred_daily_kwh=float(row.get("pred_daily_kwh", 100)),
            pv_annual_kwh=float(row.get("pv_annual_kwh", 0)),
            params=params
        )
        
        site_economics.append({
            "cand_id": row.get("cand_id", idx),
            **econ["summary"]
        })
        
        total_capex += econ["summary"]["total_capex"]
        total_net_capex += econ["summary"]["net_capex"]
        total_annual_opex += econ["summary"]["annual_opex"]
        total_annual_revenue += econ["summary"]["annual_revenue"]
    
    # Portfolio financials
    annual_net = total_annual_revenue - total_annual_opex
    r = params.discount_rate
    n = params.project_lifetime_years
    pvf = (1 - (1 + r) ** -n) / r
    
    return {
        "sites": pd.DataFrame(site_economics),
        "portfolio": {
            "total_capex": total_capex,
            "total_net_capex": total_net_capex,
            "total_annual_opex": total_annual_opex,
            "total_annual_revenue": total_annual_revenue,
            "annual_net_cash_flow": annual_net,
            "npv": -total_net_capex + annual_net * pvf,
            "simple_payback_years": total_net_capex / annual_net if annual_net > 0 else float("inf"),
            "num_sites": len(sites_df),
            "total_ports": int(sites_df["ports"].sum()) if "ports" in sites_df.columns else 0,
        }
    }

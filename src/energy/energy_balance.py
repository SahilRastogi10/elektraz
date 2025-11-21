# src/energy/energy_balance.py
"""Energy balance and load profile modeling."""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


def annual_station_energy_kwh(pred_daily_kwh: float) -> float:
    """Calculate annual energy demand from daily prediction."""
    return float(pred_daily_kwh) * 365.0


def demand_charge_mitigation_kw(storage_kwh: float, c_rate: float = 0.5, 
                                 peak_window_h: float = 2.0) -> float:
    """Estimate battery dispatch capability for peak shaving."""
    return min(storage_kwh / peak_window_h, c_rate * storage_kwh)


def monthly_load_profile(annual_kwh: float, profile_type: str = "arizona") -> np.ndarray:
    """Generate monthly load profile based on location."""
    if profile_type == "arizona":
        # Arizona: higher summer demand due to AC load correlation
        monthly_factors = np.array([
            0.07, 0.07, 0.08, 0.08, 0.09, 0.10,
            0.11, 0.11, 0.10, 0.08, 0.07, 0.07
        ])
    else:
        # Flat profile
        monthly_factors = np.ones(12) / 12
    
    return annual_kwh * monthly_factors


def hourly_load_profile(daily_kwh: float, profile_type: str = "ev_charging") -> np.ndarray:
    """Generate hourly load profile for a typical day."""
    if profile_type == "ev_charging":
        # Typical EV charging pattern: morning and evening peaks
        hourly_factors = np.array([
            0.02, 0.02, 0.02, 0.02, 0.02, 0.03,  # 0-5
            0.04, 0.06, 0.07, 0.06, 0.05, 0.05,  # 6-11
            0.05, 0.05, 0.05, 0.05, 0.06, 0.07,  # 12-17
            0.08, 0.07, 0.05, 0.04, 0.03, 0.02   # 18-23
        ])
    else:
        # Flat profile
        hourly_factors = np.ones(24) / 24
    
    return daily_kwh * hourly_factors


def calculate_peak_demand(daily_kwh: float, ports: int, 
                          port_power_kw: float = 150) -> float:
    """Calculate peak demand considering simultaneity."""
    # Estimate based on load profile
    hourly = hourly_load_profile(daily_kwh)
    peak_hourly_kwh = hourly.max()
    
    # Convert to kW (assuming 1-hour resolution)
    peak_kw_from_load = peak_hourly_kwh
    
    # Also consider hardware capacity with simultaneity
    simultaneity_factor = 0.6 + 0.1 * min(ports, 4)  # 0.7 for 4+ ports
    peak_kw_from_hardware = ports * port_power_kw * simultaneity_factor
    
    return min(peak_kw_from_load, peak_kw_from_hardware)


def solar_load_match_score(
    monthly_pv_kwh: np.ndarray,
    monthly_load_kwh: np.ndarray
) -> Dict[str, float]:
    """Calculate how well solar generation matches load profile."""
    if len(monthly_pv_kwh) != 12 or len(monthly_load_kwh) != 12:
        return {"match_score": 0, "excess_ratio": 0, "deficit_ratio": 0}
    
    # Monthly balance
    monthly_balance = monthly_pv_kwh - monthly_load_kwh
    
    excess = np.maximum(monthly_balance, 0).sum()
    deficit = np.maximum(-monthly_balance, 0).sum()
    
    total_load = monthly_load_kwh.sum()
    total_pv = monthly_pv_kwh.sum()
    
    # Match score (0-1): how much of load is directly served by PV
    direct_use = np.minimum(monthly_pv_kwh, monthly_load_kwh).sum()
    match_score = direct_use / total_load if total_load > 0 else 0
    
    return {
        "match_score": match_score,
        "excess_ratio": excess / total_pv if total_pv > 0 else 0,
        "deficit_ratio": deficit / total_load if total_load > 0 else 0,
        "self_consumption_pct": (1 - excess / total_pv) * 100 if total_pv > 0 else 0,
        "solar_fraction_pct": direct_use / total_load * 100 if total_load > 0 else 0,
    }


def thermal_derating_factor(ambient_temp_c: float, 
                            equipment_type: str = "inverter") -> float:
    """Calculate thermal derating factor for hot climate."""
    if equipment_type == "inverter":
        # Inverters derate above 45C
        if ambient_temp_c <= 45:
            return 1.0
        elif ambient_temp_c <= 55:
            return 1.0 - (ambient_temp_c - 45) * 0.02
        else:
            return 0.8
    elif equipment_type == "battery":
        # Batteries derate at high temps
        if ambient_temp_c <= 35:
            return 1.0
        elif ambient_temp_c <= 45:
            return 1.0 - (ambient_temp_c - 35) * 0.01
        else:
            return 0.9
    elif equipment_type == "charger":
        # DC fast chargers may derate
        if ambient_temp_c <= 40:
            return 1.0
        elif ambient_temp_c <= 50:
            return 1.0 - (ambient_temp_c - 40) * 0.015
        else:
            return 0.85
    return 1.0


def arizona_summer_derating(pv_kw: float, storage_kwh: float, 
                            port_power_kw: float = 150) -> Dict[str, float]:
    """Calculate Arizona summer derating factors."""
    # Phoenix summer peak: ~43C average high
    summer_temp = 43
    
    return {
        "pv_derating": thermal_derating_factor(summer_temp + 10, "inverter"),  # Module temp higher
        "storage_derating": thermal_derating_factor(summer_temp, "battery"),
        "charger_derating": thermal_derating_factor(summer_temp, "charger"),
        "effective_pv_kw": pv_kw * thermal_derating_factor(summer_temp + 10, "inverter"),
        "effective_storage_kwh": storage_kwh * thermal_derating_factor(summer_temp, "battery"),
    }


def calculate_grid_impact(
    annual_load_kwh: float,
    annual_pv_kwh: float,
    peak_demand_kw: float,
    storage_mitigation_kw: float = 0
) -> Dict[str, float]:
    """Calculate grid impact metrics."""
    net_grid_kwh = max(0, annual_load_kwh - annual_pv_kwh)
    net_peak_kw = max(0, peak_demand_kw - storage_mitigation_kw)
    
    return {
        "grid_energy_kwh": net_grid_kwh,
        "grid_energy_pct": net_grid_kwh / annual_load_kwh * 100 if annual_load_kwh > 0 else 0,
        "net_peak_kw": net_peak_kw,
        "peak_reduction_pct": (peak_demand_kw - net_peak_kw) / peak_demand_kw * 100 if peak_demand_kw > 0 else 0,
        "pv_offset_pct": (annual_load_kwh - net_grid_kwh) / annual_load_kwh * 100 if annual_load_kwh > 0 else 0,
    }

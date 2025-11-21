import pandas as pd, numpy as np

def annual_station_energy_kwh(pred_daily_kwh: float):
    return float(pred_daily_kwh)*365.0

def demand_charge_mitigation_kw(storage_kwh: float, c_rate=0.5, peak_window_h=2.0):
    # very rough proxy: usable kW shaved = min(storage_kwh/peak_window_h, c_rate*storage_kwh)
    return min(storage_kwh/peak_window_h, c_rate*storage_kwh)

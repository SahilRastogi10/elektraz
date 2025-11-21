import requests, pandas as pd
from src.common.config import AppSettings

def pvwatts_monthly(lat, lon, system_kw, params: dict):
    env = AppSettings()
    base = env.NREL_API_BASE
    url = f"{base}/api/pvwatts/v8.json"
    payload = {
        "api_key": env.NREL_API_KEY or "DEMO_KEY",
        "lat": lat, "lon": lon,
        "system_capacity": system_kw,
        "module_type": params.get("module_type", 1),
        "array_type": params.get("array_type", 2),
        "tilt": params.get("tilt", 15),
        "azimuth": params.get("azimuth", 180),
        "losses": params.get("losses", 14),
        "timeframe": "monthly"
    }
    r = requests.get(url, params=payload, timeout=60); r.raise_for_status()
    out = r.json()["outputs"]
    months = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
    return pd.Series({m: out["ac_monthly"][i] for i,m in enumerate(months)} | {"ac_annual":out["ac_annual"]})

def size_pv_for_fraction(annual_kwh_need: float, target_fraction: float, lat: float, lon: float, defaults: dict):
    # simple solver: start with 50 kW and scale up by ratio
    pv50 = pvwatts_monthly(lat, lon, 50, defaults)["ac_annual"]
    if pv50<=0: return 0.0
    needed_kwh = annual_kwh_need*target_fraction
    scale = needed_kwh / pv50
    return max(50.0, round(50.0*scale, 1))

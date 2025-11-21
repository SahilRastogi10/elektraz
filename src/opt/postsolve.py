import pandas as pd, numpy as np

def extract_solution(model, candidates: pd.DataFrame):
    open_ids = [i for i in model.I if model.open[i].value>0.5]
    out = candidates.loc[open_ids].copy()
    out["ports"] = [int(model.ports[i].value) for i in open_ids]
    out["pv_kw"] = [float(model.pv_kw[i].value) for i in open_ids]
    out["storage_kwh"] = [float(model.storage_kwh[i].value) for i in open_ids]
    return out

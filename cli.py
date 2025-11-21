# cli.py
import typer, os
from pathlib import Path
import pandas as pd, geopandas as gpd, numpy as np
from src.common.config import load_yaml, resolve_paths
from src.common.io import write_geoparquet, write_parquet
from src.utils.remote import read_arcgis_layer, get_afdc_az, get_acs_zcta, read_csv_zip

from src.data.build_candidates import candidates_from_sources
from src.features.engineer import engineer_features
from src.ml.tabular_sklearn import build_pipelines, cv_and_fit, predict_with_blend
from src.energy.pvwatts import size_pv_for_fraction
from src.opt.facility_milp import build_milp, solve_milp
from src.opt.postsolve import extract_solution

app = typer.Typer(help="AZ Solar EV Siting Toolkit (remote pulls)")

@app.command()
def ingest_remote(config_path: str="configs/default.yaml", year: int=2023):
    """
    Pull all base layers directly from the web and write to data/interim
    (no data/raw needed).
    """
    cfg = resolve_paths(load_yaml(config_path))
    d = cfg["data"]

    # AADT, NFHL, Park&Ride from ArcGIS
    adot_aadt = read_arcgis_layer(d["adot_aadt_url"])
    nfhl      = read_arcgis_layer(d["nfhl_url"])
    pr        = read_arcgis_layer(d["valley_metro_pr_url"])

    # AFDC from NREL
    afdc      = get_afdc_az()

    # ACS ZCTA (tabular)
    acs       = get_acs_zcta(year=year)

    # Optional: EJSCREEN CSV (statewide)
    ejscreen  = read_csv_zip(d["ejscreen_csv_zip"])

    # Persist to interim for reproducibility
    write_geoparquet(adot_aadt, "data/interim/adot_aadt.parquet")
    write_geoparquet(nfhl, "data/interim/nfhl.parquet")
    write_geoparquet(pr, "data/interim/park_ride.parquet")
    write_geoparquet(afdc, "data/interim/afdc_az.parquet")
    write_parquet(acs, "data/interim/acs_zcta.parquet")
    ejscreen.to_parquet("data/interim/ejscreen_state.parquet", index=False)

    typer.echo("Remote ingestion complete → data/interim/*.parquet")

@app.command()
def make_candidates(config_path: str="configs/default.yaml"):
    """
    Build candidate sites from remote-ingested interim layers.
    """
    adot_aadt = gpd.read_parquet("data/interim/adot_aadt.parquet")
    pr        = gpd.read_parquet("data/interim/park_ride.parquet")
    # If you have a separate rest areas layer, load similarly; else reuse P&R
    afc = None  # optional corridor layer if you add it later

    cand = candidates_from_sources(adot_roads=adot_aadt, aadt=adot_aadt, pr_sites=pr,
                                   rest_areas=pr, afc_corridors=adot_aadt)  # placeholder afc
    write_geoparquet(cand, "data/interim/candidates.parquet")
    typer.echo(f"Candidates: {len(cand)}")

@app.command()
def features():
    """
    Engineer features using interim layers (all originally fetched online).
    """
    cand = gpd.read_parquet("data/interim/candidates.parquet")
    afdc = gpd.read_parquet("data/interim/afdc_az.parquet")
    aadt = gpd.read_parquet("data/interim/adot_aadt.parquet")
    nfhl = gpd.read_parquet("data/interim/nfhl.parquet")

    F = engineer_features(cand, afdc, aadt, ejscreen_df=None, nfhl=nfhl)
    write_geoparquet(F, "data/processed/features.parquet")
    typer.echo("Features ready → data/processed/features.parquet")

@app.command()
def train():
    """
    Train tabular ML (blend) with proxy target; store predictions.
    """
    F = gpd.read_parquet("data/processed/features.parquet")
    # proxy label: distance * AADT density
    F["daily_kwh"] = (F["aadt_sum_1500m"].fillna(0)/1000.0) * (F["dist_m_nearest_dcfc"].fillna(5_000)/5_000)
    y = F["daily_kwh"].values

    num_cols = ["aadt_sum_500m","aadt_sum_1500m","aadt_sum_5000m","dist_m_nearest_dcfc"]
    X = F[num_cols].copy().fillna(0)
    pipes = build_pipelines(num_cols=num_cols, cat_cols=[])

    results, fitted = cv_and_fit(X, y, pipes, folds=5, seed=42)
    typer.echo(f"CV: {results}")

    F["pred_daily_kwh"] = predict_with_blend(fitted, X)
    write_geoparquet(F, "data/processed/features_scored.parquet")
    typer.echo("Scored features → data/processed/features_scored.parquet")

@app.command()
def pvsize(config_path: str="configs/default.yaml"):
    """
    Size PV per candidate to hit target fraction of annual station energy via PVWatts API.
    """
    cfg = load_yaml(config_path)
    defaults = cfg["pv"]["pvwatts_system_defaults"]
    frac = cfg["pv"]["pv_sizing_target_fraction"]

    F = gpd.read_parquet("data/processed/features_scored.parquet").to_crs(4326)
    pv_out = []
    for _,r in F.iterrows():
        pv_out.append(size_pv_for_fraction(
            annual_kwh_need=r["pred_daily_kwh"]*365,
            target_fraction=frac,
            lat=r.geometry.y, lon=r.geometry.x,
            defaults=defaults
        ))
    F["pv_kw_sized"] = pv_out
    F.to_crs(26912).to_parquet("data/processed/features_scored_pv.parquet", index=False)
    typer.echo("PV sizing complete → data/processed/features_scored_pv.parquet")

@app.command()
def optimize(config_path: str="configs/default.yaml"):
    """
    MILP siting optimization (Pyomo + HiGHS).
    """
    cfg = load_yaml(config_path)
    opt_cfg = cfg["opt"]
    F = gpd.read_parquet("data/processed/features_scored_pv.parquet").to_crs(26912)

    # Demand nodes proxy: use candidates themselves weighted by AADT
    demand = F[["cand_id","aadt_sum_1500m","geometry"]].copy()
    demand.rename(columns={"cand_id":"node_id","aadt_sum_1500m":"pop_weight"}, inplace=True)
    # distances (km)
    dist = np.zeros((len(F), len(demand)))
    for i, gi in enumerate(F.geometry):
        dist[i,:] = demand.distance(gi).values/1000.0

    # Scores & penalties
    pred = F["pred_daily_kwh"].fillna(0).values
    equity = np.zeros(len(F))  # plug EJ later if desired
    safety = (F.get("in_floodplain", pd.Series(False, index=F.index)).astype(int)).values
    gridpen = (F["dist_m_nearest_dcfc"].fillna(5000)/5000.0).clip(0,2).values

    # Costs (simple priors)
    site_capex = np.full(len(F), 250000.0)
    pv_capex_per_kw = 1600.0
    storage_capex_per_kwh = 600.0

    model = build_milp(
        cands=F.assign(x=F.geometry.x, y=F.geometry.y),
        demand_nodes=demand.reset_index(drop=True),
        dist_km=dist, pred_daily_kwh=pred, equity_score=equity,
        safety_penalty=safety, grid_penalty=gridpen,
        site_capex=site_capex,
        pv_capex_per_kw=pv_capex_per_kw,
        storage_capex_per_kwh=storage_capex_per_kwh,
        params=opt_cfg
    )
    res = solve_milp(model, solver_name="highs", time_limit_s=cfg["solver"]["time_limit_s"], mip_gap=cfg["solver"]["mip_gap"])
    selected = extract_solution(model, F)
    selected.to_parquet("artifacts/reports/selected_sites.parquet", index=False)
    typer.echo(f"Solved. Selected sites: {len(selected)} → artifacts/reports/selected_sites.parquet")

if __name__ == "__main__":
    app()

# cli.py
"""CLI for AZ Solar EV Siting Toolkit with automatic data loading."""

import typer
import os
from pathlib import Path
import pandas as pd
import geopandas as gpd
import numpy as np

from src.common.config import load_yaml, resolve_paths
from src.common.io import write_geoparquet, write_parquet
from src.data.dataloader import DataLoader, get_dataloader
from src.data.build_candidates import candidates_from_sources
from src.features.engineer import engineer_features
from src.ml.tabular_sklearn import build_pipelines, cv_and_fit, predict_with_blend, compute_shap_values, save_models, load_models
from src.energy.pvwatts import size_pv_for_fraction
from src.opt.facility_milp import build_milp, solve_milp
from src.opt.postsolve import extract_solution
from src.economics.costs import aggregate_portfolio_economics, CostParameters

app = typer.Typer(help="AZ Solar EV Siting Toolkit")


@app.command()
def load_data(
    config_path: str = "configs/default.yaml",
    force_refresh: bool = False,
    source: str = None
):
    """Load data from configured sources (uses caching by default)."""
    loader = get_dataloader(config_path)
    
    if source:
        typer.echo(f"Loading {source}...")
        data = loader.load(source, force_refresh=force_refresh)
        if data is not None:
            typer.echo(f"  Loaded {len(data)} records")
    else:
        typer.echo("Loading all data sources...")
        results = loader.load_all(force_refresh=force_refresh)
        for name, data in results.items():
            if data is not None:
                typer.echo(f"  {name}: {len(data)} records")
            else:
                typer.echo(f"  {name}: failed or skipped")
    
    # Show status
    typer.echo("\nData Status:")
    status = loader.get_status()
    typer.echo(status.to_string(index=False))


@app.command()
def make_candidates(config_path: str = "configs/default.yaml"):
    """Build candidate sites from loaded data."""
    loader = get_dataloader(config_path)

    # Load required data
    adot_aadt = loader.load("adot_aadt")
    pr = loader.load("park_ride")

    if adot_aadt is None:
        typer.echo("Required AADT data not available. Run 'load-data' first.")
        raise typer.Exit(1)

    # Create empty GeoDataFrame if park_ride not available (it's optional)
    if pr is None:
        typer.echo("Warning: Park & Ride data not available, continuing with AADT only")
        pr = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    
    cand = candidates_from_sources(
        adot_roads=adot_aadt, aadt=adot_aadt, pr_sites=pr,
        rest_areas=pr, afc_corridors=adot_aadt
    )
    
    Path("data/interim").mkdir(parents=True, exist_ok=True)
    write_geoparquet(cand, "data/interim/candidates.parquet")
    typer.echo(f"Candidates: {len(cand)} -> data/interim/candidates.parquet")


@app.command()
def features(config_path: str = "configs/default.yaml"):
    """Engineer features using loaded data."""
    loader = get_dataloader(config_path)

    # Load data
    cand = gpd.read_parquet("data/interim/candidates.parquet")
    afdc = loader.load("afdc_az")
    aadt = loader.load("adot_aadt")
    nfhl = loader.load("nfhl")

    # Report on optional data availability
    if nfhl is None:
        typer.echo("Warning: NFHL flood data not available, continuing without flood features")

    F = engineer_features(cand, afdc, aadt, nfhl=nfhl)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    write_geoparquet(F, "data/processed/features.parquet")
    typer.echo(f"Features: {len(F)} candidates -> data/processed/features.parquet")


@app.command()
def train(
    save_shap: bool = False,
    retrain: bool = False
):
    """Train ML models with proxy target."""
    models_path = Path("artifacts/models")
    
    # Check if models exist
    if models_path.exists() and (models_path / "ensemble.joblib").exists() and not retrain:
        typer.echo("Models already trained. Use --retrain to force retraining.")
        return
    
    F = gpd.read_parquet("data/processed/features.parquet")
    
    # Proxy label
    F["daily_kwh"] = (
        F["aadt_sum_1500m"].fillna(0) / 1000.0
    ) * (
        F["dist_m_nearest_dcfc"].fillna(5000) / 5000
    )
    F["daily_kwh"] = F["daily_kwh"].clip(10, 500)
    y = F["daily_kwh"].values
    
    # Use all available numeric features for better predictions
    all_num_cols = [
        "aadt_sum_500m", "aadt_sum_1500m", "aadt_sum_5000m",
        "dist_m_nearest_dcfc", "dist_m_nearest_station",
        "equity_score", "safety_score", "grid_conflict_score",
        "accessibility_score", "x", "y"
    ]
    # Filter to only columns that exist in the dataframe
    num_cols = [c for c in all_num_cols if c in F.columns]
    typer.echo(f"Training with {len(num_cols)} features: {num_cols}")

    X = F[num_cols].copy().fillna(0)

    # Save feature names for inference
    models_path.mkdir(parents=True, exist_ok=True)
    pd.Series(num_cols).to_json(models_path / "feature_cols.json")

    pipes = build_pipelines(num_cols=num_cols, cat_cols=[])
    results, fitted = cv_and_fit(X, y, pipes, folds=5, seed=42)
    
    for name, res in results.items():
        typer.echo(f"{name}: RMSE={res['rmse_mean']:.2f} +/- {res['rmse_std']:.2f}")
    
    F["pred_daily_kwh"] = predict_with_blend(fitted, X)
    
    # Save models
    models_path.mkdir(parents=True, exist_ok=True)
    save_models(fitted, str(models_path / "ensemble.joblib"))
    
    # SHAP
    if save_shap:
        typer.echo("Computing SHAP values...")
        shap_results = compute_shap_values(fitted, X, sample_size=min(1000, len(X)))
        for name, res in shap_results.items():
            if "feature_importance" in res:
                res["feature_importance"].to_parquet(models_path / f"shap_{name}.parquet")
    
    write_geoparquet(F, "data/processed/features_scored.parquet")
    typer.echo("Scored features -> data/processed/features_scored.parquet")


@app.command()
def predict(input_path: str = "data/processed/features.parquet"):
    """Apply trained models to new data without retraining."""
    models_dir = Path("artifacts/models")
    models_path = models_dir / "ensemble.joblib"
    feature_cols_path = models_dir / "feature_cols.json"

    if not models_path.exists():
        typer.echo("No trained models found. Run 'train' first.")
        raise typer.Exit(1)

    typer.echo("Loading trained models...")
    fitted = load_models(str(models_path))

    # Load feature column names
    if feature_cols_path.exists():
        num_cols = pd.read_json(feature_cols_path, typ='series').tolist()
        typer.echo(f"Using {len(num_cols)} features from training")
    else:
        # Fallback for backward compatibility
        num_cols = ["aadt_sum_500m", "aadt_sum_1500m", "aadt_sum_5000m", "dist_m_nearest_dcfc"]
        typer.echo("Warning: feature_cols.json not found, using default 4 features")

    # Load input data
    if not Path(input_path).exists():
        typer.echo(f"Input file not found: {input_path}")
        raise typer.Exit(1)

    F = gpd.read_parquet(input_path)
    typer.echo(f"Loaded {len(F)} candidates from {input_path}")

    # Prepare features (filter to available columns)
    available_cols = [c for c in num_cols if c in F.columns]
    if len(available_cols) < len(num_cols):
        missing = set(num_cols) - set(available_cols)
        typer.echo(f"Warning: Missing features {missing}, filling with 0")
        for col in missing:
            F[col] = 0.0

    X = F[num_cols].copy().fillna(0)

    # Predict
    F["pred_daily_kwh"] = predict_with_blend(fitted, X)
    typer.echo(f"Predictions: mean={F['pred_daily_kwh'].mean():.1f}, range=[{F['pred_daily_kwh'].min():.1f}, {F['pred_daily_kwh'].max():.1f}]")

    # Save
    output_path = "data/processed/features_scored.parquet"
    write_geoparquet(F, output_path)
    typer.echo(f"Scored features -> {output_path}")


@app.command()
def pvsize(config_path: str = "configs/default.yaml"):
    """Size PV systems using PVWatts API."""
    cfg = load_yaml(config_path)
    defaults = cfg["pv"]["pvwatts_system_defaults"]
    frac = cfg["pv"]["pv_sizing_target_fraction"]
    
    F = gpd.read_parquet("data/processed/features_scored.parquet").to_crs(4326)
    pv_out = []
    
    typer.echo(f"Sizing PV for {len(F)} candidates...")
    for idx, r in F.iterrows():
        try:
            pv_kw = size_pv_for_fraction(
                annual_kwh_need=r["pred_daily_kwh"] * 365,
                target_fraction=frac,
                lat=r.geometry.y, lon=r.geometry.x,
                defaults=defaults
            )
        except Exception:
            pv_kw = 100.0
        pv_out.append(pv_kw)
    
    F["pv_kw_sized"] = pv_out
    F.to_crs(26912).to_parquet("data/processed/features_scored_pv.parquet", index=False)
    typer.echo("PV sizing complete -> data/processed/features_scored_pv.parquet")


@app.command()
def optimize(config_path: str = "configs/default.yaml"):
    """Run MILP optimization for site selection."""
    cfg = load_yaml(config_path)
    opt_cfg = cfg["opt"]
    
    F = gpd.read_parquet("data/processed/features_scored_pv.parquet").to_crs(26912)
    
    # Demand nodes
    demand = F[["cand_id", "aadt_sum_1500m", "geometry"]].copy()
    demand.rename(columns={"cand_id": "node_id", "aadt_sum_1500m": "pop_weight"}, inplace=True)
    demand["pop_weight"] = demand["pop_weight"].fillna(1)
    
    # Distance matrix
    dist = np.zeros((len(F), len(demand)))
    for i, gi in enumerate(F.geometry):
        dist[i, :] = demand.distance(gi).values / 1000.0
    
    # Scores
    pred = F["pred_daily_kwh"].fillna(0).values
    equity = F.get("equity_score", pd.Series(0.5, index=F.index)).fillna(0.5).values
    safety = F.get("safety_score", pd.Series(0, index=F.index)).fillna(0).values
    gridpen = F["grid_conflict_score"].fillna(1).values
    
    # Costs
    site_capex = np.full(len(F), 250000.0)
    
    typer.echo("Building MILP model...")
    model = build_milp(
        cands=F.assign(x=F.geometry.x, y=F.geometry.y),
        demand_nodes=demand.reset_index(drop=True),
        dist_km=dist, pred_daily_kwh=pred, equity_score=equity,
        safety_penalty=safety, grid_penalty=gridpen,
        site_capex=site_capex,
        pv_capex_per_kw=1600.0,
        storage_capex_per_kwh=600.0,
        params=opt_cfg
    )
    
    typer.echo("Solving...")
    res = solve_milp(
        model, solver_name=cfg["solver"]["name"],
        time_limit_s=cfg["solver"]["time_limit_s"],
        mip_gap=cfg["solver"]["mip_gap"]
    )
    
    selected = extract_solution(model, F)
    
    # Calculate economics
    if len(selected) > 0:
        typer.echo("Calculating economics...")
        params = CostParameters()
        econ = aggregate_portfolio_economics(selected, params)
        
        selected = selected.merge(
            econ["sites"][["cand_id", "total_capex", "net_capex", "annual_opex", "npv", "roi_pct"]],
            on="cand_id", how="left"
        )
        
        typer.echo(f"\nPortfolio Summary:")
        typer.echo(f"  Sites: {econ['portfolio']['num_sites']}")
        typer.echo(f"  Total CapEx: ${econ['portfolio']['total_capex']:,.0f}")
        typer.echo(f"  Net CapEx: ${econ['portfolio']['total_net_capex']:,.0f}")
        typer.echo(f"  NPV: ${econ['portfolio']['npv']:,.0f}")
    
    Path("artifacts/reports").mkdir(parents=True, exist_ok=True)
    selected.to_parquet("artifacts/reports/selected_sites.parquet", index=False)
    typer.echo(f"\nSelected {len(selected)} sites -> artifacts/reports/selected_sites.parquet")


@app.command()
def run_all(
    config_path: str = "configs/default.yaml",
    force_refresh: bool = False,
    retrain: bool = False
):
    """Run complete pipeline: load -> candidates -> features -> train/predict -> pvsize -> optimize."""
    typer.echo("=== Running Complete Pipeline ===\n")

    typer.echo("Step 1/6: Loading data...")
    load_data(config_path, force_refresh)

    typer.echo("\nStep 2/6: Building candidates...")
    make_candidates(config_path)

    typer.echo("\nStep 3/6: Engineering features...")
    features(config_path)

    # Check if models exist
    models_exist = Path("artifacts/models/ensemble.joblib").exists()

    if retrain or not models_exist:
        typer.echo("\nStep 4/6: Training ML models...")
        train(save_shap=True, retrain=True)
    else:
        typer.echo("\nStep 4/6: Applying trained models (use --retrain to force retraining)...")
        predict()

    typer.echo("\nStep 5/6: Sizing PV systems...")
    pvsize(config_path)

    typer.echo("\nStep 6/6: Running optimization...")
    optimize(config_path)

    typer.echo("\n=== Pipeline Complete ===")


@app.command()
def status(config_path: str = "configs/default.yaml"):
    """Show data and pipeline status."""
    loader = get_dataloader(config_path)
    
    typer.echo("Data Sources:")
    status_df = loader.get_status()
    typer.echo(status_df.to_string(index=False))
    
    typer.echo("\nProcessed Files:")
    for path in [
        "data/interim/candidates.parquet",
        "data/processed/features.parquet",
        "data/processed/features_scored.parquet",
        "data/processed/features_scored_pv.parquet",
        "artifacts/reports/selected_sites.parquet",
        "artifacts/models/ensemble.joblib"
    ]:
        p = Path(path)
        if p.exists():
            size = p.stat().st_size / (1024 * 1024)
            typer.echo(f"  {path}: {size:.2f} MB")
        else:
            typer.echo(f"  {path}: not found")


if __name__ == "__main__":
    app()

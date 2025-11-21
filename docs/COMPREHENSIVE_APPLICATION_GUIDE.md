# Elektraz - Comprehensive Application Guide

## Arizona Solar EV Charging Station Optimization Toolkit

**Version:** 2025 IISE Optimization Hackathon
**Theme:** "Electricity in and to Arizona"

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Application Overview](#2-application-overview)
3. [Architecture & Data Flow](#3-architecture--data-flow)
4. [Terminology & Key Concepts](#4-terminology--key-concepts)
5. [Data Sources & Datasets](#5-data-sources--datasets)
6. [Feature Engineering](#6-feature-engineering)
7. [Machine Learning Models](#7-machine-learning-models)
8. [PV System & Energy Modeling](#8-pv-system--energy-modeling)
9. [Economic Analysis](#9-economic-analysis)
10. [MILP Optimization](#10-milp-optimization)
11. [Solver Configuration](#11-solver-configuration)
12. [Streamlit Dashboard](#12-streamlit-dashboard)
13. [Configuration Guide](#13-configuration-guide)
14. [Running the Application](#14-running-the-application)
15. [Results Interpretation](#15-results-interpretation)
16. [Troubleshooting](#16-troubleshooting)

---

## 1. Executive Summary

**Elektraz** is a sophisticated optimization toolkit that determines optimal locations for solar-powered DC fast charging (DCFC) stations across Arizona. It combines:

- **Data ingestion** from 6 public APIs
- **Machine learning** for demand prediction (XGBoost, LightGBM, CatBoost ensemble)
- **Mixed-Integer Linear Programming (MILP)** for multi-objective optimization
- **Interactive web dashboard** for configuration and visualization

### Primary Objectives

The system optimizes site selection to:
- **Maximize**: Utilization (predicted daily energy demand) + Equity (underserved area coverage)
- **Minimize**: Safety risk (flood exposure) + Grid conflicts + Net present cost

### Key Constraints

| Constraint | Default Value | Description |
|------------|---------------|-------------|
| Budget | $15,000,000 | Total capital expenditure limit |
| Max Sites | 40 | Maximum number of stations |
| Min Spacing | 50 km | NEVI interstate corridor requirement |
| Ports per Site | 4-8 | 150 kW chargers per station |
| PV Sizing | 50-300 kW | Solar array capacity |
| Battery Storage | 0-500 kWh | Optional storage per site |

---

## 2. Application Overview

### Codebase Structure

```
elektraz/
├── app/                          # Streamlit Web Dashboard
│   ├── app.py                    # Main dashboard (292 lines)
│   └── pages/
│       ├── 1_Data_Explorer.py    # Browse datasets
│       ├── 2_Configuration.py    # Adjust parameters
│       ├── 3_Map_View.py         # Interactive maps
│       ├── 4_Run_Optimization.py # Execute pipeline
│       ├── 5_Results.py          # View results & economics
│       ├── 6_ML_Insights.py      # SHAP feature importance
│       └── 7_Data_Management.py  # Data controls
│
├── src/                          # Core Application Logic
│   ├── common/                   # Shared utilities
│   │   ├── config.py             # YAML/Pydantic config
│   │   ├── geo.py                # Geospatial helpers
│   │   └── io.py                 # I/O utilities
│   │
│   ├── data/                     # Data Ingestion
│   │   ├── dataloader.py         # Auto-loading with caching
│   │   ├── build_candidates.py   # Generate candidates
│   │   ├── ingest_afdc.py        # NREL EV station API
│   │   ├── ingest_acs.py         # Census demographics
│   │   └── ingest_vector.py      # ArcGIS integration
│   │
│   ├── features/                 # Feature Engineering
│   │   └── engineer.py           # Spatial feature computation
│   │
│   ├── ml/                       # Machine Learning
│   │   ├── tabular_sklearn.py    # Ensemble pipelines
│   │   ├── tabular_torch.py      # Deep learning (optional)
│   │   └── evaluate.py           # Metrics
│   │
│   ├── energy/                   # Energy Modeling
│   │   ├── pvwatts.py            # NREL PVWatts API
│   │   └── energy_balance.py     # Load/generation balance
│   │
│   ├── economics/                # Financial Analysis
│   │   └── costs.py              # CapEx, OpEx, NPV, ROI
│   │
│   └── opt/                      # Optimization
│       ├── facility_milp.py      # MILP formulation
│       └── postsolve.py          # Solution extraction
│
├── configs/                      # Configuration
│   └── default.yaml              # All parameters
│
├── cli.py                        # Command-line Interface
└── run_app.py                    # Streamlit launcher
```

### Total Codebase

- **Lines of Code**: ~2,000 across 35+ modules
- **Dependencies**: 56 Python packages
- **Architecture**: Three-layer (Frontend → Logic → Data)

---

## 3. Architecture & Data Flow

### Pipeline Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INGEST DATA                                               │
│    ├─ ADOT AADT (traffic volumes)                           │
│    ├─ NREL AFDC (existing EV stations)                      │
│    ├─ FEMA NFHL (flood zones)                               │
│    ├─ Valley Metro (Park & Ride)                            │
│    ├─ EPA EJSCREEN (equity indicators)                      │
│    └─ Census ACS (demographics)                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. BUILD CANDIDATES                                          │
│    ├─ Combine: Park & Ride + rest areas + high-AADT sites   │
│    ├─ Snap to AFC corridor (1-mile buffer)                  │
│    └─ Deduplicate (800m grid)                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. ENGINEER FEATURES                                         │
│    ├─ Distance to nearest DCFC                              │
│    ├─ AADT aggregations (500m, 1500m, 5000m buffers)        │
│    ├─ Flood hazard intersection                             │
│    └─ Equity & grid conflict scores                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. TRAIN ML MODELS                                           │
│    ├─ Target: Proxy daily_kwh (AADT × distance)             │
│    ├─ Ensemble: XGBoost + LightGBM + CatBoost               │
│    ├─ 5-fold cross-validation                               │
│    └─ SHAP feature importance                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. SIZE PV SYSTEMS                                           │
│    ├─ Call NREL PVWatts API per location                    │
│    └─ Size for 60% annual demand offset                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. OPTIMIZE (MILP)                                           │
│    ├─ Objective: Max utilization + equity - costs - risks   │
│    ├─ Constraints: Budget, spacing, coverage                │
│    └─ Solver: HiGHS (10 min, 1% gap)                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. ECONOMIC ANALYSIS                                         │
│    ├─ CapEx breakdown per site                              │
│    ├─ OpEx (maintenance, utilities, land)                   │
│    ├─ Revenue from charging                                 │
│    └─ NPV, ROI, payback period                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Terminology & Key Concepts

### EV Charging Infrastructure

| Term | Definition |
|------|------------|
| **DCFC** | DC Fast Charging - High-power (50-350 kW) charging stations |
| **NEVI** | National Electric Vehicle Infrastructure - Federal funding program |
| **AFC** | Alternative Fuel Corridor - Designated highway routes for EV charging |
| **Port** | Individual charging connector (150 kW default) |
| **Utilization Rate** | Percentage of time chargers are in use (default 15%) |

### Solar & Energy Terms

| Term | Definition |
|------|------------|
| **PV** | Photovoltaic - Solar panels converting sunlight to electricity |
| **kW** | Kilowatt - Power capacity (rate of energy transfer) |
| **kWh** | Kilowatt-hour - Energy unit (power × time) |
| **Tilt** | Solar panel angle from horizontal (default 15°) |
| **Azimuth** | Panel compass direction (180° = south-facing) |
| **Losses** | System efficiency losses (default 14%) |
| **C-rate** | Battery discharge rate (0.5C = 50% capacity per hour) |

### Optimization Terms

| Term | Definition |
|------|------------|
| **MILP** | Mixed-Integer Linear Programming |
| **MIP Gap** | Acceptable distance from optimal solution (default 1%) |
| **Objective Function** | Mathematical expression to maximize/minimize |
| **Decision Variable** | Values the solver determines (open, ports, PV, storage) |
| **Constraint** | Limits on feasible solutions (budget, spacing) |

### Economic Terms

| Term | Definition |
|------|------------|
| **CapEx** | Capital Expenditure - Upfront construction costs |
| **OpEx** | Operating Expenditure - Annual running costs |
| **NPV** | Net Present Value - Lifetime value discounted to today |
| **ROI** | Return on Investment - Annual return percentage |
| **ITC** | Investment Tax Credit - Federal solar incentive (30%) |
| **LCOC** | Levelized Cost of Charging - $/kWh over lifetime |

### Feature Engineering Terms

| Term | Definition |
|------|------------|
| **AADT** | Annual Average Daily Traffic - Vehicles per day |
| **Buffer Aggregation** | Summing values within a radius (500m, 1500m, 5000m) |
| **Spatial Index** | R-tree structure for efficient geographic queries |
| **Grid Conflict** | Proximity penalty to existing infrastructure |

---

## 5. Data Sources & Datasets

### Primary Data Sources

| Source | Type | Purpose | Required |
|--------|------|---------|----------|
| **ADOT AADT** | ArcGIS FeatureServer | Traffic volumes (2024) | Yes |
| **NREL AFDC** | REST API | Existing EV station locations | Yes |
| **FEMA NFHL** | ArcGIS FeatureServer | Flood hazard zones | No |
| **Valley Metro** | ArcGIS MapServer | Park & Ride locations | No |
| **EPA EJSCREEN** | CSV ZIP | Environmental justice | No |
| **Census ACS** | Census API | Demographics by ZCTA | No |

### Data Caching Strategy

- **Cache Duration**: 24 hours
- **Library**: `requests-cache`
- **Storage Format**: GeoParquet (compressed geometry + metadata)
- **Force Refresh**: `--force-refresh` CLI flag

### Data File Locations

```
data/
├── interim/                  # Cached API data
│   ├── adot_aadt.parquet
│   ├── afdc_az.parquet
│   ├── nfhl.parquet
│   ├── park_ride.parquet
│   └── candidates.parquet
│
└── processed/                # Engineered outputs
    ├── features.parquet
    ├── features_scored.parquet
    └── features_scored_pv.parquet

artifacts/
├── models/
│   ├── ensemble.joblib
│   └── shap_*.parquet
└── reports/
    └── selected_sites.parquet
```

---

## 6. Feature Engineering

### Computed Features

| Feature | Source | Type | Description |
|---------|--------|------|-------------|
| `dist_m_nearest_dcfc` | AFDC | Distance | Nearest DC fast charger (meters) |
| `aadt_sum_500m` | AADT | Aggregate | Traffic within 500m radius |
| `aadt_sum_1500m` | AADT | Aggregate | Traffic within 1500m radius |
| `aadt_sum_5000m` | AADT | Aggregate | Traffic within 5000m radius |
| `in_floodplain` | NFHL | Boolean | Flood zone exposure |
| `equity_score` | EJScreen | 0-1 | Environmental justice index |
| `grid_conflict_score` | Derived | 0-2 | Distance penalty (DCFC/10000) |
| `safety_penalty` | Derived | 0-1 | Floodplain exposure penalty |
| `accessibility_score` | Derived | 0-1 | Traffic normalization |

### Multi-Scale Buffer Analysis

The system computes spatial aggregations at three scales:

- **500m**: Local accessibility (walking distance)
- **1500m**: Neighborhood scale (short detour)
- **5000m**: Regional influence (major catchment)

### Target Variable (Proxy Label)

```python
daily_kwh = (aadt_sum_1500m / 1000) * (dist_m_nearest_dcfc / 5000)
# Clipped to range [10, 500] kWh/day
```

**Logic**: High traffic + far from existing stations = high demand potential

---

## 7. Machine Learning Models

### Ensemble Architecture

Three gradient boosting models with equal-weighted blending:

#### XGBoost Configuration
```python
n_estimators: 600
max_depth: 8
learning_rate: 0.05
subsample: 0.8
colsample_bytree: 0.8
tree_method: "hist"
```

#### LightGBM Configuration
```python
n_estimators: 1200
num_leaves: 64
learning_rate: 0.03
subsample: 0.8
colsample_bytree: 0.8
```

#### CatBoost Configuration
```python
depth: 8
iterations: 1500
learning_rate: 0.03
loss_function: "RMSE"
```

### Training Pipeline

1. **Preprocessing**: StandardScaler (numeric) + OneHotEncoder (categorical)
2. **Cross-Validation**: 5-fold with RMSE scoring
3. **Fitting**: Full dataset after CV
4. **Prediction**: Weighted average of all models
5. **SHAP**: Feature importance explanations

### Model Performance

| Metric | Typical Range | Interpretation |
|--------|---------------|----------------|
| RMSE | 35-50 kWh/day | Prediction error |
| R² | 0.65-0.80 | Variance explained |
| MAE | 25-40 kWh/day | Average absolute error |

### SHAP Explainability

SHAP (SHapley Additive exPlanations) values show:
- **Feature importance**: Which inputs matter most
- **Direction**: Positive/negative contribution
- **Magnitude**: Strength of effect

Visualized in the ML Insights dashboard page.

---

## 8. PV System & Energy Modeling

### NREL PVWatts Integration

The system calls NREL's PVWatts v8 API to size solar arrays:

```python
# Default system parameters
module_type: 1          # Premium modules
array_type: 2           # Fixed open rack
losses: 14              # 14% system losses
tilt: 15                # 15° (optimal for Arizona)
azimuth: 180            # South-facing
```

### PV Sizing Algorithm

1. Calculate annual energy need: `pred_daily_kwh × 365`
2. Target PV offset: 60% of annual demand (configurable)
3. Query PVWatts for 50 kW baseline output
4. Scale linearly to achieve target fraction
5. Constrain to [50, 300] kW range

### Load Profiles

**Hourly EV Charging Pattern**:
- Morning peak: 7-8 AM
- Evening peak: 6-7 PM
- Overnight minimum: 1-4 AM

**Monthly Seasonal Pattern (Arizona)**:
- Summer peak (Jul-Aug): 11% each
- Winter low (Dec-Jan): 7% each
- Shoulder months: 8-10%

### Thermal Derating (Arizona Climate)

Equipment performance degrades in extreme heat:

| Equipment | Threshold | Derating |
|-----------|-----------|----------|
| PV Inverter | >45°C | 2% per °C (max 20%) |
| Battery | >35°C | 1% per °C (max 10%) |
| DC Charger | >40°C | 1.5% per °C (max 15%) |

**Arizona Summer (43°C ambient)**:
- PV module temp: ~53°C → 84% efficiency
- Battery: 43°C → 92% efficiency
- Charger: 43°C → 95.5% efficiency

### Grid Impact Calculations

```python
Net Grid Energy = max(0, annual_load - pv_generation)
Net Peak Demand = max(0, peak_demand - storage_mitigation)
PV Offset % = (annual_load - net_grid) / annual_load × 100
```

---

## 9. Economic Analysis

### Capital Expenditure (CapEx)

| Component | Cost | Description |
|-----------|------|-------------|
| Site Preparation | $50,000 | Grading, foundations |
| Civil Work | $75,000 | Concrete, drainage |
| Interconnection | $100,000 + $50/kW | Grid connection + transformer |
| DC Chargers | $65,000/port | 150 kW charger units |
| PV System | $1,600/kW | Solar panels + inverters |
| Battery Storage | $600/kWh | Lithium-ion batteries |

### Operating Expenditure (OpEx)

| Component | Rate | Description |
|-----------|------|-------------|
| Maintenance | 2% of CapEx | Annual equipment upkeep |
| Insurance | 0.5% of CapEx | Property + liability |
| Land Lease | $12,000/year | Fixed annual fee |
| Network Fees | $2,400/year | Connectivity + software |
| Electricity | $0.12/kWh | Grid energy purchases |
| Demand Charges | $15/kW/month | Peak power costs |

### Incentives & Subsidies

| Incentive | Rate | Description |
|-----------|------|-------------|
| Federal ITC | 30% of PV cost | Investment Tax Credit |
| NEVI Grant | 80% of CapEx | Capped at $1,000,000 |

**Example Net CapEx**:
```
Total CapEx:       $875,000
Less Federal ITC:  -$48,000 (30% of $160k PV)
Less NEVI Grant:   -$700,000 (80%, under cap)
─────────────────────────────
Net CapEx:         $127,000
```

### Financial Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **NPV** | -CapEx + Σ(CF / (1+r)^t) | Positive = profitable |
| **ROI** | Annual CF / CapEx × 100 | Higher = better returns |
| **Payback** | CapEx / Annual CF | Shorter = faster recovery |
| **LCOC** | (PV CapEx + PV OpEx) / Energy | Lower = cheaper charging |

**Default Parameters**:
- Discount rate: 8%
- Project lifetime: 15 years
- Utilization rate: 15%
- Charging price: $0.35/kWh

### Revenue Model

```python
Annual Revenue = Dispensed Energy × Charging Price
Dispensed Energy = Annual Demand × Utilization Rate
```

---

## 10. MILP Optimization

### Problem Formulation

**Type**: Mixed-Integer Linear Programming (facility location)
**Framework**: Pyomo
**Solver**: HiGHS (open-source, high-performance)

### Decision Variables

| Variable | Type | Domain | Description |
|----------|------|--------|-------------|
| `open[i]` | Binary | {0, 1} | Build site i? |
| `ports[i]` | Integer | [0, 8] | Number of chargers |
| `pv_kw[i]` | Continuous | [0, 300] | Solar capacity |
| `storage_kwh[i]` | Continuous | [0, 500] | Battery capacity |
| `assign[i,j]` | Continuous | [0, 1] | Demand assignment |

### Objective Function

**Maximize**:
```
w_util × Σ(open[i] × pred_daily_kwh[i])     # Utilization
+ w_equity × Σ(open[i] × equity_score[i])    # Equity
- w_safety × Σ(open[i] × safety_penalty[i])  # Safety risk
- w_grid × Σ(open[i] × grid_conflict[i])     # Grid conflict
- w_cost × (Total Cost / 1,000,000)          # Normalized cost
```

**Default Weights**:
```yaml
util: 1.0           # Primary driver
equity: 0.25        # Secondary bonus
safety_penalty: 0.5 # Moderate penalty
grid_penalty: 0.3   # Low penalty
npc_cost: 0.8       # Strong cost control
```

### Constraints

| Constraint | Description |
|------------|-------------|
| **Budget** | Total CapEx ≤ $15,000,000 |
| **Site Count** | Σ open[i] ≤ 40 |
| **Min Spacing** | No two sites < 50 km apart |
| **Min Ports** | ports[i] ≥ 4 if open[i] = 1 |
| **Max Ports** | ports[i] ≤ 8 × open[i] |
| **Min PV** | pv_kw[i] ≥ 50 if open[i] = 1 |
| **Max PV** | pv_kw[i] ≤ 300 × open[i] |
| **Max Storage** | storage_kwh[i] ≤ 500 × open[i] |
| **Coverage** | Each demand node assigned to ≤1 site |
| **Detour** | Assignment only if site within 1.6 km |

### Cost Function in MILP

```python
Total Cost = Σ (
    site_capex × open[i]
    + pv_kw[i] × 1600
    + storage_kwh[i] × 600
    + ports[i] × 65000
)
```

---

## 11. Solver Configuration

### HiGHS Solver (Default)

```yaml
solver:
  name: highs
  time_limit_s: 600      # 10 minutes
  mip_gap: 0.01          # 1% optimality tolerance
```

**Characteristics**:
- Free and open-source
- Excellent for medium-sized MILP
- Uses branch-and-cut with cutting planes
- Finds good solutions quickly, refines to optimality

### Alternative: CBC Solver

```yaml
solver:
  name: cbc
  time_limit_s: 600
  mip_gap: 0.01
```

### Termination Conditions

| Condition | Action |
|-----------|--------|
| **Optimal** | Return best solution |
| **Time Limit** | Return best feasible solution |
| **Infeasible** | Raise error with suggestions |
| **Unbounded** | Raise error (weight misconfiguration) |

### Infeasibility Troubleshooting

Common causes and fixes:
- **Spacing too strict**: Reduce `min_spacing_km`
- **Budget too low**: Increase `budget_usd`
- **Detour too small**: Increase `max_detour_m`
- **Too few candidates**: Relax candidate generation

---

## 12. Streamlit Dashboard

### Page Navigation

| Page | Icon | Purpose |
|------|------|---------|
| Home | ⚡ | Overview metrics and quick map |
| Data Explorer | 📊 | Browse datasets with filters |
| Configuration | ⚙️ | Adjust all parameters |
| Map View | 🗺️ | Interactive multi-layer maps |
| Run Optimization | 🚀 | Execute pipeline with progress |
| Results | 📈 | Economics and site details |
| ML Insights | 🤖 | SHAP and feature importance |
| Data Management | 🔄 | Refresh and retrain |

### Key Visualizations

**Maps (Folium)**:
- Selected sites (green, sized by ports)
- Candidates (blue-to-red gradient)
- Existing stations (gray with popups)
- AADT roads (orange, width by traffic)

**Charts (Streamlit)**:
- Port distribution bar chart
- PV sizing histogram
- SHAP feature importance
- Prediction scatter plots
- CapEx breakdown by site

### Configuration Controls

**25+ Adjustable Parameters**:
- Capital costs (6 components)
- Operating costs (6 components)
- Optimization weights (5 objectives)
- Constraints (6 limits)
- PV defaults (5 parameters)
- Solver settings (3 options)

### Export Options

| Format | Content | Page |
|--------|---------|------|
| CSV | Datasets, selected sites | Data Explorer, Results |
| PDF | Portfolio report | Results |
| YAML | Configuration | Configuration |

---

## 13. Configuration Guide

### Main Configuration File

**Location**: `configs/default.yaml`

```yaml
project_name: az-ev-solar
random_seed: 42

# Coordinate Reference Systems
crs:
  wgs84: 4326          # Lat/lon for APIs
  utm12: 26912         # Meters for distances

# File paths
paths:
  raw: data/raw
  interim: data/interim
  processed: data/processed
  artifacts: artifacts

# Machine Learning
ml:
  models: [xgb, lgbm, cat]
  folds: 5
  shap_sample: 5000

# Feature Engineering
features:
  buffer_m: [500, 1500, 5000]

# PV System
pv:
  pv_sizing_target_fraction: 0.6
  pvwatts_system_defaults:
    module_type: 1
    array_type: 2
    losses: 14
    tilt: 15
    azimuth: 180

# Optimization
opt:
  budget_usd: 15000000
  max_sites: 40
  min_spacing_km: 50
  max_detour_m: 1600
  port_power_kw: 150
  ports_min: 4
  ports_max: 8
  pv_kw_min: 50
  pv_kw_max: 300
  storage_kwh_min: 0
  storage_kwh_max: 500
  weights:
    util: 1.0
    equity: 0.25
    safety_penalty: 0.5
    grid_penalty: 0.3
    npc_cost: 0.8

# Solver
solver:
  name: highs
  time_limit_s: 600
  mip_gap: 0.01
```

### Environment Variables

**File**: `.env`

```bash
NREL_API_KEY=your_key_here        # Required for PV sizing
CENSUS_API_KEY=your_key_here      # Optional for demographics
NREL_API_BASE=https://developer.nrel.gov
```

### Weight Tuning Guide

| Scenario | util | equity | safety | grid | cost |
|----------|------|--------|--------|------|------|
| **High Demand** | 1.5 | 0.2 | 0.3 | 0.2 | 0.5 |
| **Equity Focus** | 0.8 | 0.5 | 0.3 | 0.2 | 0.6 |
| **Cost Conscious** | 0.8 | 0.2 | 0.3 | 0.2 | 1.2 |
| **Safety Priority** | 0.8 | 0.2 | 0.8 | 0.3 | 0.6 |
| **Balanced** | 1.0 | 0.25 | 0.5 | 0.3 | 0.8 |

---

## 14. Running the Application

### CLI Commands

```bash
# Full pipeline (recommended)
python cli.py run-all

# Individual steps
python cli.py load-data           # Download from APIs
python cli.py make-candidates     # Generate sites
python cli.py features            # Engineer features
python cli.py train --save-shap   # Train ML models
python cli.py pvsize              # Size PV systems
python cli.py optimize            # Run MILP
python cli.py status              # Check pipeline state
```

### Web Dashboard

```bash
# Launch Streamlit
python run_app.py

# Access at http://localhost:8501
```

### Workflow Options

**Option 1: CLI First, Dashboard for Visualization**
```bash
python cli.py run-all
python run_app.py
# Navigate to Results page
```

**Option 2: Dashboard Only**
```bash
python run_app.py
# Use Run Optimization page
# Click "Run Full Pipeline"
```

### Expected Run Times

| Step | Duration | Notes |
|------|----------|-------|
| Data Ingestion | 2-5 min | API response dependent |
| Candidate Generation | <1 sec | Simple operations |
| Feature Engineering | 10-30 sec | Spatial operations |
| ML Training | 1-3 min | 5-fold CV on 1000+ sites |
| PV Sizing | 5-10 min | NREL API calls per site |
| Optimization | Up to 10 min | Solver time limit |
| **Total** | **10-30 min** | Depends on candidate count |

---

## 15. Results Interpretation

### Selected Sites Output

**Location**: `artifacts/reports/selected_sites.parquet`

| Column | Description |
|--------|-------------|
| `cand_id` | Unique identifier |
| `geometry` | Location (Point) |
| `ports` | Number of chargers (4-8) |
| `pv_kw` | Solar capacity (50-300) |
| `storage_kwh` | Battery size (0-500) |
| `pred_daily_kwh` | Predicted demand |
| `equity_score` | Underserved bonus |

### Economic Results

**Portfolio Metrics**:
- Total CapEx (before incentives)
- Net CapEx (after ITC + NEVI)
- Annual OpEx
- Annual Revenue
- Portfolio NPV
- Average Payback Period

**Per-Site Breakdown**:
- Individual CapEx components
- Site-specific NPV
- ROI percentage

### Map Interpretation

**Selected Sites (Green)**:
- Size = number of ports
- Click for popup with all details

**Candidates (Blue-Red)**:
- Color gradient = predicted demand
- Blue = low demand
- Red = high demand

**AADT Roads (Orange)**:
- Line width = traffic volume
- Shows major corridors

### Quality Indicators

**Good Solution**:
- 15-30 sites selected
- NPV > 0
- Payback < 10 years
- Geographic coverage across Arizona
- Mix of high-demand and equity sites

**Potential Issues**:
- 0 sites selected → Infeasible constraints
- NPV < 0 → Low utilization or high costs
- All sites clustered → Adjust spacing constraint
- No equity sites → Increase equity weight

---

## 16. Troubleshooting

### Common Errors

#### "MILP model is infeasible"

**Causes**:
- `min_spacing_km` too large for candidate density
- `budget_usd` too low for minimum viable site
- `max_detour_m` too small (no coverage)

**Fixes**:
```yaml
opt:
  min_spacing_km: 40        # Reduce from 50
  budget_usd: 20000000      # Increase budget
  max_detour_m: 3000        # Allow longer detour
```

#### "No NREL_API_KEY found"

**Fix**: Create `.env` file with valid API key from [NREL Developer Network](https://developer.nrel.gov/)

```bash
echo "NREL_API_KEY=your_key_here" > .env
```

#### "Data not found" errors

**Fix**: Run data loading first

```bash
python cli.py load-data --force-refresh
```

#### Solver timeout with poor solution

**Fixes**:
```yaml
solver:
  time_limit_s: 1200        # Increase to 20 min
  mip_gap: 0.05             # Accept 5% gap
```

#### Memory errors during training

**Fix**: Reduce SHAP sample size

```yaml
ml:
  shap_sample: 1000         # Down from 5000
```

### Performance Optimization

- **Reduce candidates**: Tighten AFC buffer or increase grid cell size
- **Faster solver**: Use HiGHS over CBC
- **Skip optional data**: NFHL, EJScreen are optional
- **Cache utilization**: Avoid `--force-refresh` unless needed

### Getting Help

1. Check console logs for specific errors
2. Review `configs/default.yaml` for parameter issues
3. Verify data files exist in `data/interim/`
4. Ensure API keys are set in `.env`

---

## Appendix: Dependencies

### Core Packages

```
pandas>=2.2
geopandas>=0.14
numpy>=1.26
pyarrow>=15.0
shapely>=2.0
pyproj>=3.6
```

### Machine Learning

```
scikit-learn>=1.5
xgboost>=2.1
lightgbm>=4.5
catboost>=1.2
shap>=0.46
```

### Optimization

```
pyomo>=6.7
highspy>=1.8
```

### Visualization

```
streamlit>=1.37
streamlit-folium>=0.21
folium>=0.17
plotly>=5.22
```

### Utilities

```
hydra-core>=1.3
pydantic>=2.7
typer>=0.12
requests>=2.32
requests-cache>=1.2
```

---

**Document Version**: 1.0
**Last Updated**: November 2025
**Author**: Generated by Claude Code analysis


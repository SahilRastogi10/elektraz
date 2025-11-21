# Elektraz Quick Reference

## Commands

### Full Pipeline
```bash
python cli.py run-all
```

### Individual Steps
```bash
python cli.py load-data           # 1. Download data
python cli.py make-candidates     # 2. Generate sites
python cli.py features            # 3. Engineer features
python cli.py train --save-shap   # 4. Train ML
python cli.py pvsize              # 5. Size PV
python cli.py optimize            # 6. Run MILP
```

### Dashboard
```bash
python run_app.py                 # http://localhost:8501
```

---

## Key Parameters

### Budget & Constraints
| Parameter | Default | Config Key |
|-----------|---------|------------|
| Budget | $15,000,000 | `opt.budget_usd` |
| Max Sites | 40 | `opt.max_sites` |
| Min Spacing | 50 km | `opt.min_spacing_km` |
| Ports Range | 4-8 | `opt.ports_min/max` |
| PV Range | 50-300 kW | `opt.pv_kw_min/max` |
| Storage Range | 0-500 kWh | `opt.storage_kwh_min/max` |

### Optimization Weights
| Weight | Default | Effect |
|--------|---------|--------|
| `util` | 1.0 | Maximize demand |
| `equity` | 0.25 | Underserved bonus |
| `safety_penalty` | 0.5 | Avoid floods |
| `grid_penalty` | 0.3 | Spread sites |
| `npc_cost` | 0.8 | Minimize costs |

### Capital Costs
| Component | Cost |
|-----------|------|
| Site Prep | $50,000 |
| Civil Work | $75,000 |
| Interconnection | $100,000 + $50/kW |
| Charger | $65,000/port |
| PV System | $1,600/kW |
| Storage | $600/kWh |

### Incentives
| Incentive | Rate |
|-----------|------|
| Federal ITC | 30% of PV cost |
| NEVI Grant | 80% of CapEx (max $1M) |

---

## File Locations

### Input Data
```
data/interim/
├── adot_aadt.parquet      # Traffic
├── afdc_az.parquet        # Existing stations
├── nfhl.parquet           # Flood zones
├── park_ride.parquet      # P&R sites
└── candidates.parquet     # Generated sites
```

### Processed Data
```
data/processed/
├── features.parquet           # Engineered features
├── features_scored.parquet    # With ML predictions
└── features_scored_pv.parquet # With PV sizing
```

### Outputs
```
artifacts/
├── models/ensemble.joblib     # Trained models
├── models/shap_*.parquet      # SHAP values
└── reports/selected_sites.parquet  # Final results
```

---

## Dashboard Pages

| Page | URL Suffix | Purpose |
|------|------------|---------|
| Home | `/` | Overview & quick map |
| Data Explorer | `/Data_Explorer` | Browse data |
| Configuration | `/Configuration` | Adjust params |
| Map View | `/Map_View` | Interactive maps |
| Run Optimization | `/Run_Optimization` | Execute pipeline |
| Results | `/Results` | View economics |
| ML Insights | `/ML_Insights` | SHAP analysis |
| Data Management | `/Data_Management` | Refresh data |

---

## Common Fixes

### Infeasible MILP
```yaml
# Relax constraints in configs/default.yaml
opt:
  min_spacing_km: 40     # Reduce from 50
  budget_usd: 20000000   # Increase budget
```

### Missing API Key
```bash
# Create .env file
echo "NREL_API_KEY=your_key" > .env
```

### Force Data Refresh
```bash
python cli.py load-data --force-refresh
```

### Slow Solver
```yaml
solver:
  time_limit_s: 1200    # Increase time
  mip_gap: 0.05         # Accept 5% gap
```

---

## Expected Results

### Portfolio Summary
- Sites: 15-30 selected
- Net CapEx: ~$3-5M (after incentives)
- NPV: Should be positive
- Payback: <10 years ideal

### Per Site Averages
- Ports: 5-6
- PV: 100-150 kW
- Storage: 50-200 kWh
- Daily Demand: 100-300 kWh

---

## API Keys Required

| Key | Required | Source |
|-----|----------|--------|
| `NREL_API_KEY` | Yes (PV sizing) | [developer.nrel.gov](https://developer.nrel.gov/) |
| `CENSUS_API_KEY` | Optional | [census.gov/developers](https://www.census.gov/developers/) |

---

## Glossary

| Term | Definition |
|------|------------|
| DCFC | DC Fast Charging (50-350 kW) |
| NEVI | National EV Infrastructure Program |
| AFC | Alternative Fuel Corridor |
| MILP | Mixed-Integer Linear Programming |
| AADT | Annual Average Daily Traffic |
| CapEx | Capital Expenditure |
| OpEx | Operating Expenditure |
| NPV | Net Present Value |
| ITC | Investment Tax Credit |
| SHAP | SHapley Additive exPlanations |


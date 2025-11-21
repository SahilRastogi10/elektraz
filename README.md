# Elektraz - Arizona Solar EV Charging Station Optimization

A comprehensive toolkit for optimizing the placement of solar-powered DC fast charging (DCFC) stations across Arizona, built for the 2025 IISE Optimization Hackathon.

## Features

### Backend
- **Data Ingestion** - Pull data from public APIs (ADOT, NREL, Census, EPA)
- **Candidate Generation** - Identify potential sites from rest areas, Park & Ride, high-traffic areas
- **Feature Engineering** - Compute accessibility, equity, safety scores
- **ML Prediction** - Ensemble models (XGBoost, LightGBM, CatBoost) predict daily energy demand
- **SHAP Explanations** - Feature importance and model interpretability
- **PV Sizing** - Size solar arrays using NREL PVWatts API
- **Economic Modeling** - Detailed CapEx/OpEx, NPV, ROI calculations
- **MILP Optimization** - Facility location optimization with Pyomo + HiGHS

### Frontend (Streamlit)
- **Dashboard** - Overview of project status and metrics
- **Data Explorer** - Browse and analyze all datasets
- **Configuration** - Adjust costs, weights, and optimization parameters
- **Interactive Maps** - Visualize candidates, existing stations, and results
- **Optimization Runner** - Execute pipeline with live progress
- **Results Dashboard** - View selected sites, economics, and generate reports
- **ML Insights** - SHAP explanations and feature importance

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd elektraz

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Add your API keys:
```
NREL_API_KEY=your_nrel_key
CENSUS_API_KEY=your_census_key
```

3. Adjust parameters in `configs/default.yaml` as needed.

## Usage

### Command Line Interface

Run the complete pipeline:
```bash
python cli.py run-all
```

Or run individual steps:
```bash
python cli.py ingest-remote   # Download data from APIs
python cli.py make-candidates # Generate candidate sites
python cli.py features        # Engineer features
python cli.py train --save-shap  # Train ML models
python cli.py pvsize          # Size PV systems
python cli.py optimize        # Run optimization
```

### Streamlit Dashboard

Launch the web interface:
```bash
python run_app.py
# or
streamlit run app/app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
elektraz/
├── app/                    # Streamlit frontend
│   ├── app.py             # Main dashboard
│   └── pages/             # Additional pages
│       ├── 1_Data_Explorer.py
│       ├── 2_Configuration.py
│       ├── 3_Map_View.py
│       ├── 4_Run_Optimization.py
│       ├── 5_Results.py
│       └── 6_ML_Insights.py
├── cli.py                  # Command-line interface
├── configs/
│   └── default.yaml       # Configuration parameters
├── src/
│   ├── common/            # Shared utilities
│   ├── data/              # Data ingestion
│   ├── features/          # Feature engineering
│   ├── ml/                # Machine learning
│   ├── energy/            # PV & energy modeling
│   ├── economics/         # Cost & ROI calculations
│   ├── opt/               # MILP optimization
│   ├── utils/             # HTTP clients
│   └── viz/               # Visualization
├── data/
│   ├── interim/           # Cached API data
│   └── processed/         # Processed features
├── artifacts/
│   ├── models/            # Trained ML models
│   └── reports/           # Optimization results
└── docs/                  # Documentation
```

## Key Parameters

- **Budget**: $15,000,000
- **Max Sites**: 40
- **Min Spacing**: 50 km (NEVI requirement)
- **Ports per Site**: 4-8 (150 kW each)
- **PV Range**: 50-300 kW per site
- **Storage**: 0-500 kWh per site

## Optimization Objectives

The MILP maximizes:
- **Utilization**: Predicted daily energy demand
- **Equity**: Coverage of underserved areas

While minimizing:
- **Safety Risk**: Floodplain exposure
- **Grid Conflict**: Distance from infrastructure
- **Net Present Cost**: Lifecycle costs

## Data Sources

- ADOT AADT (2024) - Traffic volumes
- NREL AFDC - Existing EV stations
- FEMA NFHL - Flood hazard zones
- Valley Metro Park & Ride - Public host sites
- EPA EJSCREEN - Equity indicators
- Census ACS - Demographics by ZCTA

## License

MIT License

## Authors

Built for the 2025 IISE Optimization Hackathon
Theme: "Electricity in and to Arizona"

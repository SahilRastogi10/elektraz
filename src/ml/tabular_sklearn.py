import pandas as pd, numpy as np, joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_squared_error
import xgboost as xgb, lightgbm as lgb, catboost as cb

def build_pipelines(num_cols, cat_cols):
    ohe = OneHotEncoder(handle_unknown="ignore", min_frequency=0.01, sparse_output=True)
    ct = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", ohe, cat_cols),
    ])
    models = {
        "xgb": xgb.XGBRegressor(
            n_estimators=600, max_depth=8, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, tree_method="hist"
        ),
        "lgbm": lgb.LGBMRegressor(
            n_estimators=1200, num_leaves=64, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8
        ),
        "cat": cb.CatBoostRegressor(depth=8, iterations=1500, learning_rate=0.03, loss_function="RMSE", verbose=False)
    }
    pipes = {k: Pipeline(steps=[("prep", ct), ("model", m)]) for k,m in models.items()}
    return pipes

def cv_and_fit(X: pd.DataFrame, y: pd.Series, pipes: dict, folds=5, seed=42):
    kf = KFold(n_splits=folds, shuffle=True, random_state=seed)
    results, fitted = {}, {}
    for name, pipe in pipes.items():
        scores = -1 * cross_val_score(pipe, X, y, cv=kf, scoring="neg_root_mean_squared_error", n_jobs=-1)
        results[name] = {"rmse_mean": float(scores.mean()), "rmse_std": float(scores.std())}
        pipe.fit(X, y)
        fitted[name]=pipe
    return results, fitted

def predict_with_blend(models: dict, X: pd.DataFrame, weights: dict | None=None):
    if weights is None:
        weights = {k:1/len(models) for k in models}
    preds = np.zeros(len(X))
    for k,pipe in models.items():
        preds += weights.get(k,0)*pipe.predict(X)
    return preds

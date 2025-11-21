# src/ml/tabular_sklearn.py
"""ML pipelines with SHAP explanations."""

import pandas as pd
import numpy as np
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from typing import Dict, Tuple, Optional


def build_pipelines(num_cols: list, cat_cols: list) -> Dict[str, Pipeline]:
    """Build ML pipelines for ensemble."""
    ohe = OneHotEncoder(handle_unknown="ignore", min_frequency=0.01, sparse_output=True)
    
    transformers = [("num", StandardScaler(), num_cols)]
    if cat_cols:
        transformers.append(("cat", ohe, cat_cols))
    
    ct = ColumnTransformer(transformers)
    
    models = {
        "xgb": xgb.XGBRegressor(
            n_estimators=600, max_depth=8, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, tree_method="hist",
            random_state=42, verbosity=0
        ),
        "lgbm": lgb.LGBMRegressor(
            n_estimators=1200, num_leaves=64, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1
        ),
        "cat": cb.CatBoostRegressor(
            depth=8, iterations=1500, learning_rate=0.03,
            loss_function="RMSE", verbose=False, random_state=42
        )
    }
    
    pipes = {k: Pipeline(steps=[("prep", ct), ("model", m)]) for k, m in models.items()}
    return pipes


def cv_and_fit(X: pd.DataFrame, y: np.ndarray, pipes: dict, 
               folds: int = 5, seed: int = 42) -> Tuple[dict, dict]:
    """Cross-validate and fit all pipelines."""
    kf = KFold(n_splits=folds, shuffle=True, random_state=seed)
    results, fitted = {}, {}
    
    for name, pipe in pipes.items():
        scores = -1 * cross_val_score(
            pipe, X, y, cv=kf, 
            scoring="neg_root_mean_squared_error", 
            n_jobs=-1
        )
        results[name] = {
            "rmse_mean": float(scores.mean()),
            "rmse_std": float(scores.std())
        }
        pipe.fit(X, y)
        fitted[name] = pipe
    
    return results, fitted


def predict_with_blend(models: dict, X: pd.DataFrame, 
                       weights: Optional[dict] = None) -> np.ndarray:
    """Blend predictions from multiple models."""
    if weights is None:
        weights = {k: 1/len(models) for k in models}
    
    preds = np.zeros(len(X))
    for k, pipe in models.items():
        preds += weights.get(k, 0) * pipe.predict(X)
    
    return preds


def compute_shap_values(fitted_models: dict, X: pd.DataFrame, 
                        sample_size: int = 1000) -> dict:
    """Compute SHAP values for feature importance."""
    try:
        import shap
    except ImportError:
        return {"error": "SHAP not installed"}
    
    shap_results = {}
    
    # Sample if dataset is large
    if len(X) > sample_size:
        X_sample = X.sample(n=sample_size, random_state=42)
    else:
        X_sample = X
    
    for name, pipe in fitted_models.items():
        try:
            # Get preprocessed features
            preprocessor = pipe.named_steps["prep"]
            model = pipe.named_steps["model"]
            X_transformed = preprocessor.transform(X_sample)
            
            # Create explainer based on model type
            if name == "xgb":
                explainer = shap.TreeExplainer(model)
            elif name == "lgbm":
                explainer = shap.TreeExplainer(model)
            elif name == "cat":
                explainer = shap.TreeExplainer(model)
            else:
                continue
            
            shap_values = explainer.shap_values(X_transformed)
            
            # Get feature names
            feature_names = []
            for trans_name, trans, cols in preprocessor.transformers_:
                if trans_name == "num":
                    feature_names.extend(cols)
                elif trans_name == "cat" and hasattr(trans, "get_feature_names_out"):
                    feature_names.extend(trans.get_feature_names_out(cols))
            
            # Compute mean absolute SHAP values
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            
            # Create importance dataframe
            importance_df = pd.DataFrame({
                "feature": feature_names[:len(mean_abs_shap)],
                "importance": mean_abs_shap
            }).sort_values("importance", ascending=False)
            
            shap_results[name] = {
                "shap_values": shap_values,
                "feature_importance": importance_df,
                "expected_value": explainer.expected_value
            }
            
        except Exception as e:
            shap_results[name] = {"error": str(e)}
    
    return shap_results


def evaluate_models(fitted_models: dict, X: pd.DataFrame, y: np.ndarray) -> dict:
    """Evaluate fitted models on data."""
    metrics = {}
    
    for name, pipe in fitted_models.items():
        preds = pipe.predict(X)
        metrics[name] = {
            "r2": float(r2_score(y, preds)),
            "rmse": float(np.sqrt(mean_squared_error(y, preds))),
            "mae": float(mean_absolute_error(y, preds))
        }
    
    # Blend evaluation
    blend_preds = predict_with_blend(fitted_models, X)
    metrics["blend"] = {
        "r2": float(r2_score(y, blend_preds)),
        "rmse": float(np.sqrt(mean_squared_error(y, blend_preds))),
        "mae": float(mean_absolute_error(y, blend_preds))
    }
    
    return metrics


def save_models(fitted_models: dict, path: str):
    """Save fitted models to disk."""
    joblib.dump(fitted_models, path)


def load_models(path: str) -> dict:
    """Load fitted models from disk."""
    return joblib.load(path)

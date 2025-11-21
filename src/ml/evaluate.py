import numpy as np, pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

def regression_metrics(y, yhat):
    return {
        "r2": float(r2_score(y, yhat)),
        "rmse": float(np.sqrt(mean_squared_error(y, yhat))),
        "mae": float(mean_absolute_error(y, yhat)),
    }

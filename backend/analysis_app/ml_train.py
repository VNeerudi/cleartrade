import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib

FEATURES = ["ma_10", "ma_30", "rsi", "volatility"]

def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["future_ret"] = df["close"].pct_change().shift(-1)

    df["y"] = np.where(
        df["future_ret"] > 0.005, 2,
        np.where(df["future_ret"] < -0.005, 0, 1)
    )

    return df

def train_save(df: pd.DataFrame, model_path: str):
    df = df.dropna(subset=FEATURES + ["y"])

    X = df[FEATURES].values
    y = df["y"].values

    model = LogisticRegression(max_iter=2000)
    model.fit(X, y)

    joblib.dump(model, model_path)
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import joblib

FEATURES = ["ma_10", "ma_30", "rsi", "volatility"]


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Label each row with a discrete trend class based on next-day return:
    - 2 = BUY  if future return > +0.5%
    - 0 = SELL if future return < -0.5%
    - 1 = HOLD otherwise
    """
    df = df.copy()
    df["future_ret"] = df["close"].pct_change().shift(-1)

    df["y"] = np.where(
        df["future_ret"] > 0.005,
        2,
        np.where(df["future_ret"] < -0.005, 0, 1),
    )

    return df


def train_save(df: pd.DataFrame, model_path: str, model_type: str = "logreg"):
    """
    Train a supervised classifier on engineered technical indicators.

    - model_type=\"logreg\"  → interpretable Logistic Regression baseline
    - model_type=\"forest\"  → non-linear Random Forest model

    Both models expose predict_proba, so they can be used interchangeably
    by the agent layer.
    """
    df = df.dropna(subset=FEATURES + ["y"])

    X = df[FEATURES].values
    y = df["y"].values

    model_type = (model_type or "logreg").lower()
    if model_type == "forest":
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
    else:
        # Older scikit-learn versions default to a multinomial-capable
        # configuration without an explicit multi_class argument.
        model = LogisticRegression(max_iter=2000)

    model.fit(X, y)

    joblib.dump(model, model_path)
"""
Evaluate the technical trend classifier with train/test split and metrics.

Uses a time-based split: earlier dates = training set, later dates = test set.
Prints train accuracy, test accuracy, confusion matrix, and per-class metrics.

Run from backend directory (with venv activated):
  python evaluate_model.py

Optional: --ticker MSFT  --test-ratio 0.25  --model-type logreg  --save
"""
import argparse
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib

from core.models import StockPrice
from analysis_app.indicators import compute_indicators
from analysis_app.ml_train import FEATURES, add_labels

MODEL_PATH = "analysis_model.joblib"
LABELS = {0: "SELL", 1: "HOLD", 2: "BUY"}
LABEL_NAMES = [LABELS[i] for i in range(3)]


def load_and_prepare(ticker: str):
    qs = StockPrice.objects.filter(ticker=ticker).order_by("date")
    df = pd.DataFrame([{"date": p.date, "close": p.close} for p in qs])
    if df.empty:
        raise SystemExit(f"No price data for ticker {ticker}.")
    df["date"] = pd.to_datetime(df["date"])
    df = compute_indicators(df)
    df = add_labels(df)
    df = df.dropna(subset=FEATURES + ["y"])
    return df


def time_split(df: pd.DataFrame, test_ratio: float = 0.25):
    n = len(df)
    if n < 60:
        raise SystemExit("Need at least 60 rows after indicators.")
    n_test = max(int(n * test_ratio), 1)
    n_train = n - n_test
    train_df = df.iloc[:n_train]
    test_df = df.iloc[n_train:]
    return train_df, test_df


def main():
    parser = argparse.ArgumentParser(description="Evaluate trend classifier with train/test split.")
    parser.add_argument("--ticker", default="AAPL", help="Ticker to use for data (default: AAPL)")
    parser.add_argument("--test-ratio", type=float, default=0.25, help="Fraction of data for test (default: 0.25)")
    parser.add_argument("--model-type", default="logreg", choices=["logreg", "forest"], help="Model type")
    parser.add_argument("--save", action="store_true", help="Save trained model to analysis_model.joblib for the app")
    args = parser.parse_args()

    print("Loading and preparing data...")
    df = load_and_prepare(args.ticker)
    train_df, test_df = time_split(df, args.test_ratio)

    X_train = train_df[FEATURES].values
    y_train = train_df["y"].values
    X_test = test_df[FEATURES].values
    y_test = test_df["y"].values

    print(f"Train samples: {len(y_train)}, Test samples: {len(y_test)}")
    print()

    model_type = args.model_type.lower()
    if model_type == "forest":
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
    else:
        model = LogisticRegression(max_iter=2000)

    model.fit(X_train, y_train)

    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    print("=" * 60)
    print("MODEL & DATA")
    print("=" * 60)
    print(f"Ticker:        {args.ticker}")
    print(f"Model:         {'Logistic Regression' if model_type == 'logreg' else 'Random Forest'}")
    print(f"Features:      {FEATURES}")
    print(f"Train size:    {len(y_train)}  |  Test size: {len(y_test)}")
    print()

    print("=" * 60)
    print("ACCURACY")
    print("=" * 60)
    print(f"Train accuracy: {train_acc:.4f} ({train_acc * 100:.2f}%)")
    print(f"Test accuracy:  {test_acc:.4f} ({test_acc * 100:.2f}%)")
    print()

    print("=" * 60)
    print("CONFUSION MATRIX (Test set)")
    print("        Predicted")
    print("        SELL  HOLD   BUY")
    cm = confusion_matrix(y_test, y_test_pred, labels=[0, 1, 2])
    for i, name in enumerate(LABEL_NAMES):
        row = "  ".join(f"{cm[i, j]:5d}" for j in range(3))
        print(f"True {name:4}  {row}")
    print()

    print("=" * 60)
    print("CLASSIFICATION REPORT (Test set)")
    print("=" * 60)
    print(classification_report(y_test, y_test_pred, target_names=LABEL_NAMES, digits=4, zero_division=0))
    print()

    if args.save:
        joblib.dump(model, MODEL_PATH)
        print(f"Model saved to {MODEL_PATH} (trained on train set only).")
    else:
        print("Run with --save to write this model to analysis_model.joblib for the app.")


if __name__ == "__main__":
    main()

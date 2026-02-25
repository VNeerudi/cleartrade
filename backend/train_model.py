import os
import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.models import StockPrice
from analysis_app.indicators import compute_indicators
from analysis_app.ml_train import add_labels, train_save

MODEL_PATH = "analysis_model.joblib"

def main():
    ticker = "AAPL"

    qs = StockPrice.objects.filter(ticker=ticker).order_by("date")
    df = pd.DataFrame([{"date": p.date, "close": p.close} for p in qs])

    df["date"] = pd.to_datetime(df["date"])
    df = compute_indicators(df)
    df = add_labels(df)

    train_save(df, MODEL_PATH)
    print("Model saved to:", MODEL_PATH)

if __name__ == "__main__":
    main()
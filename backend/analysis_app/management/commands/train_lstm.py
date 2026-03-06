from django.core.management.base import BaseCommand
from core.models import StockPrice
from analysis_app.indicators import compute_indicators
from analysis_app.ml_train import add_labels
from analysis_app.lstm_model import train_lstm
import pandas as pd


class Command(BaseCommand):
    help = "Train LSTM on technical indicator sequences (requires tensorflow). Use one ticker's history."

    def add_arguments(self, parser):
        parser.add_argument("--ticker", default="AAPL", help="Ticker to train on")

    def handle(self, *args, **opts):
        ticker = (opts.get("ticker") or "AAPL").upper()
        qs = StockPrice.objects.filter(ticker=ticker).order_by("date")
        df = pd.DataFrame([{"date": p.date, "close": p.close} for p in qs])
        if len(df) < 80:
            self.stdout.write(self.style.WARNING(f"Need ~80+ rows for {ticker}. Import prices first."))
            return
        df["date"] = pd.to_datetime(df["date"])
        df = compute_indicators(df)
        df = add_labels(df)
        path = train_lstm(df)
        if path.startswith("/") or path.endswith(".keras"):
            self.stdout.write(self.style.SUCCESS(f"LSTM saved to {path}"))
        else:
            self.stdout.write(self.style.ERROR(path))

from django.core.management.base import BaseCommand
import pandas as pd
from core.models import StockPrice

class Command(BaseCommand):
    help = "Import prices.csv (Date, Ticker, Open, High, Low, Close, Volume)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True)

    def handle(self, *args, **opts):
        df = pd.read_csv(opts["csv"])
        df.rename(columns={
            "Date": "date",
            "Ticker": "ticker",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }, inplace=True)

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["ticker"] = df["ticker"].astype(str).str.upper()

        objs = [
            StockPrice(
                ticker=r.ticker,
                date=r.date,
                open=float(r.open),
                high=float(r.high),
                low=float(r.low),
                close=float(r.close),
                volume=int(r.volume),
            )
            for r in df.itertuples(index=False)
        ]

        StockPrice.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(objs)} price rows"))
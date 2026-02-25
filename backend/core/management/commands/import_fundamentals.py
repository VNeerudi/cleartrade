from django.core.management.base import BaseCommand
import pandas as pd
from datetime import date
from core.models import FundamentalMetric

class Command(BaseCommand):
    help = "Import FUNDAMENTALratios.csv (symbol, trailingPE, earningsGrowth, revenueGrowth)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True)

    def handle(self, *args, **opts):
        df = pd.read_csv(opts["csv"])
        df.rename(columns={
            "symbol": "ticker",
            "trailingPE": "pe_ratio",
            "earningsGrowth": "earnings_growth",
            "revenueGrowth": "revenue_growth",
        }, inplace=True)

        df["ticker"] = df["ticker"].astype(str).str.upper()
        snapshot = date.today()

        objs = []
        for r in df.itertuples(index=False):
            objs.append(FundamentalMetric(
                ticker=r.ticker,
                period_end=snapshot,
                pe_ratio=None if pd.isna(getattr(r, "pe_ratio", None)) else float(r.pe_ratio),
                earnings_growth=None if pd.isna(getattr(r, "earnings_growth", None)) else float(r.earnings_growth),
                revenue_growth=None if pd.isna(getattr(r, "revenue_growth", None)) else float(r.revenue_growth),
            ))

        FundamentalMetric.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(objs)} fundamentals rows"))
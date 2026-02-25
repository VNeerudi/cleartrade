from django.core.management.base import BaseCommand
import pandas as pd
from core.models import NewsHeadline

class Command(BaseCommand):
    help = "Import financial_news_events.csv (Date, Headline, Related_Company)"

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True)

    def handle(self, *args, **opts):
        df = pd.read_csv(opts["csv"])
        df.rename(columns={
            "Date": "date",
            "Headline": "headline",
            "Related_Company": "ticker",
        }, inplace=True)

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["ticker"] = df["ticker"].astype(str).str.upper()

        objs = []
        for r in df.itertuples(index=False):
            t = str(r.ticker).strip()
            if t == "" or t.lower() == "nan":
                continue
            objs.append(NewsHeadline(ticker=t, date=r.date, headline=str(r.headline)))

        NewsHeadline.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(objs)} news rows"))
"""
Backtesting (paper §4 future features): evaluate past recommendations vs next-period returns.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import StockPrice, FundamentalMetric, NewsHeadline
from analysis_app.indicators import compute_indicators
from analysis_app.sentiment import score_sentiment
from analysis_app.agent import predict, fuse
import pandas as pd
import os

MODEL_PATH = os.path.join(settings.BASE_DIR, "analysis_model.joblib")
FEATURES = ["ma_10", "ma_30", "rsi", "volatility"]


class Command(BaseCommand):
    help = "Backtest recommendations: technical signal vs next-day return (optional: full pipeline with fundamentals/sentiment)"

    def add_arguments(self, parser):
        parser.add_argument("--ticker", default="AAPL")
        parser.add_argument("--days", type=int, default=252, help="Trading days to test")
        parser.add_argument("--full", action="store_true", help="Use full pipeline (fundamentals + sentiment) when data available")

    def handle(self, *args, **opts):
        ticker = (opts.get("ticker") or "AAPL").upper()
        days = max(50, opts.get("days", 252))
        use_full = opts.get("full", False)

        qs = StockPrice.objects.filter(ticker=ticker).order_by("date")
        df = pd.DataFrame([{"date": p.date, "close": p.close} for p in qs])
        if len(df) < 80:
            self.stdout.write(self.style.WARNING("Need 80+ price rows. Import prices first."))
            return
        df["date"] = pd.to_datetime(df["date"])
        df = compute_indicators(df).dropna(subset=FEATURES)
        df["next_ret"] = df["close"].pct_change().shift(-1)

        test_df = df.tail(days).head(-1)
        if not os.path.isfile(MODEL_PATH):
            self.stdout.write(self.style.ERROR("analysis_model.joblib not found. Run train_model.py first."))
            return

        results = []
        for i, row in test_df.iterrows():
            feats = {f: float(row[f]) for f in FEATURES}
            next_ret = row["next_ret"]
            if pd.isna(next_ret):
                continue
            try:
                signal, conf, probs = predict(MODEL_PATH, feats)
                pe = eg = rg = None
                sentiment = None
                if use_full:
                    fund = FundamentalMetric.objects.filter(ticker=ticker).order_by("-period_end").first()
                    if fund:
                        pe, eg, rg = fund.pe_ratio, fund.earnings_growth, fund.revenue_growth
                    news = NewsHeadline.objects.filter(ticker=ticker).order_by("-date")[:5]
                    if news:
                        sentiment = score_sentiment([n.headline for n in news])
                final_signal, _, _ = fuse(signal, conf, pe, eg, rg, sentiment, probs=probs)
                results.append({
                    "signal": final_signal,
                    "next_ret": next_ret,
                    "correct": (final_signal == "BUY" and next_ret > 0.005) or (final_signal == "SELL" and next_ret < -0.005) or (final_signal == "HOLD" and -0.005 <= next_ret <= 0.005),
                })
            except Exception:
                continue

        if not results:
            self.stdout.write(self.style.WARNING("No backtest results."))
            return

        df_res = pd.DataFrame(results)
        accuracy = df_res["correct"].mean()
        buy_count = (df_res["signal"] == "BUY").sum()
        sell_count = (df_res["signal"] == "SELL").sum()
        hold_count = (df_res["signal"] == "HOLD").sum()
        self.stdout.write(self.style.SUCCESS(f"Backtest {ticker} ({len(results)} days)"))
        self.stdout.write(f"  Accuracy (signal vs next-day return): {accuracy:.2%}")
        self.stdout.write(f"  BUY: {buy_count}, HOLD: {hold_count}, SELL: {sell_count}")

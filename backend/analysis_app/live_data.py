import datetime as dt

import pandas as pd
import yfinance as yf

from core.models import StockPrice, FundamentalMetric, NewsHeadline


def _fetch_prices_from_yahoo(ticker: str, lookback_days: int = 365) -> pd.DataFrame:
  """
  Fetch recent daily OHLCV data for a ticker from Yahoo Finance.

  Normalises columns to a simple one-level index with:
  [date, open, high, low, close, volume].
  """
  end = dt.date.today()
  start = end - dt.timedelta(days=lookback_days)

  try:
    df = yf.download(ticker, start=start, end=end, progress=False)
  except Exception:
    return pd.DataFrame()

  if df.empty:
    return df

  df = df.reset_index()

  # yfinance can return either single-level or MultiIndex columns depending
  # on version and options. We flatten everything to simple lowercase names.
  if isinstance(df.columns, pd.MultiIndex):
    flat_cols = []
    for top, _sub in df.columns:
      if str(top).lower() == "date":
        flat_cols.append("date")
      else:
        flat_cols.append(str(top).strip().lower())
    df.columns = flat_cols
  else:
    df.rename(
      columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
      },
      inplace=True,
    )

  return df[["date", "open", "high", "low", "close", "volume"]]


def ensure_prices_for_ticker(ticker: str, min_rows: int = 60) -> bool:
  """
  Ensure we have at least `min_rows` StockPrice rows for this ticker.

  - If enough rows already exist in the DB, do nothing and return True.
  - Otherwise, fetch recent data from Yahoo Finance and bulk-insert it.
  - Returns True if, after this, we have at least `min_rows` rows; False otherwise.
  """
  ticker = (ticker or "").upper().strip()
  if not ticker:
    return False

  existing = StockPrice.objects.filter(ticker=ticker).count()
  if existing >= min_rows:
    return True

  df = _fetch_prices_from_yahoo(ticker)
  if df.empty:
    return existing >= min_rows

  objs = []
  for r in df.itertuples(index=False):
    date_val = getattr(r, "date", None)
    if date_val is None:
      continue

    if hasattr(date_val, "date"):
      date_val = date_val.date()

    try:
      open_val = float(r.open)
      high_val = float(r.high)
      low_val = float(r.low)
      close_val = float(r.close)
      vol_val = int(getattr(r, "volume", 0) or 0)
    except (AttributeError, TypeError, ValueError):
      continue

    objs.append(
      StockPrice(
        ticker=ticker,
        date=date_val,
        open=open_val,
        high=high_val,
        low=low_val,
        close=close_val,
        volume=vol_val,
      )
    )

  if objs:
    StockPrice.objects.bulk_create(objs, ignore_conflicts=True)

  final_count = StockPrice.objects.filter(ticker=ticker).count()
  return final_count >= min_rows


def ensure_fundamentals_and_news(ticker: str, max_news: int = 20) -> None:
  """
  Best-effort fetch of fundamentals (P/E, earnings/revenue growth) and
  recent news headlines for a ticker using Yahoo Finance.

  - If rows already exist in FundamentalMetric / NewsHeadline, we leave them.
  - Any network/API errors are swallowed so the core analysis still works.
  """
  ticker = (ticker or "").upper().strip()
  if not ticker:
    return

  has_fund = FundamentalMetric.objects.filter(ticker=ticker).exists()
  has_news = NewsHeadline.objects.filter(ticker=ticker).exists()
  if has_fund and has_news:
    return

  try:
    y_ticker = yf.Ticker(ticker)
  except Exception:
    return

  # Fundamentals
  if not has_fund:
    try:
      info = y_ticker.info or {}
    except Exception:
      info = {}

    pe = info.get("trailingPE")
    eg = info.get("earningsGrowth")
    rg = info.get("revenueGrowth")

    if any(v is not None for v in (pe, eg, rg)):
      FundamentalMetric.objects.create(
        ticker=ticker,
        period_end=dt.date.today(),
        pe_ratio=pe,
        earnings_growth=eg,
        revenue_growth=rg,
      )

  # News → sentiment
  if not has_news:
    try:
      news_items = getattr(y_ticker, "news", []) or []
    except Exception:
      news_items = []

    objs = []
    today = dt.date.today()
    for item in news_items[:max_news]:
      title = item.get("title") if isinstance(item, dict) else None
      if not title:
        continue
      objs.append(
        NewsHeadline(
          ticker=ticker,
          date=today,
          headline=str(title),
        )
      )

    if objs:
      NewsHeadline.objects.bulk_create(objs, ignore_conflicts=True)


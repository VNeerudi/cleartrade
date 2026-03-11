"""
Live data integration for ClearTrade: prices (technicals), fundamentals, and news (sentiment).
Call refresh_all_live_data(ticker) before analyze when historical CSV data is missing or stale.
"""
import datetime as dt
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import yfinance as yf

from core.models import StockPrice, FundamentalMetric, NewsHeadline

MIN_NEWS_HEADLINES = 5
MAX_HEADLINES_TO_APPEND = 30


def _df_to_price_objs(ticker: str, df: pd.DataFrame) -> list:
    """Build StockPrice instances from normalized OHLCV dataframe."""
    ticker = (ticker or "").upper().strip()
    objs = []
    if df is None or df.empty:
        return objs

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
    return objs


def _fetch_prices_from_yahoo(ticker: str, lookback_days: int = 400) -> pd.DataFrame:
    """Fetch OHLCV via yf.download; normalize columns."""
    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
    except Exception:
        return pd.DataFrame()
    return _normalize_ohlcv_df(df)


def _fetch_prices_from_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    Fetch via Ticker.history — often works when download() returns empty
    (e.g. single ticker vs batch quirks).
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.reset_index()
    # history gives Date, Open, High, Low, Close, Volume
    hist.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
        inplace=True,
    )
    for col in ("open", "high", "low", "close", "volume"):
        if col not in hist.columns:
            return pd.DataFrame()
    return hist[["date", "open", "high", "low", "close", "volume"]]


def _normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.reset_index()
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
    needed = ["date", "open", "high", "low", "close", "volume"]
    if not all(c in df.columns for c in needed):
        return pd.DataFrame()
    return df[needed]


def sync_prices_from_yahoo(ticker: str, min_rows: int = 60) -> bool:
    """
    Always merge latest Yahoo OHLCV into StockPrice so technicals have data
    without relying on imported CSVs. Uses history() then download() fallback.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return False

    df = _fetch_prices_from_history(ticker, period="2y")
    if df.empty:
        df = _fetch_prices_from_yahoo(ticker, lookback_days=500)
    if df.empty:
        return StockPrice.objects.filter(ticker=ticker).count() >= min_rows

    objs = _df_to_price_objs(ticker, df)
    if objs:
        StockPrice.objects.bulk_create(objs, ignore_conflicts=True)

    return StockPrice.objects.filter(ticker=ticker).count() >= min_rows


def ensure_prices_for_ticker(ticker: str, min_rows: int = 60) -> bool:
    """Backward-compatible alias: sync live prices then check count."""
    return sync_prices_from_yahoo(ticker, min_rows=min_rows)


def _yfinance_news_list(y_ticker) -> list:
    items = []
    try:
        raw = getattr(y_ticker, "news", None)
        if callable(raw):
            raw = raw()
        if raw is None:
            raw = []
        items = list(raw) if not isinstance(raw, list) else raw
    except Exception:
        items = []
    return items


def _extract_title_from_news_item(item):
    if isinstance(item, dict):
        title = item.get("title") or item.get("headline") or item.get("summary")
        if title:
            return str(title).strip()
        return None
    if isinstance(item, str) and item.strip():
        return item.strip()
    return None


def _fetch_yahoo_rss_headlines(ticker: str, limit: int = 25):
    ticker = (ticker or "").upper().strip()
    if not ticker or not re.match(r"^[A-Z0-9.\-]+$", ticker):
        return []
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={urllib.parse.quote(ticker)}"
        "&region=US&lang=en-US"
    )
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ClearTrade/1.0 (live sentiment)"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
    except Exception:
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    titles = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag != "item":
            continue
        title_el = None
        for child in elem:
            ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if ctag == "title" and child.text:
                title_el = child.text.strip()
                break
        if title_el and title_el not in titles:
            titles.append(title_el)
        if len(titles) >= limit:
            break
    return titles


def _append_headlines_for_ticker(ticker: str, titles: list, existing_titles: set) -> int:
    today = dt.date.today()
    objs = []
    for title in titles:
        title = (title or "").strip()
        if not title or len(title) < 4 or title in existing_titles:
            continue
        existing_titles.add(title)
        objs.append(
            NewsHeadline(ticker=ticker, date=today, headline=title)
        )
    if not objs:
        return 0
    NewsHeadline.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)


def sync_fundamentals_live(ticker: str) -> None:
    """
    Always pull latest yfinance info and store a new FundamentalMetric row
    so fusion uses current P/E and growth when available.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return
    try:
        y_ticker = yf.Ticker(ticker)
        info = y_ticker.info or {}
    except Exception:
        return
    pe = info.get("trailingPE")
    eg = info.get("earningsGrowth")
    rg = info.get("revenueGrowth")
    if not any(v is not None for v in (pe, eg, rg)):
        return
    FundamentalMetric.objects.create(
        ticker=ticker,
        period_end=dt.date.today(),
        pe_ratio=pe,
        earnings_growth=eg,
        revenue_growth=rg,
    )


def sync_news_live(ticker: str) -> None:
    """
    Always append fresh headlines (yfinance + RSS) with dedupe so sentiment
    uses recent text even when DB had old or no rows.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return
    existing_titles = set(
        NewsHeadline.objects.filter(ticker=ticker).values_list("headline", flat=True)
    )
    try:
        y_ticker = yf.Ticker(ticker)
    except Exception:
        y_ticker = None

    if y_ticker is not None:
        yf_titles = []
        for item in _yfinance_news_list(y_ticker)[:MAX_HEADLINES_TO_APPEND]:
            t = _extract_title_from_news_item(item)
            if t:
                yf_titles.append(t)
        if yf_titles:
            _append_headlines_for_ticker(ticker, yf_titles, existing_titles)

    rss_titles = _fetch_yahoo_rss_headlines(ticker, limit=MAX_HEADLINES_TO_APPEND)
    if rss_titles:
        _append_headlines_for_ticker(ticker, rss_titles, existing_titles)


def refresh_all_live_data(ticker: str) -> bool:
    """
    Single entry point before analyze:
    1. Sync OHLCV from Yahoo (history + download fallback) → technicals
    2. Sync fundamentals from yfinance info → fusion / fundamentals panel
    3. Sync news headlines → sentiment

    Returns True if at least min_rows prices exist after sync.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return False
    ok = sync_prices_from_yahoo(ticker, min_rows=60)
    sync_fundamentals_live(ticker)
    sync_news_live(ticker)
    return ok


def ensure_fundamentals_and_news(ticker: str, max_news: int = 25) -> None:
    """
    Legacy path: fundamentals only if missing; news only if count low.
    Prefer refresh_all_live_data() for accurate live results.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return
    has_fund = FundamentalMetric.objects.filter(ticker=ticker).exists()
    news_count = NewsHeadline.objects.filter(ticker=ticker).count()
    if has_fund and news_count >= MIN_NEWS_HEADLINES:
        return
    try:
        y_ticker = yf.Ticker(ticker)
    except Exception:
        y_ticker = None
    if not has_fund and y_ticker is not None:
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
    if news_count >= MIN_NEWS_HEADLINES:
        return
    existing_titles = set(
        NewsHeadline.objects.filter(ticker=ticker).values_list("headline", flat=True)
    )
    if y_ticker is not None:
        yf_titles = []
        for item in _yfinance_news_list(y_ticker)[:max_news]:
            t = _extract_title_from_news_item(item)
            if t:
                yf_titles.append(t)
        if yf_titles:
            _append_headlines_for_ticker(ticker, yf_titles, existing_titles)
    if NewsHeadline.objects.filter(ticker=ticker).count() >= MIN_NEWS_HEADLINES:
        return
    rss_titles = _fetch_yahoo_rss_headlines(ticker, limit=max_news)
    if rss_titles:
        _append_headlines_for_ticker(ticker, rss_titles, existing_titles)

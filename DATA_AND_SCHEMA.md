# Data Sources and Database Schema (Paper §6.1, §8)

## Real-time / API data

The backend supports **on-the-fly** data when the database has insufficient history:

- **Stock prices (technicals):** `refresh_all_live_data(ticker)` always syncs **Yahoo OHLCV** into `StockPrice` using `Ticker.history(period="2y")` first, then `yf.download` if needed—so MA/RSI/volatility work **without CSV imports** as long as the symbol exists on Yahoo.
- **Fundamentals:** Each analyze run calls `sync_fundamentals_live`, which inserts a fresh `FundamentalMetric` row from **yfinance `info`** (trailingPE, earningsGrowth, revenueGrowth) so fusion uses **current** valuation/growth when available.
- **Sentiment:** `sync_news_live` always appends **deduped** headlines from yfinance `.news` and from **Yahoo RSS** so the latest run scores **recent** news even when the DB started empty.
- **Legacy:** `ensure_fundamentals_and_news` remains for minimal fetch-only-when-missing behavior; the analyze API uses `refresh_all_live_data` for full live integration.

Historical data can still be loaded via management commands (see README):

- `import_prices` – OHLCV from CSV
- `import_fundamentals` – P/E, earnings growth, revenue growth
- `import_news_events` – financial news headlines

## Database schema (Paper §6.1)

The project uses **SQLite** by default; **MySQL** is supported via environment variables for deployment.

| Table / model       | Purpose (paper mapping) |
|---------------------|--------------------------|
| **StockPrice**      | Raw OHLCV price history for technical analysis |
| **FundamentalMetric** | Valuation and growth metrics (P/E, earnings growth, revenue growth) |
| **NewsHeadline**    | Financial news headlines for sentiment analysis |
| **Recommendation** | Fused BUY/HOLD/SELL with confidence, explanation, and stored indicators (MA, RSI, volatility, sentiment, P/E, growth) for traceability and evaluation |

This structure supports **traceability** and **backtesting** (paper §4, §6.1).

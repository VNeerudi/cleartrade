# Data Sources and Database Schema (Paper §6.1, §8)

## Real-time / API data

The backend supports **on-the-fly** data when the database has insufficient history:

- **Stock prices:** `analysis_app/live_data.py` uses **Yahoo Finance** (`yfinance`) to fetch recent OHLCV for a ticker when `StockPrice` has fewer than 60 rows. This aligns with the paper’s “Real-Time Market Data Integration” and use of open market data (Yahoo Finance, Kaggle).
- **Fundamentals and news:** `ensure_fundamentals_and_news(ticker)` attempts to fetch current fundamentals and recent headlines for well-known tickers so the UI shows fundamentals and sentiment even without imported CSVs.

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

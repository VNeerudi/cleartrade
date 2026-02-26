from __future__ import annotations

import csv
from datetime import date, timedelta
import random
from typing import Iterable, List, Dict


def generate_dummy_prices(
    ticker: str = "AAPL",
    start: date = date(2024, 1, 1),
    days: int = 200,
    base_price: float = 150.0,
) -> List[Dict[str, object]]:
    """
    Generate a simple random-walk OHLCV price series suitable for local demos.

    This is ONLY for educational/testing use so the ClearTrade pipeline has
    enough rows to compute indicators. It does not represent real market data.
    """
    rows: List[Dict[str, object]] = []
    price = base_price

    for i in range(days):
        d = start + timedelta(days=i)
        # Skip weekends to roughly mimic trading days.
        if d.weekday() >= 5:
            continue

        # Random daily move within +/- 2%
        move = random.uniform(-0.02, 0.02)
        open_price = price
        close_price = max(1.0, price * (1 + move))

        high_price = max(open_price, close_price) * (1 + random.uniform(0.0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0.0, 0.01))

        volume = random.randint(1_000_000, 5_000_000)

        rows.append(
            {
                "Date": d.isoformat(),
                "Ticker": ticker.upper(),
                "Open": round(open_price, 2),
                "High": round(high_price, 2),
                "Low": round(low_price, 2),
                "Close": round(close_price, 2),
                "Volume": volume,
            }
        )

        price = close_price

    return rows


def write_prices_csv(path: str, rows: Iterable[Dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """
    Generate dummy OHLCV data for a small basket of tickers that you
    are likely to test during the demo. This does NOT try to cover the
    entire stock market, but shows how any ticker can be supported once
    data are available.
    """
    tickers = ["AAPL", "MSFT", "AMZN", "GOOG", "META"]
    all_rows: List[Dict[str, object]] = []

    for t in tickers:
        base = {
            "AAPL": 150.0,
            "MSFT": 320.0,
            "AMZN": 130.0,
            "GOOG": 140.0,
            "META": 300.0,
        }.get(t, 100.0)
        series = generate_dummy_prices(ticker=t, base_price=base)
        all_rows.extend(series)

    path = "dummy_prices_demo.csv"
    write_prices_csv(path, all_rows)
    print(f"Wrote {len(all_rows)} dummy price rows for {', '.join(tickers)} to {path}")


if __name__ == "__main__":
    main()

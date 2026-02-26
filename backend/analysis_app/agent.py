import numpy as np
import joblib

FEATURES = ["ma_10", "ma_30", "rsi", "volatility"]
LABELS = {0: "SELL", 1: "HOLD", 2: "BUY"}


def predict(model_path: str, feats: dict):
    """
    Load the trained classifier (Logistic Regression or Random Forest)
    and produce a discrete BUY/HOLD/SELL signal plus class probabilities.
    """
    model = joblib.load(model_path)
    x = np.array([[feats[f] for f in FEATURES]])
    probs = model.predict_proba(x)[0]
    idx = int(np.argmax(probs))
    return LABELS[idx], float(np.max(probs)), probs.tolist()


def summarize_for_human(
    signal: str,
    confidence: float,
    feats: dict,
    pe_ratio,
    earnings_growth,
    revenue_growth,
    sentiment: float,
) -> str:
    """
    Create a short, plain-language summary that a non-expert can understand.
    """
    pieces = []

    # Overall recommendation
    if signal == "BUY":
        pieces.append("The system suggests this stock is a good buy right now.")
    elif signal == "SELL":
        pieces.append("The system suggests it may be a good time to sell this stock.")
    else:
        pieces.append("The system suggests holding this stock rather than buying or selling aggressively.")

    # Confidence
    pieces.append(f"The confidence in this view is about {confidence * 100:.0f}% based on recent market data.")

    # Simple technical description
    ma10 = feats.get("ma_10")
    ma30 = feats.get("ma_30")
    rsi = feats.get("rsi")

    if ma10 is not None and ma30 is not None:
        if ma10 > ma30:
            pieces.append("Recent prices are above the longer-term average, which usually means an upward trend.")
        elif ma10 < ma30:
            pieces.append("Recent prices are below the longer-term average, which usually means a weaker trend.")

    if rsi is not None:
        if rsi > 70:
            pieces.append("The RSI indicator is high, meaning the stock may be overbought in the very short term.")
        elif rsi < 30:
            pieces.append("The RSI indicator is low, meaning the stock may be oversold in the very short term.")

    # Fundamentals
    if pe_ratio is not None:
        if pe_ratio > 35:
            pieces.append("The valuation (P/E ratio) is quite high, so the stock may be expensive compared to earnings.")
        elif pe_ratio < 15:
            pieces.append("The valuation (P/E ratio) is relatively low, which can be attractive if earnings are stable.")

    if earnings_growth is not None and earnings_growth > 0:
        pieces.append("Company earnings have been growing, which supports a positive outlook.")
    if revenue_growth is not None and revenue_growth > 0:
        pieces.append("Company revenue has been growing, another good long‑term sign.")

    # Sentiment
    if sentiment is not None:
        if sentiment > 0.1:
            pieces.append("Recent news sentiment around the stock is mostly positive.")
        elif sentiment < -0.1:
            pieces.append("Recent news sentiment around the stock is mostly negative.")

    return " ".join(pieces)


def fuse(
    signal: str,
    conf: float,
    pe_ratio,
    earnings_growth,
    revenue_growth,
    sentiment: float,
):
    """
    Agent-style fusion of technical, fundamental, and sentiment signals.

    - Starts from the ML model's BUY/HOLD/SELL signal and probability.
    - Adjusts confidence up/down based on valuation and growth metrics.
    - Incorporates news sentiment as contextual evidence.
    - Returns a human-readable explanation string that traces these steps.
    """
    reasons: list[str] = []
    confidence = conf

    reasons.append(f"Technical model suggests {signal} (probability={conf:.2f}).")

    # Fundamental validation
    if pe_ratio is not None and signal == "BUY" and pe_ratio > 35:
        confidence *= 0.85
        reasons.append("High P/E may indicate possible overvaluation, so BUY confidence is reduced.")
    if earnings_growth is not None and earnings_growth > 0 and signal == "BUY":
        confidence *= 1.05
        reasons.append("Positive earnings growth supports the BUY signal.")
    if revenue_growth is not None and revenue_growth < 0 and signal == "BUY":
        confidence *= 0.90
        reasons.append("Negative revenue growth weakens the BUY case.")

    # Sentiment context
    if sentiment > 0.2:
        confidence *= 1.05
        reasons.append("Overall news sentiment is positive, supporting the recommendation.")
    elif sentiment < -0.2:
        confidence *= 0.90
        reasons.append("Overall news sentiment is negative, reducing confidence in the signal.")

    confidence = float(max(0.0, min(1.0, confidence)))
    reasons.append(
        "Key drivers considered: moving-average trend, RSI level, volatility, valuation, earnings/revenue growth, and news sentiment."
    )

    explanation = " ".join(reasons)
    return signal, confidence, explanation
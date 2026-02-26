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
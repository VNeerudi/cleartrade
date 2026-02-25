import numpy as np
import joblib

FEATURES = ["ma_10","ma_30","rsi","volatility"]
LABELS = {0:"SELL", 1:"HOLD", 2:"BUY"}

def predict(model_path: str, feats: dict):
    model = joblib.load(model_path)
    x = np.array([[feats[f] for f in FEATURES]])
    probs = model.predict_proba(x)[0]
    idx = int(np.argmax(probs))
    return LABELS[idx], float(np.max(probs)), probs.tolist()

def fuse(signal: str, conf: float, pe_ratio, earnings_growth, revenue_growth, sentiment: float):
    reasons = []
    confidence = conf

    reasons.append(f"Technical model suggests {signal} (probability={conf:.2f}).")

    # Fundamental validation
    if pe_ratio is not None and signal == "BUY" and pe_ratio > 35:
        confidence *= 0.85
        reasons.append("High P/E may indicate overvaluation → confidence reduced.")
    if earnings_growth is not None and earnings_growth > 0 and signal == "BUY":
        confidence *= 1.05
        reasons.append("Positive earnings growth supports BUY.")
    if revenue_growth is not None and revenue_growth < 0 and signal == "BUY":
        confidence *= 0.90
        reasons.append("Negative revenue growth reduces confidence.")

    # Sentiment context
    if sentiment > 0.2:
        confidence *= 1.05
        reasons.append("Positive news sentiment supports the recommendation.")
    elif sentiment < -0.2:
        confidence *= 0.90
        reasons.append("Negative news sentiment reduces confidence.")

    confidence = float(max(0.0, min(1.0, confidence)))
    reasons.append("Key factors: MA trend, RSI level, volatility, fundamentals, and sentiment.")

    return signal, confidence, " ".join(reasons)
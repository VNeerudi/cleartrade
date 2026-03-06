import numpy as np
import joblib

FEATURES = ["ma_10", "ma_30", "rsi", "volatility"]
LABELS = {0: "SELL", 1: "HOLD", 2: "BUY"}

# Paper §6.4: Decision Fusion Agent rules
# If Technical_Prob(Buy) > 0.65 AND Fundamental_Score > 0.6 AND Sentiment >= 0 → BUY
# If signals conflict → HOLD
BUY_PROB_THRESHOLD = 0.65
FUNDAMENTAL_SCORE_THRESHOLD = 0.6
SENTIMENT_THRESHOLD = 0.0


def compute_fundamental_score(pe_ratio, earnings_growth, revenue_growth) -> float | None:
    """
    Fundamental Agent: financial strength score in [0, 1] from valuation and growth.
    Paper: valuation ratios, earnings growth, leverage metrics.
    """
    if pe_ratio is None and earnings_growth is None and revenue_growth is None:
        return None
    score = 0.5  # neutral baseline
    n = 0
    if pe_ratio is not None:
        # Prefer moderate P/E (15–25); penalize very high or very low
        if 15 <= pe_ratio <= 25:
            score += 0.2
        elif pe_ratio > 35:
            score -= 0.15
        n += 1
    if earnings_growth is not None:
        if earnings_growth > 0.1:
            score += 0.15
        elif earnings_growth < -0.1:
            score -= 0.15
        n += 1
    if revenue_growth is not None:
        if revenue_growth > 0.05:
            score += 0.15
        elif revenue_growth < -0.05:
            score -= 0.15
        n += 1
    if n:
        score = max(0.0, min(1.0, score))
    return score


def predict(model_path: str, feats: dict, feats_sequence: np.ndarray | None = None):
    """
    Technical Agent: produce BUY/HOLD/SELL from ML model.
    If feats_sequence is provided (shape [SEQUENCE_LEN, 4]) and LSTM model exists, use LSTM;
    otherwise use Logistic Regression / Random Forest from model_path.
    """
    if feats_sequence is not None:
        try:
            from analysis_app.lstm_model import predict_lstm
            out = predict_lstm(feats_sequence)
            if out is not None:
                return out
        except Exception:
            pass
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
    probs: list | None = None,
):
    """
    Decision Fusion Agent (paper §6.4): combine Technical, Fundamental, and Sentiment agents.
    Rule: If Technical_Prob(Buy) > 0.65 AND Fundamental_Score > 0.6 AND Sentiment >= 0 → BUY;
    if signals conflict → HOLD.
    """
    reasons: list[str] = []
    # probs order: [SELL, HOLD, BUY] per LABELS
    prob_buy = probs[2] if probs and len(probs) > 2 else (conf if signal == "BUY" else 0.0)
    fundamental_score = compute_fundamental_score(pe_ratio, earnings_growth, revenue_growth)
    sentiment_ok = sentiment is None or sentiment >= SENTIMENT_THRESHOLD
    tech_buy_strong = signal == "BUY" and prob_buy >= BUY_PROB_THRESHOLD
    fund_ok = fundamental_score is None or fundamental_score >= FUNDAMENTAL_SCORE_THRESHOLD

    # Paper rule: all three agree for BUY
    if tech_buy_strong and fund_ok and sentiment_ok:
        final_signal = "BUY"
        confidence = min(1.0, conf * 1.05)
        reasons.append(
            f"Technical agent suggests BUY (probability={prob_buy:.2f}). "
            f"Fundamental score {fundamental_score:.2f} and sentiment support the signal."
        )
    elif signal == "SELL" and (
        (fundamental_score is not None and fundamental_score < 0.4)
        or (sentiment is not None and sentiment < -0.2)
    ):
        final_signal = "SELL"
        confidence = min(1.0, conf * 1.05)
        reasons.append(
            f"Technical agent suggests SELL (probability={conf:.2f}). "
            "Fundamentals or sentiment reinforce caution."
        )
    elif (signal == "BUY" and (not fund_ok or not sentiment_ok)) or (
        signal == "SELL" and fund_ok and (sentiment is None or sentiment >= 0)
    ):
        # Conflict → HOLD (paper: "If signals conflict → HOLD")
        final_signal = "HOLD"
        confidence = 0.55
        reasons.append(
            f"Technical agent suggests {signal} (probability={conf:.2f}), "
            "but fundamental or sentiment signals conflict; decision fusion yields HOLD for caution."
        )
    else:
        final_signal = signal
        confidence = conf
        reasons.append(f"Technical model suggests {signal} (probability={conf:.2f}).")

    if fundamental_score is not None:
        reasons.append(f"Fundamental score = {fundamental_score:.2f} (0–1 scale).")
    if sentiment is not None:
        reasons.append(f"News sentiment = {sentiment:.2f} (positive > 0).")
    reasons.append(
        "Key drivers: moving averages, RSI, volatility, valuation, earnings/revenue growth, and news sentiment."
    )

    confidence = float(max(0.0, min(1.0, confidence)))
    explanation = " ".join(reasons)
    return final_signal, confidence, explanation
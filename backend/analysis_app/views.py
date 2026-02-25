from rest_framework.decorators import api_view
from rest_framework.response import Response
import pandas as pd

from core.models import StockPrice, FundamentalMetric, NewsHeadline, Recommendation
from analysis_app.indicators import compute_indicators
from analysis_app.sentiment import score_sentiment
from analysis_app.agent import predict, fuse

MODEL_PATH = "analysis_model.joblib"

@api_view(["GET"])
def analyze(request):
    ticker = request.query_params.get("ticker", "").upper().strip()
    if not ticker:
        return Response({"error": "ticker is required"}, status=400)

    qs = StockPrice.objects.filter(ticker=ticker).order_by("date")
    if qs.count() < 60:
        return Response({"error": "Need at least 60 rows of prices for indicators."}, status=400)

    df = pd.DataFrame([{"date": p.date, "close": p.close} for p in qs])
    df["date"] = pd.to_datetime(df["date"])
    df = compute_indicators(df).dropna()
    latest = df.iloc[-1]

    feats = {
        "ma_10": float(latest["ma_10"]),
        "ma_30": float(latest["ma_30"]),
        "rsi": float(latest["rsi"]),
        "volatility": float(latest["volatility"]),
    }

    fund = FundamentalMetric.objects.filter(ticker=ticker).order_by("-period_end").first()
    pe = fund.pe_ratio if fund else None
    eg = fund.earnings_growth if fund else None
    rg = fund.revenue_growth if fund else None

    news = NewsHeadline.objects.filter(ticker=ticker).order_by("-date")[:10]
    sentiment = score_sentiment([n.headline for n in news])

    signal, conf, probs = predict(MODEL_PATH, feats)
    final_signal, final_conf, explanation = fuse(signal, conf, pe, eg, rg, sentiment)

    rec = Recommendation.objects.create(
        ticker=ticker,
        signal=final_signal,
        confidence=final_conf,
        explanation=explanation,
        ma_10=feats["ma_10"],
        ma_30=feats["ma_30"],
        rsi=feats["rsi"],
        volatility=feats["volatility"],
        sentiment=sentiment,
        pe_ratio=pe,
        earnings_growth=eg,
        revenue_growth=rg,
    )

    return Response({
        "ticker": ticker,
        "recommendation": rec.signal,
        "confidence": rec.confidence,
        "explanation": rec.explanation,
        "class_probabilities": probs,
        "features": feats,
        "fundamentals": {"pe_ratio": pe, "earnings_growth": eg, "revenue_growth": rg},
        "sentiment": sentiment,
    })

@api_view(["GET"])
def history(request):
    ticker = request.query_params.get("ticker", "").upper().strip()
    qs = Recommendation.objects.filter(ticker=ticker).order_by("-created_at")[:20]
    return Response({
        "ticker": ticker,
        "history": [
            {"created_at": r.created_at, "signal": r.signal, "confidence": r.confidence, "explanation": r.explanation}
            for r in qs
        ]
    })

@api_view(["POST"])
def chat(request):
    ticker = str(request.data.get("ticker", "")).upper().strip()
    question = str(request.data.get("question", "")).strip().lower()
    if not ticker or not question:
        return Response({"error": "ticker and question are required"}, status=400)

    last = Recommendation.objects.filter(ticker=ticker).order_by("-created_at").first()
    if not last:
        return Response({"answer": "No recommendation found. Run Analyze first."})

    if "why" in question or "explain" in question:
        return Response({"answer": last.explanation})
    if "confidence" in question:
        return Response({"answer": f"Confidence = {last.confidence:.2f}."})
    if "rsi" in question:
        return Response({"answer": f"RSI = {last.rsi:.2f}. Above 70 is overbought; below 30 is oversold."})
    if "sentiment" in question or "news" in question:
        return Response({"answer": f"Sentiment score = {last.sentiment:.2f} (positive>0, negative<0)."})
    return Response({"answer": "Try: 'Why?', 'Confidence?', 'RSI?', 'Sentiment?'."})
import datetime as dt

from rest_framework.decorators import api_view
from rest_framework.response import Response
import pandas as pd

from core.models import StockPrice, FundamentalMetric, NewsHeadline, Recommendation
from analysis_app.indicators import compute_indicators
from analysis_app.sentiment import score_sentiment
from analysis_app.agent import (
    predict,
    fuse,
    summarize_for_human,
    compute_fundamental_score,
    FEATURES as INDICATOR_NAMES,
)
from analysis_app.live_data import refresh_all_live_data

MODEL_PATH = "analysis_model.joblib"
LSTM_SEQUENCE_LEN = 20

@api_view(["GET"])
def analyze(request):
    ticker = request.query_params.get("ticker", "").upper().strip()
    if not ticker:
        return Response({"error": "ticker is required"}, status=400)

    # Live data first: Yahoo OHLCV (technicals), yfinance info (fundamentals),
    # RSS + yfinance news (sentiment). Works without imported CSV history.
    if not refresh_all_live_data(ticker):
        return Response(
            {
                "error": "Could not load enough price history for this ticker. "
                "Check the symbol on Yahoo Finance or try another ticker.",
            },
            status=400,
        )

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
    # Build sequence for LSTM if available (last LSTM_SEQUENCE_LEN rows)
    feats_sequence = None
    if len(df) >= LSTM_SEQUENCE_LEN:
        try:
            feats_sequence = df.iloc[-LSTM_SEQUENCE_LEN:][list(INDICATOR_NAMES)].values.astype("float32")
        except Exception:
            pass

    fund = FundamentalMetric.objects.filter(ticker=ticker).order_by("-period_end").first()
    pe = fund.pe_ratio if fund else None
    eg = fund.earnings_growth if fund else None
    rg = fund.revenue_growth if fund else None

    # Prefer headlines from the last 14 days (live/recency); fall back if too few
    cutoff = dt.date.today() - dt.timedelta(days=14)
    news_qs = (
        NewsHeadline.objects.filter(ticker=ticker, date__gte=cutoff)
        .order_by("-date", "-id")[:10]
    )
    news = list(news_qs)
    if len(news) < 3:
        news = list(
            NewsHeadline.objects.filter(ticker=ticker).order_by("-date", "-id")[:10]
        )
    news_headlines_used = len(news)
    # Expose actual headlines so the UI can show what drove sentiment (descriptive, not just a score).
    news_samples = [
        {"headline": n.headline, "date": n.date.isoformat() if n.date else None}
        for n in news
    ]
    if news:
        sentiment = score_sentiment([n.headline for n in news])
    else:
        sentiment = None

    signal, conf, probs = predict(MODEL_PATH, feats, feats_sequence=feats_sequence)
    final_signal, final_conf, explanation = fuse(
        signal, conf, pe, eg, rg, sentiment, probs=probs
    )
    fundamental_score = compute_fundamental_score(pe, eg, rg)

    summary = summarize_for_human(
        final_signal,
        final_conf,
        feats,
        pe,
        eg,
        rg,
        sentiment,
    )

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

    from analysis_app.explainability import get_feature_importance, get_shap_values

    feature_importance = get_feature_importance(MODEL_PATH, feats, probs)
    shap_values = get_shap_values(MODEL_PATH, feats)

    return Response({
        "ticker": ticker,
        "recommendation": rec.signal,
        "confidence": rec.confidence,
        "explanation": rec.explanation,
        "summary": summary,
        "class_probabilities": probs,
        "features": feats,
        "fundamentals": {"pe_ratio": pe, "earnings_growth": eg, "revenue_growth": rg},
        "fundamental_score": fundamental_score,
        "sentiment": sentiment,
        "news_headlines_used": news_headlines_used,
        "news_samples": news_samples,
        "feature_importance": feature_importance,
        "shap_values": shap_values,
    })

@api_view(["GET"])
def series(request):
    """
    Last N days of close prices for charting (chronological order).
    Requires ticker to have rows in StockPrice (run Analyze once to sync).
    """
    ticker = request.query_params.get("ticker", "").upper().strip()
    if not ticker:
        return Response({"error": "ticker is required"}, status=400)
    try:
        limit = min(int(request.query_params.get("limit", 90)), 365)
    except ValueError:
        limit = 90
    qs = StockPrice.objects.filter(ticker=ticker).order_by("-date")[:limit]
    rows = list(qs)
    rows.reverse()
    return Response({
        "ticker": ticker,
        "points": [
            {"date": p.date.isoformat(), "close": float(p.close)}
            for p in rows
        ],
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
    from analysis_app.chat_agent import build_chat_answer, suggested_prompts

    ticker = str(request.data.get("ticker", "")).upper().strip()
    question = str(request.data.get("question", "")).strip()
    if not ticker or not question:
        return Response({"error": "ticker and question are required"}, status=400)

    last = Recommendation.objects.filter(ticker=ticker).order_by("-created_at").first()
    if not last:
        return Response({"answer": "No recommendation found. Run Analyze first."})

    answer = build_chat_answer(last, question)
    return Response({"answer": answer, "suggested_prompts": suggested_prompts()})
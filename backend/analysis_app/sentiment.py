"""
Sentiment analysis for financial headlines (paper §4: FinBERT or TF-IDF + LR).
Uses: optional FinBERT → TF-IDF+LR if trained → keyword fallback.
"""
from analysis_app.sentiment_model import (
    score_sentiment_finbert,
    score_sentiment_tfidf_lr,
)


def score_sentiment(headlines: list[str]) -> float:
    if not headlines:
        return 0.0
    # Optional FinBERT when transformers/torch available
    finbert_score = score_sentiment_finbert(headlines)
    if finbert_score is not None:
        return finbert_score
    # TF-IDF + LR if model exists, else keyword fallback
    return score_sentiment_tfidf_lr(headlines)

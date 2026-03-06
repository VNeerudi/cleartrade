"""
Sentiment model: TF-IDF + Logistic Regression (paper §4, §8.3).
Optional FinBERT when transformers/torch available.
"""
import os
import re
import joblib
from typing import List

# Default: keyword-based weak labels for training TF-IDF+LR when no labeled data
POS = {"gain", "gains", "up", "rise", "surge", "strong", "record", "profit", "growth", "bullish", "upgrade"}
NEG = {"down", "drop", "fall", "plunge", "weak", "loss", "decline", "bearish", "downgrade", "lawsuit"}

SENTIMENT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "sentiment_model.joblib")
SENTIMENT_VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), "sentiment_vectorizer.joblib")


def _tokenize(text: str) -> List[str]:
    text = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return [t for t in text.split() if len(t) > 1]


def _keyword_score(headline: str) -> float:
    tokens = _tokenize(headline)
    p = sum(1 for t in tokens if t in POS)
    n = sum(1 for t in tokens if t in NEG)
    total = p + n
    if total == 0:
        return 0.0
    return (p - n) / total


def score_sentiment_tfidf_lr(headlines: List[str]) -> float:
    """
    Score sentiment using trained TF-IDF + Logistic Regression if available.
    Returns a single aggregate score in [-1, 1] (positive = bullish).
    """
    if not headlines:
        return 0.0
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        model = joblib.load(SENTIMENT_MODEL_PATH)
        vectorizer = joblib.load(SENTIMENT_VECTORIZER_PATH)
        X = vectorizer.transform(headlines)
        # Model predicts 0=neg, 1=neutral, 2=pos; we map to score
        preds = model.predict(X)
        probs = model.predict_proba(X) if hasattr(model, "predict_proba") else None
        if probs is not None and probs.shape[1] >= 3:
            # score = P(pos) - P(neg)
            scores = probs[:, 2] - probs[:, 0]
        else:
            scores = np.where(preds == 2, 0.5, np.where(preds == 0, -0.5, 0.0))
        return float(np.clip(np.mean(scores), -1.0, 1.0))
    except Exception:
        return _score_keyword_fallback(headlines)


def _score_keyword_fallback(headlines: List[str]) -> float:
    scores = [_keyword_score(h) for h in headlines]
    return float(sum(scores) / len(scores)) if scores else 0.0


def score_sentiment_finbert(headlines: List[str]) -> float | None:
    """
    Optional: use FinBERT-style model if transformers/torch installed.
    Returns aggregate score in [-1, 1] or None if not available.
    """
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        model_name = "ProsusAI/finbert"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model.eval()
        scores_list = []
        for text in headlines[:20]:  # limit for speed
            if not (text or "").strip():
                continue
            inputs = tokenizer(text[:512], return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                out = model(**inputs)
            logits = out.logits
            # finbert: 0=positive, 1=negative, 2=neutral
            probs = torch.softmax(logits, dim=1)[0]
            s = float(probs[0].item() - probs[1].item())  # pos - neg
            scores_list.append(s)
        if not scores_list:
            return None
        return float(sum(scores_list) / len(scores_list))
    except Exception:
        return None


def train_sentiment_model(texts: List[str], labels: List[int] | None = None):
    """
    Train TF-IDF + Logistic Regression. If labels is None, use keyword-based weak labels:
    2=positive, 0=negative, 1=neutral (thresholds on _keyword_score).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    if not texts:
        return
    if labels is None:
        labels = []
        for t in texts:
            s = _keyword_score(t)
            if s > 0.15:
                labels.append(2)
            elif s < -0.15:
                labels.append(0)
            else:
                labels.append(1)
    vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 2), min_df=1)
    X = vectorizer.fit_transform(texts)
    y = labels
    model = LogisticRegression(max_iter=500)
    model.fit(X, y)
    joblib.dump(model, SENTIMENT_MODEL_PATH)
    joblib.dump(vectorizer, SENTIMENT_VECTORIZER_PATH)

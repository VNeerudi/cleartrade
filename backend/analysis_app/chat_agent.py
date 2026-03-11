"""
Rule-based explainability chat: answers from the latest Recommendation row.
Purpose: let users ask natural follow-ups without calling an LLM—fast, deterministic,
and grounded in the same data that produced the signal.
"""
from __future__ import annotations

from core.models import Recommendation


def _fmt(x, nd=2):
    if x is None:
        return None
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None


def build_chat_answer(last: Recommendation, question: str) -> str:
    """
    Map user question (lowercased) to an answer using stored recommendation fields.
    Order matters: more specific checks before generic ones.
    """
    q = (question or "").strip().lower()
    if not q:
        return "Ask me about the recommendation, confidence, RSI, sentiment, fundamentals, or moving averages."

    # --- Signal / recommendation ---
    if any(
        w in q
        for w in (
            "buy or sell",
            "buy sell",
            "what should i",
            "recommendation",
            "signal",
            "what do you recommend",
            "verdict",
            "decision",
        )
    ) or (q.strip() in ("buy?", "sell?", "hold?")):
        return (
            f"Latest signal for {last.ticker}: {last.signal} with confidence {last.confidence:.1%}. "
            f"{last.explanation}"
        )

    # --- Why / explain ---
    if "why" in q or "explain" in q or "reason" in q:
        return last.explanation

    # --- Confidence ---
    if "confidence" in q or "how sure" in q or "certain" in q:
        return (
            f"Confidence is {last.confidence:.1%} (0–100%). "
            "Higher means the fused model (technical + fundamentals + sentiment) agreed more strongly."
        )

    # --- RSI ---
    if "rsi" in q or "overbought" in q or "oversold" in q:
        r = _fmt(last.rsi, 1)
        if r is None:
            return "RSI wasn't stored for this run."
        zone = "overbought territory" if r >= 70 else "oversold territory" if r <= 30 else "neutral zone"
        return f"RSI = {r}. Above 70 is typically overbought; below 30 oversold. Currently in {zone}."

    # --- Sentiment / news ---
    if "sentiment" in q or "news" in q or "headline" in q:
        if last.sentiment is None:
            return (
                "No sentiment score was stored—usually because no headlines were available. "
                "Re-run Analyze after news is ingested (RSS/yfinance) or import a news CSV."
            )
        s = last.sentiment
        tone = "positive" if s > 0.1 else "negative" if s < -0.1 else "roughly neutral"
        return f"Sentiment score = {s:.2f} (positive > 0, negative < 0). Interpretation: {tone} for recent news."

    # --- Fundamentals ---
    if any(
        w in q
        for w in (
            "fundamental",
            "p/e",
            "pe ratio",
            "valuation",
            "earnings growth",
            "revenue growth",
            "growth",
        )
    ):
        parts = []
        if last.pe_ratio is not None:
            parts.append(f"P/E ≈ {_fmt(last.pe_ratio, 1)}")
        if last.earnings_growth is not None:
            parts.append(f"earnings growth ≈ {last.earnings_growth * 100:.1f}%")
        if last.revenue_growth is not None:
            parts.append(f"revenue growth ≈ {last.revenue_growth * 100:.1f}%")
        if parts:
            return "Fundamentals used in fusion: " + "; ".join(parts) + "."
        return "No fundamentals were stored for this run (Yahoo/yfinance may not have returned metrics for this ticker)."

    # --- Moving averages / trend ---
    if any(w in q for w in ("ma", "moving average", "trend", "momentum")):
        m10 = _fmt(last.ma_10, 2)
        m30 = _fmt(last.ma_30, 2)
        if m10 is None or m30 is None:
            return "Moving averages weren't stored for this run."
        if m10 > m30:
            trend = "short-term average above longer-term—often read as upward momentum."
        elif m10 < m30:
            trend = "short-term average below longer-term—often read as weaker near-term trend."
        else:
            trend = "MA-10 and MA-30 are close—trend is mixed."
        return f"MA-10 = {m10}, MA-30 = {m30}. {trend}"

    # --- Volatility ---
    if "volatil" in q or "risk" in q or "swing" in q:
        v = _fmt(last.volatility, 4)
        if v is None:
            return "Volatility wasn't stored for this run."
        return (
            f"Annualized volatility (from recent returns) ≈ {v}. "
            "Higher means larger typical price swings."
        )

    # --- Summary / overview ---
    if any(w in q for w in ("summary", "overview", "recap", "everything", "all", "what did you use")):
        lines = [
            f"{last.ticker} → {last.signal} at {last.confidence:.1%} confidence.",
            last.explanation,
        ]
        if last.rsi is not None:
            lines.append(f"RSI {_fmt(last.rsi, 1)}; MA-10 {_fmt(last.ma_10, 2)} vs MA-30 {_fmt(last.ma_30, 2)}.")
        if last.sentiment is not None:
            lines.append(f"Sentiment {_fmt(last.sentiment, 2)}.")
        return "\n\n".join(lines)

    # --- Help ---
    if "help" in q or "what can you" in q or "what do you do" in q:
        return (
            "I answer from your latest Analyze run only—no live LLM. Try asking about:\n"
            "• Why / reason for the signal\n"
            "• Confidence / how sure\n"
            "• RSI / overbought or oversold\n"
            "• Sentiment / news tone\n"
            "• Fundamentals / P/E, growth\n"
            "• Moving averages / trend\n"
            "• Volatility / risk\n"
            "• Summary / full recap"
        )

    # --- Greeting / thanks ---
    if q in ("hi", "hello", "hey", "thanks", "thank you"):
        return f"Hi—ask me anything about the last {last.ticker} recommendation (why, RSI, sentiment, etc.)."

    # --- Fallback: partial match on single words ---
    if "hold" in q and last.signal == "HOLD":
        return f"The model suggests HOLD with confidence {last.confidence:.1%}. {last.explanation}"
    if "buy" in q and last.signal == "BUY":
        return f"The model suggests BUY with confidence {last.confidence:.1%}. {last.explanation}"
    if "sell" in q and last.signal == "SELL":
        return f"The model suggests SELL with confidence {last.confidence:.1%}. {last.explanation}"

    return (
        "I didn't catch that. Try: Why? Confidence? RSI? Sentiment? Fundamentals? "
        "Moving averages? Volatility? Summary? or type help."
    )


def suggested_prompts() -> list[str]:
    """Short prompts the UI can show as chips."""
    return [
        "Why?",
        "Summary",
        "Confidence?",
        "RSI?",
        "Sentiment?",
        "Fundamentals?",
        "Moving averages?",
        "Volatility?",
        "help",
    ]

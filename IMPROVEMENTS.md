# ClearTrade – Improvements to Align With Capstone Paper

This document maps **paper sections** to **current implementation** and suggests **concrete improvements** for better outputs and full alignment with the Winter 2026 CS 687 capstone proposal.

---

## 1. Already Aligned

| Paper | Implementation |
|-------|----------------|
| Technical indicators (MA-10, MA-30, RSI, volatility) | `analysis_app/indicators.py` |
| Fundamental validation (P/E, earnings growth, revenue growth) | `core.models.FundamentalMetric`, used in `agent.fuse` |
| Sentiment from news headlines | `analysis_app/sentiment.py` |
| Agent-based fusion | `analysis_app/agent.fuse` with decision rules (§6.4) |
| Confidence score | Returned with every recommendation |
| Full-stack (Django + React) | `backend/`, `frontend/` |
| Explainability (plain-language summary) | `summarize_for_human`, explanation string |
| MCP integration | `cleartrade_mcp_server.py` |

---

## 2. Implemented in This Pass

- **Fundamental Agent score (§6.4)**  
  `compute_fundamental_score(pe_ratio, earnings_growth, revenue_growth)` returns a 0–1 financial strength score; used in fusion.

- **Explicit Decision Fusion rules (§6.4)**  
  - If Technical_Prob(Buy) > 0.65 AND Fundamental_Score > 0.6 AND Sentiment ≥ 0 → **BUY**.  
  - If signals conflict → **HOLD**.  
  - Logic in `agent.fuse()` with optional `probs` from the technical model.

- **Feature importance for explainability (§4, §7)**  
  API now returns `fundamental_score` and `feature_importance` (from Logistic Regression coefficients or Random Forest `feature_importances_`) so the UI can show “contribution of key indicators.”

---

## 3. Implemented in “Implement All” Pass

- **Sentiment:** `sentiment_model.py` – TF-IDF + Logistic Regression (train with `train_sentiment` on DB headlines); optional FinBERT in `score_sentiment_finbert` when `transformers`/`torch` installed. `sentiment.py` uses FinBERT → TF-IDF+LR → keyword fallback.
- **LSTM:** `lstm_model.py` – LSTM over sequences of technical indicators; train with `train_lstm` (requires `tensorflow`). Agent uses LSTM when `feats_sequence` is provided and LSTM model exists.
- **SHAP:** `explainability.py` – `get_shap_values()` for tree models (Random Forest); `get_feature_importance()` for coefficients/tree importance. API returns `shap_values` and `feature_importance`; frontend shows bar chart.
- **Backtesting:** Management command `backtest_recommendations` – evaluates technical (and optional full) pipeline vs next-day return; reports accuracy and signal counts.
- **Explainability UI:** “Indicator impact” / “SHAP impact” bar chart in the React app (Explanation & AI chat section).
- **Docs:** `DATA_AND_SCHEMA.md` – real-time data sources and DB schema aligned with paper §6.1, §8.

## 4. Recommended Next Steps (Priority Order)

### 4.1 Sentiment: FinBERT or TF-IDF + classifier (Paper §4, §8.3)

- **Current:** Simple keyword-based polarity in `sentiment.py`.
- **Paper:** “FinBERT-based classification or TF-IDF features combined with Logistic Regression.”
- **Improvement:**  
  - Option A: Use a small FinBERT (or other finance-oriented) model for headline polarity.  
  - Option B: TF-IDF + Logistic Regression on labeled financial headlines (e.g. from Kaggle).  
- **Benefit:** More accurate sentiment and better alignment with literature (e.g. Hu et al., Ruan 2025).

### 4.2 LSTM for technical trend prediction (Paper §4, §7)

- **Current:** Logistic Regression / Random Forest on technical indicators only.
- **Paper:** “LSTM networks for temporal dependencies” in financial time series (Fischer & Krauss, 2018).
- **Improvement:**  
  - Add an LSTM (or 1D CNN) that takes a window of past prices/indicators and outputs Buy/Hold/Sell probabilities.  
  - Keep Logistic Regression as the interpretable baseline; use LSTM as an optional “advanced” model or ensemble component.  
- **Benefit:** Stronger alignment with related work and potentially better trend capture.

### 4.3 SHAP-based explainability (Paper §4, §6.4, §7)

- **Current:** Feature importance from model coefficients / `feature_importances_`; narrative explanation.
- **Paper:** “SHAP values and feature importance to generate human-readable explanation.”
- **Improvement:**  
  - Compute SHAP values (e.g. `shap.TreeExplainer` or `KernelExplainer`) for the technical model’s prediction.  
  - Expose SHAP contributions in the API and show them in the UI (e.g. bar chart “Indicator impact”).  
- **Benefit:** Direct citation of paper’s explainability method and clearer “contribution of each indicator.”

### 4.4 Backtesting (Paper §4 Future features)

- **Current:** No backtesting.
- **Paper:** “Backtesting module to evaluate how past recommendations would have performed.”
- **Improvement:**  
  - Script or management command: for each date in a test window, run the pipeline (technical + fundamental + sentiment), record recommendation, then compare to next-period return.  
  - Report accuracy, confusion matrix, and simple performance metrics (e.g. hypothetical PnL if following BUY/SELL).  
- **Benefit:** Quantitative evaluation and stronger “Findings” section.

### 4.5 Enhanced explainability visualization (Paper §4 Future features)

- **Current:** Text explanation and optional feature importance in API.
- **Paper:** “Feature-importance charts or indicator impact graphs.”
- **Improvement:**  
  - In the React UI, add a small “Indicator impact” or “Explainability” panel that shows a bar chart of `feature_importance` (and later SHAP) per indicator.  
- **Benefit:** Matches “enhanced explainability visualization” in the feature list.

### 4.6 Real-time / API data (Paper §4, §8)

- **Current:** Yahoo Finance used in `live_data.py` for on-the-fly prices; fundamentals and news partially integrated.
- **Paper:** “Real-time market data integration” and use of APIs.
- **Improvement:**  
  - Document and, if needed, extend `ensure_prices_for_ticker` and `ensure_fundamentals_and_news` so that when historical DB is sparse, the system clearly relies on live/API data for the demo.  
- **Benefit:** Aligns with “current conditions” and data sources mentioned in the paper.

### 3.7 Database: MySQL and schema (Paper §6.1, §8)

- **Current:** SQLite by default; MySQL via env vars; schema matches paper (prices, fundamentals, news, recommendations).
- **Improvement:**  
  - Keep optional MySQL as in README; add a short “Data schema” section in the report that maps tables to §6.1 / §8.  
- **Benefit:** Full alignment with “MySQL database” and traceability.

### 4.8 Code structure naming (Paper §8.5)

- **Current:** `indicators.py`, `ml_train.py`, `agent.py`, `sentiment.py`, views in `views.py`.
- **Paper:** technical_analysis.py, ml_model.py, fundamental_scoring.py, sentiment_model.py, agent_fusion.py, explainability.py.
- **Improvement:**  
  - Optionally add thin modules or aliases (e.g. `fundamental_scoring.py` that calls `agent.compute_fundamental_score`) and document the mapping in the report.  
- **Benefit:** Easier for graders to match paper to code.

---

## 4. Summary Table

| Area | Status | Action |
|------|--------|--------|
| Technical indicators | Done | — |
| Fundamental validation | Done | — |
| Fundamental score (0–1) | Done | Exposed in API and used in fusion |
| Sentiment | Partial | Upgrade to FinBERT or TF-IDF+LR |
| Agent fusion rules | Done | BUY/HOLD/SELL + conflict → HOLD |
| Feature importance | Done | In API; optional UI chart |
| SHAP | Done | explainability.py + API + UI bar chart |
| LSTM | Done | lstm_model.py + train_lstm + agent integration |
| Backtesting | Done | backtest_recommendations management command |
| Explainability UI | Done | Bar chart for feature_importance / SHAP |
| Real-time / API data | Partial | Document and extend as needed |
| MySQL / schema | Done | Document in report |

Implementing **§3.1 (sentiment)**, **§3.2 (LSTM)**, and **§3.3 (SHAP)** next will give the largest gain in both output quality and paper alignment.

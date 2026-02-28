## ClearTrade – Explainable Stock Decision Support

This repository implements the **ClearTrade** capstone project: an explainable, agent-based stock market decision-support system that combines **technical analysis**, **fundamental analysis**, and **sentiment analysis** to generate **Buy / Hold / Sell** recommendations with confidence scores and human-readable explanations.

The stack closely follows the project paper:

- **Backend**: Django + Django REST Framework, agent-style fusion logic, SQLite by default with optional **MySQL** support for deployment.
- **ML layer**: Python + scikit-learn (Logistic Regression baseline, optional Random Forest) trained on engineered technical indicators (MA‑10, MA‑30, RSI, volatility).
- **Frontend**: React + Vite single-page app that shows recommendations, confidence, feature blocks, and an explainability chat.

### 1. Backend: running the API

From the `backend` directory:

```bash
python -m venv .venv
.\.venv\Scripts\activate   # on Windows PowerShell

pip install django==6.0.2 djangorestframework django-cors-headers pandas numpy scikit-learn joblib

python manage.py migrate
python manage.py runserver
```

The API is served at `http://127.0.0.1:8000/api/`:

- `GET /api/analyze?ticker=AAPL` – run full pipeline (technical + fundamental + sentiment) and return recommendation.
- `POST /api/chat` – ask follow-up “why / confidence / RSI / sentiment” questions about the latest recommendation.
- `GET /api/history?ticker=AAPL` – recent recommendation history for that ticker.

#### Database configuration (SQLite vs MySQL)

By default the project uses SQLite for easy local setup. To align with the paper’s design (MySQL-backed deployment), set these environment variables before running `manage.py`:

```bash
set DB_ENGINE=mysql
set DB_NAME=cleartrade
set DB_USER=cleartrade
set DB_PASSWORD=your_password
set DB_HOST=127.0.0.1
set DB_PORT=3306
```

The models in `core.models` map directly to the paper:

- `StockPrice` – raw OHLCV price history (technical analysis).
- `FundamentalMetric` – snapshot of valuation and growth metrics.
- `NewsHeadline` – cleaned financial news headlines.
- `Recommendation` – fused BUY/HOLD/SELL signal with confidence, indicators, fundamentals, sentiment, and explanation.

### 2. Data pipeline & training

The backend includes management commands that mirror the data collection section of the paper. After downloading CSVs (for example, from the Kaggle links in the paper) **locally only**:

```bash
.\.venv\Scripts\activate

# Import historical prices (Date, Ticker, Open, High, Low, Close, Volume)
python manage.py import_prices --csv path\to\prices.csv

# Import fundamentals (symbol, trailingPE, earningsGrowth, revenueGrowth)
python manage.py import_fundamentals --csv path\to\FUNDAMENTALratios.csv

# Import financial news (Date, Headline, Related_Company)
python manage.py import_news_events --csv path\to\financial_news_events.csv
```

Once data are loaded, train the technical trend classifier:

```bash
python train_model.py
```

By default this uses an **interpretable Logistic Regression** model; an optional Random Forest can be enabled inside `train_model.py` via `model_type="forest"`. The trained model is stored as `analysis_model.joblib` and is used by the agent layer.

### 3. Frontend: running the ClearTrade UI

From the `frontend` directory:

```bash
npm install
npm run dev
```

Open the printed Vite URL (usually `http://localhost:5173/`).

The main screen matches the “Stock Selection & Analysis Dashboard” described in the paper:

- Ticker input and **Analyze** button.
- Recommendation card showing **BUY / HOLD / SELL**, confidence, and a narrative explanation.
- Collapsible blocks for **technical indicators**, **fundamental metrics**, and **sentiment summary**.
- An **Explainability Chat** panel where you can ask:
  - “Why?” / “Explain” – returns the stored explanation.
  - “Confidence?” – returns the numeric confidence.
  - “RSI?” – returns the latest RSI value with context.
  - “Sentiment?” / “News?” – returns the sentiment score interpretation.

### 4. High-level mapping to the paper

- **Technical analysis** – MA‑10, MA‑30, RSI, and volatility are computed in `analysis_app/indicators.py` and power the ML classifier.
- **Fundamental validation** – valuation and growth metrics are imported via `import_fundamentals` and used in the fusion logic in `analysis_app/agent.py`.
- **Sentiment analysis** – news headlines are imported via `import_news_events`, scored in `analysis_app/sentiment.py`, and folded into the final decision.
- **Agent-based fusion** – `analysis_app/agent.fuse` adjusts confidence up/down based on fundamentals and sentiment and generates the human-readable explanation string returned to the UI.

This keeps the implementation consistent with the written capstone while remaining lightweight enough to run locally without bundling large datasets into the repository.

---

**Cleaning the latest commit message (optional)**  
If the latest commit on GitHub shows unwanted extra text when you view files, run `fix_last_commit.bat` from **Command Prompt or PowerShell outside your IDE** (from the repo root). It rewrites the latest commit with a clean message and force-pushes to `main`.


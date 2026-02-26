import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000/api";

const formatConfidence = (value) => {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
};

const getRecommendationClass = (recommendation) => {
  if (!recommendation) return "pill pill-neutral";

  const value = recommendation.toString().toLowerCase();
  if (value.includes("buy")) return "pill pill-buy";
  if (value.includes("sell")) return "pill pill-sell";
  if (value.includes("hold")) return "pill pill-hold";
  return "pill pill-neutral";
};

const formatFundamentals = (fundamentals) => {
  if (!fundamentals) return {};
  const { pe_ratio, earnings_growth, revenue_growth } = fundamentals;
  return {
    pe: pe_ratio ?? "—",
    eg: typeof earnings_growth === "number" ? `${(earnings_growth * 100).toFixed(1)}%` : "—",
    rg: typeof revenue_growth === "number" ? `${(revenue_growth * 100).toFixed(1)}%` : "—",
  };
};

const describeSentiment = (score) => {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return {
      label: "No data",
      tone: "neutral",
      explanation: "No recent news headlines were available to score sentiment for this ticker.",
    };
  }

  const rounded = score.toFixed(2);

  if (score > 0.1) {
    return {
      label: `Positive (${rounded})`,
      tone: "positive",
      explanation: "Recent finance news is mostly positive, which supports bullish sentiment for this stock.",
    };
  }

  if (score < -0.1) {
    return {
      label: `Negative (${rounded})`,
      tone: "negative",
      explanation: "Recent finance news is mostly negative, which may be contributing to downside risk.",
    };
  }

  return {
    label: `Neutral (${rounded})`,
    tone: "neutral",
    explanation: "News flow is mixed or balanced, so sentiment is not strongly pushing price in either direction.",
  };
};

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const [q, setQ] = useState("");
  const [chat, setChat] = useState([
    { role: "agent", text: "Ask about RSI, confidence, sentiment or fundamentals for this trade." },
  ]);

  async function analyze() {
    const cleaned = ticker.toUpperCase().trim();
    if (!cleaned) {
      setErr("Please enter a ticker symbol.");
      return;
    }

    setErr("");
    setResult(null);
    setLoading(true);
    try {
      const res = await fetch(`${API}/analyze?ticker=${cleaned}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analyze failed");
      setResult(data);
    } catch (e) {
      setErr(e.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function sendChat() {
    if (!result) return;
    const question = q.trim();
    if (!question) return;

    setChat((c) => [...c, { role: "you", text: question }]);
    setQ("");

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: result.ticker, question }),
      });

      const data = await res.json();
      setChat((c) => [...c, { role: "agent", text: data.answer || "No response" }]);
    } catch {
      setChat((c) => [...c, { role: "agent", text: "I couldn't reach the analysis service. Please try again." }]);
    }
  }

  const hasResult = Boolean(result);
  const fundamentals = hasResult ? formatFundamentals(result.fundamentals) : null;
  const sentimentInfo = hasResult ? describeSentiment(result.sentiment) : null;

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
          <div className="app-brand">
            <span className="brand-badge">CT</span>
            <div>
              <h1 className="app-title">ClearTrade</h1>
              <p className="app-subtitle">Explainable stock decision support.</p>
            </div>
          </div>
        </header>

        <div className="layout">
          <aside className="sidebar">
            <div className="sidebar-card ticker-card">
              <div className="ticker-row">
                <div className="ticker-chip">
                  <span className="ticker-symbol">{ticker.toUpperCase()}</span>
                </div>
                <button
                  className="primary-button"
                  onClick={analyze}
                  disabled={loading}
                >
                  {loading ? "Analyzing..." : "Analyze"}
                </button>
              </div>

              <label className="ticker-label">
                Enter ticker symbol
                <input
                  className="ticker-input"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  placeholder="e.g. MSFT"
                />
              </label>

              {err && <p className="error-text">{err}</p>}

              {hasResult && (
                <div className="ticker-summary">
                  <span className="ticker-summary-label">Latest signal</span>
                  <span className={getRecommendationClass(result.recommendation)}>
                    {result.recommendation || "No signal"} · {formatConfidence(result.confidence)}
                  </span>
                </div>
              )}
            </div>

            <div className="sidebar-card">
              <h3 className="sidebar-title">Price chart</h3>
              <div className="chart-placeholder">
                <span>Price history visualization</span>
              </div>
            </div>

            <div className="sidebar-card">
              <h3 className="sidebar-title">Fundamentals</h3>
              {hasResult ? (
                <div className="mini-metrics">
                  <div className="mini-metric">
                    <span className="mini-label">P/E</span>
                    <span className="mini-value">{fundamentals.pe}</span>
                  </div>
                  <div className="mini-metric">
                    <span className="mini-label">Earnings growth</span>
                    <span className="mini-value">{fundamentals.eg}</span>
                  </div>
                  <div className="mini-metric">
                    <span className="mini-label">Revenue growth</span>
                    <span className="mini-value">{fundamentals.rg}</span>
                  </div>
                </div>
              ) : (
                <p className="sidebar-muted">Run an analysis to see fundamentals.</p>
              )}
            </div>

            <div className="sidebar-card">
              <h3 className="sidebar-title">Sentiment analysis</h3>
              {hasResult && sentimentInfo ? (
                <>
                  <div className={`sentiment-chip sentiment-${sentimentInfo.tone}`}>
                    {sentimentInfo.label}
                  </div>
                  <p className="sidebar-muted sentiment-expl">{sentimentInfo.explanation}</p>
                </>
              ) : (
                <p className="sidebar-muted">News sentiment will appear here after you run an analysis.</p>
              )}
            </div>
          </aside>

          <main className="main">
            {!hasResult && !err && (
              <div className="empty-state">
                <h2>Explainable insights for any stock</h2>
                <p>
                  Enter a ticker on the left and click Analyze to see technical indicators, fundamental validation,
                  news sentiment, and an explainable Buy / Hold / Sell signal.
                </p>
                <ul className="empty-list">
                  <li>Combined view of technical, fundamental, and sentiment factors.</li>
                  <li>Clear confidence score with natural language explanation.</li>
                  <li>AI assistant to answer &quot;Why?&quot;, &quot;RSI?&quot;, &quot;Sentiment?&quot;, and more.</li>
                </ul>
              </div>
            )}

            {hasResult && (
              <>
                <section className="panel main-reco-panel">
                  <header className="panel-header">
                    <div>
                      <p className="panel-label">Price chart</p>
                      <h2 className="panel-title">{result.ticker}</h2>
                    </div>
                    <div className="reco-summary">
                      <span className={getRecommendationClass(result.recommendation)}>
                        {result.recommendation || "No signal"}
                      </span>
                      <span className="reco-confidence">{formatConfidence(result.confidence)}</span>
                    </div>
                  </header>

                  <p className="panel-subtext">
                    In simple terms: {result.summary || "This recommendation combines recent price behaviour, company fundamentals and news sentiment."}
                  </p>
                  <ul className="bullet-list">
                    <li>
                      <strong>Technical indicators:</strong> Moving averages (MA‑10 / MA‑30), RSI and volatility from
                      recent price action.
                    </li>
                    <li>
                      <strong>Fundamentals:</strong> Valuation and growth metrics from the latest fundamentals snapshot.
                    </li>
                    <li>
                      <strong>Sentiment:</strong> News sentiment score aggregated from recent finance headlines.
                    </li>
                  </ul>
                </section>

                <section className="panel">
                  <header className="panel-header">
                    <div>
                      <p className="panel-label">Explanation</p>
                      <h2 className="panel-title">Why this recommendation?</h2>
                    </div>
                  </header>
                  <p className="section-body">{result.explanation}</p>
                </section>

                <section className="panel panel-secondary chat-panel">
                  <header className="panel-header">
                    <div>
                      <p className="panel-label">AI Assistant</p>
                      <h2 className="panel-title">Ask for more detail…</h2>
                    </div>
                  </header>

                  <div className="chat-window">
                    {chat.map((m, i) => (
                      <div
                        key={i}
                        className={`chat-message chat-message-${m.role === "you" ? "user" : "agent"}`}
                      >
                        <span className="chat-role">
                          {m.role === "you" ? "You" : "Agent"}
                        </span>
                        <p className="chat-text">{m.text}</p>
                      </div>
                    ))}
                  </div>

                  <div className="chat-input-row">
                    <input
                      className="chat-input"
                      value={q}
                      onChange={(e) => setQ(e.target.value)}
                      placeholder={hasResult ? "Ask: Why? RSI? Confidence? Sentiment? ..." : "Run Analyze to enable chat"}
                      disabled={!hasResult}
                    />
                    <button
                      className="secondary-button"
                      onClick={sendChat}
                      disabled={!hasResult}
                    >
                      Send
                    </button>
                  </div>

                  {!hasResult && (
                    <p className="chat-helper">
                      Run an analysis first to unlock the explainability chat for this ticker.
                    </p>
                  )}
                </section>
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
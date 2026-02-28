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
  const [showMoreDetails, setShowMoreDetails] = useState(false);
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
      const raw = await res.text();

      let data;
      try {
        data = raw ? JSON.parse(raw) : null;
      } catch {
        throw new Error("The analysis service returned an invalid response. Is the backend running?");
      }

      if (!res.ok) {
        throw new Error((data && data.error) || "Analyze failed");
      }

      setResult(data);
      setShowMoreDetails(false);
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
  const hasFundamentalsData =
    fundamentals &&
    !(fundamentals.pe === "—" && fundamentals.eg === "—" && fundamentals.rg === "—");

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
              <h3 className="sidebar-title">Fundamentals</h3>
              {hasResult ? (
                hasFundamentalsData ? (
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
                  <p className="sidebar-muted">No fundamentals data available for this ticker.</p>
                )
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
                <p>Type a ticker on the left and click Analyze to see a clear Buy / Hold / Sell view with supporting details.</p>
              </div>
            )}

            {hasResult && (
              <>
                <section className="panel main-reco-panel">
                  <header className="panel-header">
                    <h2 className="panel-title">{result.ticker}</h2>
                    <div className="reco-summary">
                      <span className={getRecommendationClass(result.recommendation)}>
                        {result.recommendation || "No signal"}
                      </span>
                      <span className="reco-confidence">{formatConfidence(result.confidence)}</span>
                    </div>
                  </header>
                  <p className="panel-subtext">
                    {result.summary || "Recommendation based on technicals, fundamentals and news sentiment."}
                  </p>
                  <button
                    type="button"
                    className="more-details-toggle"
                    onClick={() => setShowMoreDetails((v) => !v)}
                    aria-expanded={showMoreDetails}
                  >
                    {showMoreDetails ? "Hide details" : "Explanation & AI chat"}
                  </button>
                </section>

                {showMoreDetails && (
                  <>
                    <section className="panel">
                      <h3 className="panel-heading-sm">Why this recommendation?</h3>
                      <p className="section-body">{result.explanation}</p>
                    </section>

                    <section className="panel panel-secondary chat-panel">
                      <h3 className="panel-heading-sm">AI Assistant</h3>
                      <div className="chat-window">
                        {chat.map((m, i) => (
                          <div
                            key={i}
                            className={`chat-message chat-message-${m.role === "you" ? "user" : "agent"}`}
                          >
                            <span className="chat-role">{m.role === "you" ? "You" : "Agent"}</span>
                            <p className="chat-text">{m.text}</p>
                          </div>
                        ))}
                      </div>
                      <div className="chat-input-row">
                        <input
                          className="chat-input"
                          value={q}
                          onChange={(e) => setQ(e.target.value)}
                          placeholder="Ask: Why? RSI? Confidence? Sentiment?"
                          onKeyDown={(e) => e.key === "Enter" && sendChat()}
                        />
                        <button className="secondary-button" onClick={sendChat}>
                          Send
                        </button>
                      </div>
                    </section>
                  </>
                )}
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
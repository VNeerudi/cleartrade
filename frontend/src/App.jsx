import { useState, useRef, useEffect } from "react";
import "./App.css";
import TechnicalSnapshot from "./components/TechnicalSnapshot.jsx";
import SentimentWithNews from "./components/SentimentWithNews.jsx";
import { getRecommendationClass, formatConfidence } from "./recommendationUtils.js";

const API = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

function humanizeError(message) {
  if (!message) return "Something went wrong. Please try again.";
  if (/failed to fetch|networkerror/i.test(message)) {
    return "Can't reach the API. Start the backend (port 8000) and check VITE_API_BASE in .env.";
  }
  if (/60 rows|at least 60/i.test(message)) {
    return "Not enough price history for this ticker. Import CSV data or wait for live fetch to fill 60+ days.";
  }
  return message;
}

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

// Matches backend chat_agent.suggested_prompts (rule-based explainability, no LLM)
const CHAT_PROMPTS = [
  "Summary",
  "Why?",
  "Confidence?",
  "RSI?",
  "Sentiment?",
  "Fundamentals?",
  "Moving averages?",
  "Volatility?",
  "help",
];

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const [q, setQ] = useState("");
  const [showMoreDetails, setShowMoreDetails] = useState(false);
  const [chat, setChat] = useState([
    {
      role: "agent",
      text: "I explain your latest Analyze run (no live AI model). Try Summary, Why?, RSI, Sentiment, Fundamentals, Moving averages, Volatility—or type help.",
    },
  ]);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!showMoreDetails) return;
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, showMoreDetails]);

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
        const serverMsg = (data && data.error) || "Analyze failed";
        throw new Error(serverMsg);
      }

      setResult(data);
      setShowMoreDetails(false);
      setChat([
        {
          role: "agent",
          text: `Ready for ${data.ticker}. Ask Summary, Why?, Confidence, RSI, Sentiment, Fundamentals, MA trend, Volatility—or help.`,
        },
      ]);
    } catch (e) {
      const msg = e.message || "Something went wrong.";
      setErr(humanizeError(msg));
    } finally {
      setLoading(false);
    }
  }

  async function sendChat(questionOverride) {
    if (!result) return;
    const question = (questionOverride ?? q).trim();
    if (!question) return;

    setChat((c) => [...c, { role: "you", text: question }]);
    if (!questionOverride) setQ("");

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: result.ticker, question }),
      });
      const data = await res.json();
      setChat((c) => [...c, { role: "agent", text: data.answer || "No response" }]);
    } catch {
      setChat((c) => [
        ...c,
        { role: "agent", text: "I couldn't reach the analysis service. Please try again." },
      ]);
    }
  }

  const hasResult = Boolean(result);
  const fundamentals = hasResult ? formatFundamentals(result.fundamentals) : null;
  const sentimentInfo = hasResult ? describeSentiment(result.sentiment) : null;
  const hasFundamentalsData =
    fundamentals &&
    !(fundamentals.pe === "—" && fundamentals.eg === "—" && fundamentals.rg === "—");

  const probs = result?.class_probabilities;
  const hasProbs = probs && typeof probs === "object" && Object.keys(probs).length > 0;

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
                <button className="primary-button" onClick={analyze} disabled={loading}>
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

              {loading && <div className="loading-bar" aria-hidden="true" />}

              {err && (
                <>
                  <p className="error-text">{err}</p>
                  <p className="error-hint">
                    Backend: <code>python manage.py runserver</code> in <code>backend/</code>
                  </p>
                </>
              )}

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

            <div className="sidebar-card sidebar-card-sentiment">
              <h3 className="sidebar-title">Sentiment</h3>
              {hasResult && sentimentInfo ? (
                <SentimentWithNews
                  sentimentInfo={sentimentInfo}
                  newsSamples={result.news_samples}
                  newsHeadlinesUsed={result.news_headlines_used}
                  compact
                />
              ) : (
                <p className="sidebar-muted">Run an analysis to see score and headlines used.</p>
              )}
            </div>
          </aside>

          <main className="main">
            {loading && (
              <div className="panel skeleton-panel" aria-busy="true">
                <div className="skeleton-block skeleton-title" />
                <div className="skeleton-block skeleton-line" />
                <div className="skeleton-block skeleton-line short" />
                <div className="skeleton-block skeleton-line" />
              </div>
            )}

            {!hasResult && !err && !loading && (
              <div className="empty-state">
                <h2>Explainable insights for any stock</h2>
                <p>
                  Type a ticker on the left and click Analyze to see a clear Buy / Hold / Sell view with
                  technical snapshot and supporting details.
                </p>
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
                  {hasProbs && (
                    <div className="prob-chips">
                      {Object.entries(probs).map(([k, v]) => (
                        <span key={k} className="prob-chip" title="Model class probability">
                          {k}: {(Number(v) * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    className="more-details-toggle"
                    onClick={() => setShowMoreDetails((v) => !v)}
                    aria-expanded={showMoreDetails}
                  >
                    {showMoreDetails ? "Hide details" : "Explanation & AI chat"}
                  </button>
                </section>

                <TechnicalSnapshot features={result.features} />

                {hasResult && sentimentInfo && result.news_samples?.length > 0 && (
                  <section className="panel panel-sentiment-main">
                    <h3 className="panel-heading-sm">News & sentiment detail</h3>
                    <SentimentWithNews
                      sentimentInfo={sentimentInfo}
                      newsSamples={result.news_samples}
                      newsHeadlinesUsed={result.news_headlines_used}
                    />
                  </section>
                )}

                {showMoreDetails && (
                  <>
                    <section className="panel">
                      <h3 className="panel-heading-sm">Why this recommendation?</h3>
                      <p className="section-body">{result.explanation}</p>
                      {result.fundamental_score != null && (
                        <p className="section-body sidebar-muted" style={{ marginTop: "0.5rem" }}>
                          Fundamental score (0–1):{" "}
                          <strong>{Number(result.fundamental_score).toFixed(2)}</strong> (higher = stronger
                          financial strength).
                        </p>
                      )}
                      {(() => {
                        const impact = result.shap_values || result.feature_importance;
                        if (!impact || Object.keys(impact).length === 0) return null;
                        const entries = Object.entries(impact).map(([k, v]) => [k, Number(v)]);
                        const maxVal = Math.max(...entries.map(([, v]) => Math.abs(v)), 1e-9);
                        return (
                          <div className="section-body explainability-chart" style={{ marginTop: "0.75rem" }}>
                            <h4 className="panel-heading-sm">
                              {result.shap_values ? "SHAP impact" : "Indicator impact"} (explainability)
                            </h4>
                            <div className="impact-bars">
                              {entries.map(([name, val]) => (
                                <div key={name} className="impact-bar-row">
                                  <span className="impact-label">{name}</span>
                                  <div className="impact-bar-wrap">
                                    <div
                                      className={`impact-bar ${val >= 0 ? "impact-positive" : "impact-negative"}`}
                                      style={{
                                        width: `${Math.min(100, (Math.abs(val) / maxVal) * 100)}%`,
                                      }}
                                    />
                                  </div>
                                  <span className="impact-value">{val.toFixed(3)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })()}
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
                            <p className="chat-text chat-text-multiline">{m.text}</p>
                          </div>
                        ))}
                        <div ref={chatEndRef} />
                      </div>
                      <div className="prompt-chips">
                        {CHAT_PROMPTS.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            className="prompt-chip"
                            onClick={() => sendChat(prompt)}
                          >
                            {prompt}
                          </button>
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
                        <button className="secondary-button" onClick={() => sendChat()}>
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

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

  return (
    <div className="app">
      <div className="app-shell">
        <header className="app-header">
          <div className="app-brand">
            <span className="brand-badge">CT</span>
            <div>
              <h1 className="app-title">ClearTrade</h1>
              <p className="app-subtitle">Explainable, AI-powered stock decision support.</p>
            </div>
          </div>

          <div className="ticker-form">
            <label className="ticker-label">
              Ticker
              <input
                className="ticker-input"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="e.g. AAPL"
              />
            </label>
            <button
              className="primary-button"
              onClick={analyze}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>

          {err && <p className="error-text">{err}</p>}
        </header>

        <main className="app-main">
          {!hasResult && !err && (
            <div className="empty-state">
              <h2>Start with a ticker symbol</h2>
              <p>We&apos;ll fetch indicators, fundamentals, sentiment, and a clear recommendation for your next move.</p>
              <ul className="empty-list">
                <li>View a concise recommendation and confidence score.</li>
                <li>Inspect key technical indicators and volatility.</li>
                <li>Chat with an agent to dig into the &quot;why&quot; behind the signal.</li>
              </ul>
            </div>
          )}

          {hasResult && (
            <section className="app-grid">
              <article className="panel">
                <header className="panel-header">
                  <div>
                    <p className="panel-label">Overview</p>
                    <h2 className="panel-title">{result.ticker}</h2>
                  </div>
                  <span className={getRecommendationClass(result.recommendation)}>
                    {result.recommendation || "No signal"}
                  </span>
                </header>

                <div className="metric-row">
                  <div className="metric">
                    <p className="metric-label">Confidence</p>
                    <p className="metric-value">{formatConfidence(result.confidence)}</p>
                  </div>
                </div>

                {result.explanation && (
                  <section className="section">
                    <h3 className="section-title">Why this recommendation?</h3>
                    <p className="section-body">{result.explanation}</p>
                  </section>
                )}

                <section className="section-grid">
                  <div className="section-card">
                    <h3 className="section-title">Technical indicators</h3>
                    <pre className="data-pre">
                      {JSON.stringify(result.features, null, 2)}
                    </pre>
                  </div>

                  <div className="section-card">
                    <h3 className="section-title">Fundamentals</h3>
                    <pre className="data-pre">
                      {JSON.stringify(result.fundamentals, null, 2)}
                    </pre>
                  </div>

                  <div className="section-card section-card-wide">
                    <h3 className="section-title">Sentiment</h3>
                    <pre className="data-pre">
                      {JSON.stringify(result.sentiment, null, 2)}
                    </pre>
                  </div>
                </section>
              </article>

              <aside className="panel panel-secondary">
                <header className="panel-header">
                  <div>
                    <p className="panel-label">Conversation</p>
                    <h2 className="panel-title">Explainability chat</h2>
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
                    placeholder={hasResult ? "Ask about risk, signals, or time horizon…" : "Run Analyze to enable chat"}
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
              </aside>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
import { useState } from "react";
import { Link } from "react-router-dom";
import { getRecommendationClass, formatConfidence } from "../recommendationUtils.js";

const API = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

export default function HistoryPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    const t = ticker.toUpperCase().trim();
    if (!t) return;
    setErr("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/history?ticker=${encodeURIComponent(t)}`);
      const data = await res.json();
      setRows(Array.isArray(data.history) ? data.history : []);
    } catch {
      setErr("Could not load history.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell app-shell-page">
      <header className="page-nav">
        <Link to="/" className="page-nav-link">
          ← Dashboard
        </Link>
        <h1 className="page-nav-title">Recommendation history</h1>
      </header>

      <div className="history-toolbar">
        <input
          className="ticker-input"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="Ticker"
        />
        <button type="button" className="primary-button" onClick={load} disabled={loading}>
          {loading ? "Loading…" : "Load history"}
        </button>
      </div>
      {err && <p className="error-text">{err}</p>}

      {rows.length === 0 && !loading && !err && (
        <p className="sidebar-muted">Enter a ticker and load to see past Analyze runs.</p>
      )}

      {rows.length > 0 && (
        <div className="history-table-wrap">
          <table className="history-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Signal</th>
                <th>Confidence</th>
                <th>Explanation</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="history-cell-time">
                    {r.created_at
                      ? new Date(r.created_at).toLocaleString()
                      : "—"}
                  </td>
                  <td>
                    <span className={getRecommendationClass(r.signal)}>{r.signal}</span>
                  </td>
                  <td>{formatConfidence(r.confidence)}</td>
                  <td className="history-cell-expl">{r.explanation || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

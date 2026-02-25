import { useState } from "react";

const API = "http://127.0.0.1:8000/api";

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  const [q, setQ] = useState("");
  const [chat, setChat] = useState([{ role: "agent", text: "Ask: Why? RSI? Confidence? Sentiment?" }]);

  async function analyze() {
    setErr("");
    setResult(null);
    try {
      const res = await fetch(`${API}/analyze?ticker=${ticker.toUpperCase().trim()}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analyze failed");
      setResult(data);
    } catch (e) {
      setErr(e.message);
    }
  }

  async function sendChat() {
    if (!result) return;
    const question = q.trim();
    if (!question) return;

    setChat((c) => [...c, { role: "you", text: question }]);
    setQ("");

    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: result.ticker, question }),
    });

    const data = await res.json();
    setChat((c) => [...c, { role: "agent", text: data.answer || "No response" }]);
  }

  return (
    <div style={{ padding: 24, fontFamily: "Arial" }}>
      <h2>ClearTrade — Explainable Stock Decision Support</h2>

      <div style={{ display: "flex", gap: 8 }}>
        <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
        <button onClick={analyze}>Analyze</button>
      </div>

      {err && <p style={{ color: "crimson" }}>{err}</p>}

      {result && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
          <div style={{ border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
            <h3>{result.ticker}</h3>
            <p><b>Recommendation:</b> {result.recommendation}</p>
            <p><b>Confidence:</b> {(result.confidence * 100).toFixed(1)}%</p>
            <p><b>Explanation:</b> {result.explanation}</p>

            <h4>Technical Features</h4>
            <pre>{JSON.stringify(result.features, null, 2)}</pre>

            <h4>Fundamentals</h4>
            <pre>{JSON.stringify(result.fundamentals, null, 2)}</pre>

            <h4>Sentiment</h4>
            <pre>{JSON.stringify(result.sentiment, null, 2)}</pre>
          </div>

          <div style={{ border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
            <h3>Chat Assistant</h3>
            <div style={{ height: 260, overflow: "auto", background: "#fafafa", padding: 8 }}>
              {chat.map((m, i) => (
                <div key={i} style={{ margin: "6px 0" }}>
                  <b>{m.role}:</b> {m.text}
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Ask a question..."
                style={{ flex: 1 }}
              />
              <button onClick={sendChat}>Send</button>
            </div>

            {!result && <p style={{ fontSize: 12, color: "#666" }}>Run Analyze first to enable chat.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
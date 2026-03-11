/**
 * Shows MA-10, MA-30, RSI, volatility from analyze API `features`.
 */
export default function TechnicalSnapshot({ features }) {
  if (!features || typeof features !== "object") return null;

  const rows = [
    { key: "ma_10", label: "MA-10", value: features.ma_10, fmt: (v) => Number(v).toFixed(2) },
    { key: "ma_30", label: "MA-30", value: features.ma_30, fmt: (v) => Number(v).toFixed(2) },
    {
      key: "rsi",
      label: "RSI",
      value: features.rsi,
      fmt: (v) => Number(v).toFixed(1),
      hint: (v) => {
        const n = Number(v);
        if (n >= 70) return "Overbought zone";
        if (n <= 30) return "Oversold zone";
        return "Neutral";
      },
    },
    {
      key: "volatility",
      label: "Volatility",
      value: features.volatility,
      fmt: (v) => Number(v).toFixed(4),
    },
  ].filter((r) => r.value != null && !Number.isNaN(Number(r.value)));

  if (rows.length === 0) return null;

  return (
    <section className="panel panel-technical">
      <h3 className="panel-heading-sm">Technical snapshot</h3>
      <p className="sidebar-muted technical-lead">
        Latest indicator values used for the model and fusion.
      </p>
      <div className="technical-grid">
        {rows.map(({ key, label, value, fmt, hint }) => (
          <div key={key} className="technical-cell">
            <span className="technical-label">{label}</span>
            <span className="technical-value">{fmt(value)}</span>
            {hint && <span className="technical-hint">{hint(value)}</span>}
          </div>
        ))}
      </div>
    </section>
  );
}

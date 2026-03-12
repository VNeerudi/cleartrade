import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

/**
 * Close price over time from GET /api/series?ticker=
 */
export default function PriceChart({ ticker, points }) {
  if (!points || points.length === 0) {
    return (
      <div className="chart-empty">
        No price series yet. Run Analyze to sync data, then refresh.
      </div>
    );
  }

  const data = points.map((p) => ({
    ...p,
    label: p.date?.slice(5) || p.date, // MM-DD for axis
  }));

  return (
    <div className="chart-wrap">
      <h4 className="chart-title">{ticker} — close (last {data.length} sessions)</h4>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            stroke="#94a3b8"
            interval="preserveStartEnd"
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 11 }}
            stroke="#94a3b8"
            width={56}
            tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0))}
          />
          <Tooltip
            formatter={(value) => [Number(value).toFixed(2), "Close"]}
            labelFormatter={(label, payload) => payload?.[0]?.payload?.date || label}
            contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#4f46e5"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

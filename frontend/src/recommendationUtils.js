/** Shared pill classes for BUY/HOLD/SELL */
export function getRecommendationClass(recommendation) {
  if (!recommendation) return "pill pill-neutral";
  const value = recommendation.toString().toLowerCase();
  if (value.includes("buy")) return "pill pill-buy";
  if (value.includes("sell")) return "pill pill-sell";
  if (value.includes("hold")) return "pill pill-hold";
  return "pill pill-neutral";
}

export function formatConfidence(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

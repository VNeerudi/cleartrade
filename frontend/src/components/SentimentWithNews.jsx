/**
 * Descriptive sentiment: score + list of headlines used so users see *what* news drove the score.
 */
export default function SentimentWithNews({
  sentimentInfo,
  newsSamples,
  newsHeadlinesUsed,
  compact = false,
}) {
  const samples = Array.isArray(newsSamples) ? newsSamples : [];
  const displaySamples = compact ? samples.slice(0, 2) : samples;
  const moreCount = compact && samples.length > 2 ? samples.length - 2 : 0;

  if (!sentimentInfo) return null;

  return (
    <div className="sentiment-block">
      <div className="sentiment-block-header">
        <div className={`sentiment-chip sentiment-${sentimentInfo.tone}`}>{sentimentInfo.label}</div>
        {typeof newsHeadlinesUsed === "number" && newsHeadlinesUsed > 0 && (
          <span className="sentiment-count">{newsHeadlinesUsed} headlines scored</span>
        )}
      </div>
      <p className="sentiment-block-lead">{sentimentInfo.explanation}</p>

      {displaySamples.length > 0 && (
        <div className={`news-headlines-box ${compact ? "news-headlines-box--compact" : ""}`}>
          {!compact && (
            <>
              <h4 className="news-headlines-title">Recent headlines used for sentiment</h4>
              <p className="news-headlines-sub">
                These items were fed into the sentiment model (keyword / TF-IDF / FinBERT when available).
              </p>
            </>
          )}
          {compact && <p className="news-headlines-sub">Sample headlines:</p>}
          <ul className="news-headlines-list">
            {displaySamples.map((item, i) => (
              <li key={i} className="news-headline-item">
                <span className="news-headline-text">{item.headline}</span>
                {item.date && <span className="news-headline-date">{item.date}</span>}
              </li>
            ))}
          </ul>
          {moreCount > 0 && (
            <p className="news-headlines-more">+ {moreCount} more in the main panel →</p>
          )}
        </div>
      )}

      {samples.length === 0 && sentimentInfo.tone !== "neutral" && sentimentInfo.label !== "No data" && (
        <p className="sidebar-muted sentiment-expl">
          Headline list unavailable for this response; score is still from aggregated news text.
        </p>
      )}
    </div>
  );
}

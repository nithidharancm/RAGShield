export default function RiskGauge({ score, status, bypassed = false }) {
  const numeric = Number.isFinite(score);
  const bounded = numeric ? Math.max(0, Math.min(100, score)) : 0;
  const degrees = bounded * 3.6;

  let label = bypassed ? "Security Bypassed" : "No scan trace";
  let tone = "unknown";

  if (numeric) {
    if (bounded <= 20) {
      label = "Low Risk";
      tone = "low";
    } else if (bounded <= 40) {
      label = "Moderate Risk";
      tone = "moderate";
    } else if (bounded <= 70) {
      label = "High Risk";
      tone = "high";
    } else {
      label = "Critical Risk";
      tone = "critical";
    }
  }

  return (
    <div className="risk-content">
      <div
        className={`risk-ring ${tone}`}
        style={{ "--risk-angle": `${degrees}deg` }}
      >
        <div className="risk-ring-inner">
          <strong>{numeric ? bounded : "—"}</strong>
          <span>{numeric ? "/ 100" : bypassed ? "bypassed" : "not exposed"}</span>
        </div>
      </div>

      <div className="risk-copy">
        <strong className={`risk-label ${tone}`}>{label}</strong>
        <span>
          {bypassed
            ? "RAGShield was OFF for this trace, so Layer 1 did not calculate a risk score."
            : numeric
            ? status === "QUARANTINED"
              ? "This document was quarantined by Stage 1."
              : "Risk score captured from the ingestion scan."
            : "The current /search response does not expose historic ingestion scores. Upload through this UI to capture one."}
        </span>
        <div className="risk-scale">
          <i className="scale-low" />
          <i className="scale-moderate" />
          <i className="scale-high" />
          <i className="scale-critical" />
        </div>
      </div>
    </div>
  );
}

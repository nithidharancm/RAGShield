import { ShieldCheck } from "lucide-react";

export default function ShieldToggle({ enabled, onChange }) {
  return (
    <button
      className={`shield-toggle ${enabled ? "enabled" : "disabled"}`}
      onClick={() => onChange(!enabled)}
      aria-pressed={enabled}
      title={
        enabled
          ? "RAGShield protection is enabled for the next request"
          : "RAGShield protection is disabled for the next request"
      }
    >
      <div className="shield-toggle-copy">
        <div className="shield-toggle-label">
          <ShieldCheck size={15} />
          <strong>RAGShield</strong>
        </div>
        <span>
          {enabled ? "Next request: protected" : "Next request: baseline"}
        </span>
      </div>

      <div className="toggle-track">
        <span>{enabled ? "ON" : "OFF"}</span>
        <i />
      </div>
    </button>
  );
}

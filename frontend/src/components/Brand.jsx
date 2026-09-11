import { ShieldCheck } from "lucide-react";

export default function Brand() {
  return (
    <div className="brand">
      <div className="brand-shield">
        <ShieldCheck size={24} strokeWidth={1.8} />
      </div>
      <div>
        <div className="brand-title">RAGShield</div>
        <div className="brand-subtitle">Secure. Grounded. Yours.</div>
      </div>
    </div>
  );
}

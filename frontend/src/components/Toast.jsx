import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";

export default function Toast({ toast, onClose }) {
  if (!toast) return null;
  const Icon = toast.type === "error" ? TriangleAlert : toast.type === "success" ? CheckCircle2 : Info;
  return (
    <div className={`toast ${toast.type || "info"}`}>
      <Icon size={18} />
      <span>{toast.message}</span>
      <button onClick={onClose}><X size={14} /></button>
    </div>
  );
}

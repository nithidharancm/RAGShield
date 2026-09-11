import { FileText, ShieldCheck } from "lucide-react";

export default function SourceList({ sources = [], tenant }) {
  if (!sources.length) {
    return (
      <div className="source-empty">
        <FileText size={26} />
        <strong>No sources yet</strong>
        <span>Send a document-grounded query to inspect retrieved files.</span>
      </div>
    );
  }

  return (
    <div className="source-list-panel">
      {sources.map((source, index) => {
        const authorized = source.tenant_id === tenant;
        return (
          <div className="source-row" key={`${source.document_id}-${index}`}>
            <div className="source-icon"><FileText size={17} /></div>
            <div className="source-copy">
              <strong>{source.filename}</strong>
              <span>{source.document_id}</span>
            </div>
            <div className={`source-tenant ${authorized ? "ok" : "bad"}`}>
              <ShieldCheck size={13} />
              {source.tenant_id}
            </div>
          </div>
        );
      })}
    </div>
  );
}

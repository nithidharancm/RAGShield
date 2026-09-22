import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Database,
  FileCheck2,
  FileText,
  LoaderCircle,
  LockKeyhole,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  UploadCloud,
  X,
} from "lucide-react";
import { secureSearch, uploadAndScan } from "../services/api";
import { getDemoPrompts } from "../config/prompts";
import SourceList from "../components/SourceList";

function LayerCard({ number, title, subtitle, status, detail, icon: Icon }) {
  const state =
    status === "PASSED" || status === "APPROVED"
      ? "passed"
      : status === "BYPASSED"
        ? "bypassed"
      : status === "BLOCKED" || status === "QUARANTINED" || status === "FAILED"
        ? "blocked"
        : status === "RUNNING"
          ? "running"
          : "waiting";

  return (
    <div className={`upload-layer-card ${state}`}>
      <div className="upload-layer-number">{number}</div>
      <div className="upload-layer-icon">
        {status === "RUNNING" ? <LoaderCircle className="spin" size={20} /> : <Icon size={20} />}
      </div>
      <div className="upload-layer-copy">
        <strong>{title}</strong>
        <span>{subtitle}</span>
        <small>{detail}</small>
      </div>
      <div className={`upload-layer-status ${state}`}>
        {state === "passed" ? <CheckCircle2 size={14} /> : state === "blocked" || state === "bypassed" ? <TriangleAlert size={14} /> : null}
        {status}
      </div>
    </div>
  );
}

export default function UploadPage({
  activeUser,
  protectionOn,
  registerScan,
  updateTrace,
  setPage,
  notify,
}) {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [scanRecord, setScanRecord] = useState(null);
  const [verificationQuery, setVerificationQuery] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verification, setVerification] = useState(null);
  const fileInput = useRef(null);
  const prompts = useMemo(() => getDemoPrompts(activeUser.id), [activeUser.id]);

  useEffect(() => {
    setFile(null);
    setScanRecord(null);
    setVerification(null);
    setVerificationQuery("");
    if (fileInput.current) fileInput.current.value = "";
  }, [activeUser.id]);

  function chooseFile(nextFile) {
    if (!nextFile) return;
    const name = nextFile.name.toLowerCase();
    if (!name.endsWith(".txt") && !name.endsWith(".pdf")) {
      notify("Only TXT and PDF files are supported by the backend.", "error");
      return;
    }
    setFile(nextFile);
    setScanRecord(null);
    setVerification(null);
  }

  async function processFile() {
    if (!file || processing) return;
    setProcessing(true);
    setScanRecord(null);
    setVerification(null);

    try {
      const result = await uploadAndScan(file, activeUser.tenant, protectionOn);
      const record = {
        document_id: result.upload.document_id,
        filename: result.upload.filename,
        tenant_id: result.upload.tenant_id,
        sha256: result.upload.sha256,
        ...result.scan,
        vector_store: result.scan.vector_store || result.upload.vector_store,
        scannedAt: Date.now(),
      };
      registerScan(record);
      setScanRecord(record);

      if (record.ragshield_enabled === false || record.status === "BASELINE_INDEXED") {
        notify(`${record.filename} was indexed in baseline mode with Layer 1 bypassed.`, "info");
      } else if (record.status === "APPROVED") {
        notify(`${record.filename} passed Layer 1 and was indexed.`, "success");
      } else {
        notify(`${record.filename} was quarantined at Layer 1.`, "error");
      }
    } catch (error) {
      notify(`Upload failed: ${error.message}`, "error");
      setScanRecord({
        filename: file.name,
        tenant_id: activeUser.tenant,
        status: "FAILED",
        error: error.message,
      });
    } finally {
      setProcessing(false);
    }
  }

  async function runVerification() {
    const query = verificationQuery.trim();
    const readyForQuery = scanRecord?.status === "APPROVED" || scanRecord?.status === "BASELINE_INDEXED";
    if (!query || verifying || !readyForQuery) return;
    setVerifying(true);

    try {
      const requestProtected = scanRecord?.ragshield_enabled !== false;
      const { payload, latencyMs } = await secureSearch(activeUser.id, query, requestProtected);
      const sources = payload.sources || [];
      const sourceTenantsValid = sources.every((source) => source.tenant_id === activeUser.tenant);

      const kind = payload.ragshield_enabled === false
        ? "baseline"
        : payload.layer_trace?.input_guard === "BLOCKED"
          ? "input-block"
          : payload.blocked
            ? "output-block"
            : "success";

      const nextTrace = {
        id: crypto.randomUUID(),
        query,
        answer: payload.answer || "",
        safe: payload.safe,
        blocked: Boolean(payload.blocked),
        threats: payload.threats || [],
        reason: payload.reason || "",
        sources,
        latencyMs,
        userId: activeUser.id,
        tenant: activeUser.tenant,
        authorizedTenant: payload.ragshield_enabled === false ? null : activeUser.tenant,
        ragshield_enabled: payload.ragshield_enabled ?? requestProtected,
        mode: payload.mode || (requestProtected ? "RAGSHIELD" : "BASELINE"),
        security_bypassed: Boolean(payload.security_bypassed),
        layer_trace: payload.layer_trace || null,
        timestamp: Date.now(),
        kind,
      };

      updateTrace(nextTrace);
      setVerification({ ...nextTrace, sourceTenantsValid });

      if (payload.ragshield_enabled === false) {
        notify("Baseline query completed without RAGShield verification.", "info");
      } else if (payload.safe === false || payload.blocked) {
        notify("Verification query was blocked by RAGShield.", "error");
      } else {
        notify("Layers 2 and 3 completed successfully.", "success");
      }
    } catch (error) {
      const nextTrace = {
        id: crypto.randomUUID(),
        query,
        answer: "",
        safe: false,
        blocked: true,
        sources: [],
        latencyMs: null,
        userId: activeUser.id,
        tenant: activeUser.tenant,
        authorizedTenant: scanRecord?.ragshield_enabled === false ? null : activeUser.tenant,
        ragshield_enabled: scanRecord?.ragshield_enabled !== false,
        mode: scanRecord?.ragshield_enabled === false ? "BASELINE" : "RAGSHIELD",
        security_bypassed: scanRecord?.ragshield_enabled === false,
        layer_trace: null,
        timestamp: Date.now(),
        kind: error.status === 403 ? "authorization-error" : "request-error",
        reason: error.message,
      };
      updateTrace(nextTrace);
      setVerification({ ...nextTrace, sourceTenantsValid: false });
      notify(`Verification failed: ${error.message}`, "error");
    } finally {
      setVerifying(false);
    }
  }

  const baselineMode = scanRecord?.ragshield_enabled === false || scanRecord?.mode === "BASELINE";
  const readyForQuery = scanRecord?.status === "APPROVED" || scanRecord?.status === "BASELINE_INDEXED";

  const layer1Status = processing
    ? "RUNNING"
    : baselineMode
      ? "BYPASSED"
      : scanRecord?.status || "WAITING";
  const layer2Status = verifying
    ? "RUNNING"
    : verification
      ? verification.layer_trace?.layer_2 === "BYPASSED"
        ? "BYPASSED"
        : verification.layer_trace?.layer_2?.startsWith("PASSED")
          ? "PASSED"
          : verification.layer_trace?.layer_2 === "NOT_RUN"
            ? "NOT REACHED"
            : verification.kind === "authorization-error" || verification.sourceTenantsValid === false
              ? "FAILED"
              : verification.kind === "input-block"
                ? "NOT REACHED"
                : "PASSED"
      : scanRecord?.status === "QUARANTINED" || scanRecord?.status === "FAILED"
        ? "NOT REACHED"
        : readyForQuery
          ? "WAITING FOR QUERY"
          : "WAITING";

  const layer3Status = verifying
    ? "RUNNING"
    : verification
      ? verification.layer_trace?.layer_3 === "BYPASSED"
        ? "BYPASSED"
        : verification.layer_trace?.layer_3 === "PASSED"
          ? "PASSED"
          : verification.layer_trace?.layer_3 === "NOT_RUN"
            ? "NOT REACHED"
            : verification.safe === false || verification.blocked
              ? "BLOCKED"
              : "PASSED"
      : scanRecord?.status === "QUARANTINED" || scanRecord?.status === "FAILED"
        ? "NOT REACHED"
        : readyForQuery
          ? "WAITING FOR GENERATION"
          : "WAITING";

  return (
    <div className="upload-page">
      <header className="upload-page-header">
        <div>
          <span className="upload-kicker"><UploadCloud size={15} /> Manual Document Verification</span>
          <h1>Upload. Inspect. Verify.</h1>
          <p>
            Test a document against the real backend. RAGShield ON runs Layer 1 at ingestion;
            RAGShield OFF sends the document through the baseline path with security checks bypassed.
          </p>
        </div>
        <div className="upload-identity">
          <span className={`mini-avatar ${activeUser.accent}`}>{activeUser.short}</span>
          <div><strong>{activeUser.id}</strong><span>{activeUser.tenant}</span></div>
        </div>
      </header>

      <div className="upload-workspace-grid">
        <section className="verification-card upload-drop-card">
          <div className="card-heading">
            <div><strong>1. Select document</strong><span>TXT or PDF · uploaded as {activeUser.tenant}</span></div>
          </div>

          <input
            ref={fileInput}
            hidden
            type="file"
            accept=".txt,.pdf,text/plain,application/pdf"
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />

          <div
            className={`upload-dropzone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              chooseFile(event.dataTransfer.files?.[0]);
            }}
            onClick={() => !file && fileInput.current?.click()}
          >
            {file ? (
              <div className="selected-file">
                <div className="selected-file-icon"><FileText size={28} /></div>
                <div>
                  <strong>{file.name}</strong>
                  <span>{(file.size / 1024).toFixed(1)} KB · {activeUser.tenant}</span>
                </div>
                <button
                  title="Remove file"
                  onClick={(event) => {
                    event.stopPropagation();
                    setFile(null);
                    setScanRecord(null);
                    setVerification(null);
                    if (fileInput.current) fileInput.current.value = "";
                  }}
                >
                  <X size={17} />
                </button>
              </div>
            ) : (
              <>
                <div className="drop-icon"><UploadCloud size={30} /></div>
                <strong>Drop a document here</strong>
                <span>or click to choose a TXT / PDF file</span>
              </>
            )}
          </div>

          <button className="primary-action wide" disabled={!file || processing} onClick={processFile}>
            {processing ? <LoaderCircle className="spin" size={18} /> : <ShieldCheck size={18} />}
            {processing
              ? protectionOn ? "Running ingestion security..." : "Uploading to baseline..."
              : protectionOn ? "Upload & Run Layer 1" : "Upload in Baseline Mode"}
          </button>

          {scanRecord && (
            <div className={`scan-summary ${baselineMode ? "baseline" : scanRecord.status === "APPROVED" ? "safe" : "danger"}`}>
              <div className="scan-summary-head">
                <div>
                  {!baselineMode && scanRecord.status === "APPROVED" ? <CheckCircle2 size={19} /> : <TriangleAlert size={19} />}
                  <strong>{baselineMode ? "BASELINE / SECURITY BYPASSED" : scanRecord.status}</strong>
                </div>
                {Number.isFinite(scanRecord.risk_score) && <span>Risk {scanRecord.risk_score}/100</span>}
              </div>
              {scanRecord.error ? (
                <p>{scanRecord.error}</p>
              ) : (
                <div className="scan-result-grid">
                  <div><span>ML prediction</span><strong>{scanRecord.ml_prediction || "—"}</strong></div>
                  <div><span>Malicious probability</span><strong>{scanRecord.ml_malicious_probability != null ? `${(scanRecord.ml_malicious_probability * 100).toFixed(1)}%` : "—"}</strong></div>
                  <div><span>Chunks added</span><strong>{scanRecord.vector_store?.chunks_added ?? 0}</strong></div>
                  <div><span>Document ID</span><strong className="mono">{scanRecord.document_id?.slice(0, 12) || "—"}…</strong></div>
                </div>
              )}
              {!scanRecord.error && scanRecord.detected_signals?.length > 0 && (
                <div className="scan-signals">
                  <span>Detected signals</span>
                  <div>{scanRecord.detected_signals.map((signal, index) => (
                    <small key={`${signal.type || "signal"}-${index}`}>{signal.type || "SIGNAL"}</small>
                  ))}</div>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="verification-card full-pipeline-card">
          <div className="card-heading">
            <div><strong>2. Three-layer verification</strong><span>Live status from the current manual test</span></div>
            <span className="live-pill"><i /> Backend</span>
          </div>

          <div className="upload-layer-stack">
            <LayerCard
              number="01"
              icon={FileCheck2}
              title="Ingestion Guard"
              subtitle="Rules + ML + risk scoring"
              status={layer1Status}
              detail={
                baselineMode
                  ? "Security scan skipped; document indexed in the separate baseline collection"
                  : scanRecord?.status === "APPROVED"
                  ? `Risk ${scanRecord.risk_score}/100 · indexed in ChromaDB`
                  : scanRecord?.status === "QUARANTINED"
                    ? "Stopped before vector storage"
                    : scanRecord?.error || "Waiting for a document"
              }
            />
            <div className={`upload-flow-line ${readyForQuery ? "active" : ""}`}><span /></div>
            <LayerCard
              number="02"
              icon={LockKeyhole}
              title="Retrieval Guard"
              subtitle={baselineMode ? "Authorization + tenant checks bypassed" : "Authorization + tenant-scoped search"}
              status={layer2Status}
              detail={
                verification
                  ? verification.ragshield_enabled === false
                    ? "Direct baseline retrieval; no tenant authorization guard"
                    : verification.sourceTenantsValid
                    ? `${activeUser.tenant} sources only`
                    : "Source tenant mismatch or authorization failure"
                  : readyForQuery
                    ? "Waiting for a verification query"
                    : "Runs only after safe ingestion"
              }
            />
            <div className={`upload-flow-line ${verification ? "active" : ""}`}><span /></div>
            <LayerCard
              number="03"
              icon={Sparkles}
              title="Output Guard"
              subtitle={baselineMode ? "Output verification bypassed" : "Grounding + output security"}
              status={layer3Status}
              detail={
                verification
                  ? verification.ragshield_enabled === false
                    ? "Raw Groq output returned without Layer 3 validation"
                    : verification.reason || "Output evaluated"
                  : readyForQuery
                    ? "Waiting for generation"
                    : "Runs only on generated output"
              }
            />
          </div>
        </section>
      </div>

      <section className="verification-card verification-query-card">
        <div className="card-heading">
          <div>
            <strong>3. Exercise Layers 2 + 3</strong>
            <span>{baselineMode
              ? "Ask a question to run the same document through the real baseline retrieval and raw generation path."
              : "After an APPROVED upload, ask a question to run real tenant retrieval and generation verification."}</span>
          </div>
        </div>

        <div className="upload-prompt-row">
          {prompts.slice(0, 2).map((item) => (
            <button
              key={item.id}
              className={`prompt-chip ${item.tone}`}
              disabled={!readyForQuery}
              onClick={() => setVerificationQuery(item.prompt)}
            >
              <Search size={14} />
              <span><strong>{item.label}</strong><small>{item.prompt}</small></span>
            </button>
          ))}
        </div>

        <div className="verification-query-box">
          <textarea
            value={verificationQuery}
            onChange={(event) => setVerificationQuery(event.target.value)}
            placeholder={
              readyForQuery
                ? "Ask a verification question about the tenant knowledge base..."
                : "Process a document first..."
            }
            disabled={!readyForQuery || verifying}
            rows={2}
          />
          <button
            className="primary-action"
            onClick={runVerification}
            disabled={!readyForQuery || !verificationQuery.trim() || verifying}
          >
            {verifying ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
            {verifying ? "Running query..." : baselineMode ? "Run Baseline Query" : "Run Layers 2 + 3"}
          </button>
        </div>

        {verification && (
          <div className={`full-verification-result ${verification.ragshield_enabled === false ? "baseline" : verification.safe === true ? "safe" : "danger"}`}>
            <div className="full-verification-result-head">
              <div>
                {verification.ragshield_enabled === false || verification.safe !== true ? <TriangleAlert size={20} /> : <CheckCircle2 size={20} />}
                <span>
                  <strong>{verification.ragshield_enabled === false
                    ? "Baseline / unverified response"
                    : verification.safe === true
                      ? "Full verification passed"
                      : "Verification blocked"}</strong>
                  <small>{verification.reason || "RAGShield completed the query trace."}</small>
                </span>
              </div>
              <button onClick={() => setPage("verification")}>Open detailed trace <ArrowRight size={14} /></button>
            </div>

            {verification.answer && (
              <div className="verification-answer">
                <span>Generated answer</span>
                <p>{verification.answer}</p>
              </div>
            )}

            <SourceList sources={verification.sources || []} tenant={activeUser.tenant} />
          </div>
        )}
      </section>

      <section className="upload-architecture-note">
        <Database size={17} />
        <p>
          <strong>Why this is split into two actions:</strong> Layer 1 is an ingestion-time check.
          Layers 2 and 3 are query-time checks. This page joins both phases into one demo workflow
          without pretending all three layers normally run during file upload.
        </p>
      </section>
    </div>
  );
}

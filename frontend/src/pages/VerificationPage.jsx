import {
  CheckCircle2,
  Clock3,
  Database,
  FileCheck2,
  FileText,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import FlowGraph from "../components/FlowGraph";
import MetricCard from "../components/MetricCard";
import RiskGauge from "../components/RiskGauge";
import { getUser } from "../config/users";

const MODEL_EVAL_ACCURACY = 100;
const MODEL_EVAL_SAMPLES = 17;

function statusClass(status) {
  if (["PASSED", "APPROVED", "ENFORCED", "ENFORCED_AT_INGESTION"].includes(status)) return "good";
  if (["FAILED", "BLOCKED", "QUARANTINED"].includes(status)) return "bad";
  if (status === "BYPASSED") return "bypassed";
  return "";
}

function evidenceClass(status) {
  if (["PASSED", "APPROVED", "ENFORCED", "ENFORCED_AT_INGESTION"].includes(status)) return "passed";
  if (["FAILED", "BLOCKED", "QUARANTINED"].includes(status)) return "blocked";
  if (status === "BYPASSED") return "bypassed";
  return "waiting";
}

function formatSimilarity(value) {
  if (!Number.isFinite(value)) return "N/A";
  return value >= 0 && value <= 1 ? `${(value * 100).toFixed(1)}%` : value.toFixed(3);
}

export default function VerificationPage({ trace, activeUser, scans, latencyHistory }) {
  const traceProtected = trace ? trace.ragshield_enabled !== false : true;
  const traceUser = trace?.userId ? getUser(trace.userId) : activeUser;
  const traceTenant = trace?.tenant || traceUser.tenant;
  const authorizedTenant = traceProtected ? (trace?.authorizedTenant || traceTenant) : null;

  const sources = trace?.sources || [];
  const matchedSource = sources[0] || null;
  const matchingScan = matchedSource
    ? scans.find((scan) => scan.document_id === matchedSource.document_id) || null
    : null;

  const authorizedSourceCount = traceProtected && authorizedTenant
    ? sources.filter((source) => source.tenant_id === authorizedTenant).length
    : 0;
  const unauthorizedSourceCount = traceProtected && sources.length
    ? sources.length - authorizedSourceCount
    : null;
  const sourceAuthorizationValid = traceProtected && sources.length
    ? unauthorizedSourceCount === 0
    : null;
  const sourceAuthorizationPercent = traceProtected && sources.length
    ? Math.round((authorizedSourceCount / sources.length) * 100)
    : null;

  const layerTrace = trace?.layer_trace || {};
  const inputGuardState = traceProtected ? layerTrace.input_guard : trace ? "BYPASSED" : null;
  const layer2State = traceProtected ? layerTrace.layer_2 : trace ? "BYPASSED" : null;
  const generationState = traceProtected ? layerTrace.generation : trace ? "RAW_BASELINE" : null;
  const layer3State = traceProtected ? layerTrace.layer_3 : trace ? "BYPASSED" : null;

  const safetyValue = !trace
    ? "Awaiting"
    : !traceProtected
      ? "Unverified"
      : layer3State === "PASSED"
        ? "Passed"
        : layer3State === "BLOCKED"
          ? "Blocked"
          : "Not run";

  const tenantValue = !trace
    ? "—"
    : !traceProtected
      ? "Bypassed"
      : sourceAuthorizationPercent == null
        ? "—"
        : `${sourceAuthorizationPercent}%`;

  const latencyValue = trace?.latencyMs != null
    ? `${(trace.latencyMs / 1000).toFixed(2)}s`
    : "—";

  const latencySeries = latencyHistory.length
    ? latencyHistory.map((item) => item / 1000)
    : [0];

  const riskScore = traceProtected && Number.isFinite(matchingScan?.risk_score)
    ? matchingScan.risk_score
    : null;

  const layer1EvidenceState = !trace
    ? "N/A"
    : !traceProtected
      ? "BYPASSED"
      : matchingScan?.status || (layerTrace.layer_1 === "ENFORCED_AT_INGESTION" ? "ENFORCED" : "N/A");

  const tenantCheckState = !trace
    ? "—"
    : !traceProtected
      ? "BYPASSED"
      : sources.length === 0
        ? "N/A"
        : sourceAuthorizationValid
          ? "PASSED"
          : "FAILED";

  const outputCheckState = !trace
    ? "—"
    : !traceProtected
      ? "BYPASSED"
      : layer3State || "NOT_RUN";

  const resultLabel = !trace
    ? "Awaiting query"
    : !traceProtected
      ? "Baseline / unverified response"
      : trace.blocked || trace.safe === false
        ? "Blocked by RAGShield"
        : layer3State === "PASSED"
          ? "Passed RAGShield verification"
          : "Protected request completed";

  const headerLabel = !trace
    ? "Ready"
    : !traceProtected
      ? "Baseline / Unprotected"
      : trace.blocked || trace.safe === false
        ? "Blocked"
        : "Protected";

  const headerTone = !traceProtected ? "baseline" : trace?.safe === false || trace?.blocked ? "danger" : "";

  return (
    <div className="verification-page">
      <header className="verification-header">
        <div>
          <div className="title-with-pill">
            <h1>RAGShield Verification Panel</h1>
            <span className={`protect-pill ${headerTone}`}>
              {!traceProtected || trace?.safe === false || trace?.blocked
                ? <TriangleAlert size={14} />
                : <ShieldCheck size={14} />}
              {headerLabel}
            </span>
          </div>
          <p>Validate sources, inspect the execution path, and show only security results supported by the saved request trace.</p>
        </div>
        <div className="verification-identity" title="Identity saved with this trace">
          <span className={`mini-avatar ${traceUser.accent}`}>{traceUser.short}</span>
          <div>
            <strong>{trace?.userId || traceUser.id}</strong>
            <span>{traceTenant} · {trace ? "trace identity" : "current identity"}</span>
          </div>
        </div>
      </header>

      <section className="verification-top-grid">
        <div className="verification-card risk-card">
          <div className="card-heading">
            <div><strong>Document Risk Score</strong><span>Layer 1 ingestion result for the exact retrieved document</span></div>
            {matchingScan?.status && traceProtected && (
              <span className={`micro-status ${matchingScan.status === "APPROVED" ? "safe" : "danger"}`}>{matchingScan.status}</span>
            )}
            {trace && !traceProtected && <span className="micro-status baseline">BYPASSED</span>}
          </div>
          <RiskGauge score={riskScore} status={matchingScan?.status} bypassed={trace != null && !traceProtected} />
        </div>

        <div className="verification-card metrics-card-shell">
          <div className="card-heading">
            <div><strong>Performance & Accuracy</strong><span>Real session telemetry + bundled classifier evaluation</span></div>
            <span className="live-pill"><i /> Live</span>
          </div>
          <div className="metrics-grid">
            <MetricCard
              label="Classifier Eval Accuracy"
              value={`${MODEL_EVAL_ACCURACY}%`}
              detail={`${MODEL_EVAL_SAMPLES}/${MODEL_EVAL_SAMPLES} bundled test samples`}
              tone="green"
              values={[100, 100, 100, 100]}
            />
            <MetricCard
              label="Output Safety"
              value={safetyValue}
              detail={!trace ? "No query evaluated yet" : !traceProtected ? "Layer 3 was bypassed" : trace.reason || "Backend output-guard state"}
              tone={!traceProtected && trace ? "red" : trace?.safe === false ? "red" : "blue"}
              values={trace ? [layer3State === "PASSED" ? 1 : 0] : [0]}
            />
            <MetricCard
              label="Source Authorization"
              value={tenantValue}
              detail={!trace
                ? "No trace yet"
                : !traceProtected
                  ? "Tenant authorization guard bypassed"
                  : sources.length
                    ? `${authorizedSourceCount}/${sources.length} sources authorized`
                    : "No sources returned"}
              tone={!traceProtected && trace ? "red" : sourceAuthorizationValid === false ? "red" : "violet"}
              values={traceProtected && sources.length ? [sourceAuthorizationPercent] : [0]}
            />
            <MetricCard
              label="End-to-End Latency"
              value={latencyValue}
              detail="Recent queries · browser-to-backend round trip"
              tone="cyan"
              values={latencySeries}
            />
          </div>
        </div>
      </section>

      <section className="verification-card graph-card">
        <div className="card-heading graph-heading">
          <div>
            <strong>Query Execution Graph</strong>
            <span>{traceProtected
              ? "Layer 1 reflects ingestion trust; Layers 2 and 3 reflect this saved protected query."
              : "This saved trace ran in BASELINE mode with RAGShield security layers bypassed."}</span>
          </div>
          <div className={`execution-complete ${!traceProtected || trace?.safe === false || trace?.blocked ? "danger" : ""}`}>
            {!traceProtected || trace?.safe === false || trace?.blocked ? <TriangleAlert size={15} /> : <CheckCircle2 size={15} />}
            {!trace ? "Awaiting query" : !traceProtected ? "Baseline · unverified" : trace.safe === false || trace.blocked ? "Execution blocked" : "Execution verified"}
          </div>
        </div>
        <div className="detailed-flow-wrap">
          <FlowGraph
            protectedView={trace ? traceProtected : true}
            detailed
            trace={trace}
            matchedSource={matchedSource}
            matchingScan={matchingScan}
          />
        </div>

        {trace && (
          <div className={`trace-answer-summary ${traceProtected ? "protected" : "baseline"}`}>
            <div>
              <span>QUERY</span>
              <p>{trace.query || "—"}</p>
            </div>
            <div>
              <span>GENERATED ANSWER</span>
              <p>{trace.answer || "No answer returned."}</p>
            </div>
            <div className="trace-result-line">
              <span>RESULT</span>
              <strong>{resultLabel}</strong>
            </div>
          </div>
        )}
      </section>

      <section className="verification-detail-grid">
        <div className="verification-card detail-card">
          <div className="card-heading">
            <div><strong>Top Retrieved Source</strong><span>{sources.length} retrieved source{sources.length === 1 ? "" : "s"}</span></div>
          </div>
          {matchedSource ? (
            <>
              <div className="matched-file-head">
                <div className="big-file-icon"><FileText size={23} /></div>
                <div>
                  <strong>{matchedSource.filename}</strong>
                  <span>
                    {traceProtected
                      ? sourceAuthorizationValid === false && matchedSource.tenant_id !== authorizedTenant
                        ? <><TriangleAlert size={12} /> Tenant mismatch</>
                        : <><ShieldCheck size={12} /> Authorized source</>
                      : <><TriangleAlert size={12} /> Baseline source · not authorization-checked</>}
                  </span>
                </div>
              </div>
              <div className="detail-table">
                <div><span>Tenant</span><strong>{matchedSource.tenant_id}</strong></div>
                <div><span>Document ID</span><strong className="mono truncate">{matchedSource.document_id}</strong></div>
                <div><span>Layer 1 status</span><strong>{!traceProtected ? "BYPASSED" : matchingScan?.status || "N/A"}</strong></div>
                <div><span>Similarity score</span><strong>{formatSimilarity(matchedSource.similarity_score)}</strong></div>
              </div>
              {sources.length > 1 && (
                <details className="retrieved-source-details">
                  <summary>View all {sources.length} retrieved sources</summary>
                  <div>
                    {sources.map((source, index) => (
                      <span key={`${source.document_id}-${index}`}>
                        <FileText size={12} /> {source.filename} · {source.tenant_id}
                      </span>
                    ))}
                  </div>
                </details>
              )}
            </>
          ) : (
            <div className="detail-empty"><FileText size={24} /><span>No retrieved source for the current trace.</span></div>
          )}
        </div>

        <div className="verification-card detail-card">
          <div className="card-heading"><div><strong>Verification Results</strong><span>States from the saved backend trace</span></div></div>
          <div className="verification-list">
            <div>
              {inputGuardState === "BLOCKED" ? <TriangleAlert /> : <CheckCircle2 />}
              <span><strong>Input threat check</strong><small>{!trace ? "Awaiting query" : !traceProtected ? "Input guard not executed" : trace.reason || "Backend input-guard state"}</small></span>
              <b className={statusClass(inputGuardState)}>{inputGuardState || "—"}</b>
            </div>
            <div>
              <LockKeyhole />
              <span><strong>Tenant isolation</strong><small>{!trace ? "Awaiting query" : !traceProtected ? "No authorization or tenant filtering" : authorizedTenant ? `${authorizedTenant} authorized scope` : "Authorization unavailable"}</small></span>
              <b className={statusClass(tenantCheckState)}>{tenantCheckState}</b>
            </div>
            <div>
              <ShieldCheck />
              <span><strong>Output grounding</strong><small>{!trace ? "Awaiting query" : !traceProtected ? "Output guard not executed" : trace.reason || "Backend output-guard state"}</small></span>
              <b className={statusClass(outputCheckState)}>{outputCheckState}</b>
            </div>
            <div>
              <Clock3 />
              <span><strong>Response time</strong><small>Measured in this browser session</small></span>
              <b>{latencyValue}</b>
            </div>
          </div>
        </div>

        <div className="verification-card detail-card">
          <div className="card-heading"><div><strong>Security Evidence</strong><span>Non-fabricated evidence behind this trace</span></div></div>
          <div className="layer-result-list">
            <div className={evidenceClass(layer1EvidenceState)}>
              <div className="layer-icon"><FileCheck2 size={18} /></div>
              <span>
                <strong>Layer 1 · Ingestion Guard</strong>
                <small>{!trace
                  ? "Awaiting trace"
                  : !traceProtected
                    ? "Risk N/A · ML NOT_RUN"
                    : matchingScan
                      ? `Risk ${matchingScan.risk_score}/100 · ML ${matchingScan.ml_prediction || "N/A"}${matchingScan.ml_malicious_probability != null ? ` · malicious ${(matchingScan.ml_malicious_probability * 100).toFixed(1)}%` : ""}`
                      : "Risk N/A · ML N/A for this retrieved source"}</small>
              </span>
              <b>{layer1EvidenceState}</b>
            </div>
            <div className={evidenceClass(!traceProtected && trace ? "BYPASSED" : sourceAuthorizationValid === false ? "FAILED" : layer2State)}>
              <div className="layer-icon"><Database size={18} /></div>
              <span>
                <strong>Layer 2 · Retrieval Guard</strong>
                <small>{!trace
                  ? "Awaiting trace"
                  : !traceProtected
                    ? `Authorization bypassed · ${sources.length} sources returned`
                    : `Authorized tenant: ${authorizedTenant || "N/A"} · Sources checked: ${sources.length} · Unauthorized: ${unauthorizedSourceCount ?? "N/A"}`}</small>
              </span>
              <b>{!trace ? "N/A" : !traceProtected ? "BYPASSED" : sourceAuthorizationValid === false ? "FAILED" : layer2State || "N/A"}</b>
            </div>
            <div className={evidenceClass(outputCheckState)}>
              <div className="layer-icon"><Sparkles size={18} /></div>
              <span>
                <strong>Layer 3 · Output Guard</strong>
                <small>{!trace
                  ? "Awaiting trace"
                  : !traceProtected
                    ? `Generation ${generationState || "RAW_BASELINE"} · output validation bypassed`
                    : trace.reason || `Output guard: ${outputCheckState}`}</small>
              </span>
              <b>{outputCheckState === "—" ? "N/A" : outputCheckState}</b>
            </div>
          </div>
        </div>
      </section>

      <section className="truth-note">
        <ShieldCheck size={16} />
        <span><strong>Metric integrity:</strong> classifier accuracy is the bundled backend model's 17/17 test-set result. End-to-end latency is measured in this browser session. Source authorization is derived from the saved trace. Risk and similarity are shown only when data for the exact source is available.</span>
      </section>
    </div>
  );
}

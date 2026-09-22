import {
  Bot,
  CheckCircle2,
  Database,
  FileCheck2,
  FileText,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  UserRound,
} from "lucide-react";

function FlowNode({ icon: Icon, title, subtitle, meta, state = "safe" }) {
  return (
    <div className={`flow-node ${state}`}>
      <div className="flow-node-icon">
        <Icon size={19} strokeWidth={1.8} />
      </div>
      <div className="flow-node-copy">
        <strong>{title}</strong>
        {subtitle && <span>{subtitle}</span>}
        {meta && <small>{meta}</small>}
      </div>
    </div>
  );
}

function Edge({ danger = false }) {
  return (
    <div className={`flow-edge ${danger ? "danger" : ""}`}>
      <span className="flow-pulse" />
      <i />
    </div>
  );
}

export default function FlowGraph({
  protectedView = true,
  detailed = false,
  trace,
  matchedSource,
  matchingScan,
}) {
  const blockedInput = trace?.kind === "input-block";
  const unauthorized = trace?.kind === "authorization-error";
  const outputBlocked = trace?.kind === "output-block";

  if (!protectedView) {
    if (detailed) {
      return (
        <div className="flow-row detailed">
          <FlowNode icon={UserRound} title="User Query" subtitle={trace?.query || "Awaiting query"} state="muted" />
          <Edge danger />
          <FlowNode icon={FileCheck2} title="Layer 1" subtitle="Ingestion Guard" meta="BYPASSED" state="warning" />
          <Edge danger />
          <FlowNode icon={LockKeyhole} title="Layer 2" subtitle="Retrieval Guard" meta="BYPASSED" state="warning" />
          <Edge danger />
          <FlowNode icon={Bot} title="Groq" subtitle="Raw generation" state="muted" />
          <Edge danger />
          <FlowNode icon={ShieldCheck} title="Layer 3" subtitle="Output Guard" meta="BYPASSED" state="warning" />
          <Edge danger />
          <FlowNode icon={TriangleAlert} title="Unverified Response" subtitle="Baseline output" state="warning" />
        </div>
      );
    }

    return (
      <div className="flow-column">
        <FlowNode icon={UserRound} title="User Query" subtitle={trace?.query || "Waiting for a message"} state="muted" />
        <div className="vertical-edge danger"><span /></div>
        <FlowNode icon={FileCheck2} title="Layer 1" subtitle="BYPASSED" state="warning" />
        <div className="vertical-edge danger"><span /></div>
        <FlowNode icon={LockKeyhole} title="Layer 2" subtitle="BYPASSED · no tenant guard" state="warning" />
        <div className="vertical-edge danger"><span /></div>
        <FlowNode icon={Bot} title="Groq" subtitle="Raw baseline generation" state="muted" />
        <div className="vertical-edge danger"><span /></div>
        <FlowNode icon={ShieldCheck} title="Layer 3" subtitle="BYPASSED" state="warning" />
        <div className="vertical-edge danger"><span /></div>
        <FlowNode icon={TriangleAlert} title="Unverified Response" subtitle="Baseline output" state="warning" />
      </div>
    );
  }

  if (blockedInput) {
    return (
      <div className={`flow-row ${detailed ? "detailed" : ""}`}>
        <FlowNode icon={UserRound} title="User Query" subtitle="Received" />
        <Edge danger />
        <FlowNode
          icon={TriangleAlert}
          title="Input Guard"
          subtitle="Threat detected"
          meta={trace?.threats?.[0] || "Blocked"}
          state="danger"
        />
        <Edge danger />
        <FlowNode icon={ShieldCheck} title="Blocked" subtitle="Stopped before retrieval" state="danger" />
      </div>
    );
  }

  if (unauthorized) {
    return (
      <div className={`flow-row ${detailed ? "detailed" : ""}`}>
        <FlowNode icon={UserRound} title="User Query" subtitle="Received" />
        <Edge danger />
        <FlowNode icon={LockKeyhole} title="Authorization" subtitle="Access denied" state="danger" />
        <Edge danger />
        <FlowNode icon={ShieldCheck} title="Blocked" subtitle="No tenant access" state="danger" />
      </div>
    );
  }

  if (detailed) {
    const scanMeta = matchingScan
      ? `Risk ${matchingScan.risk_score}/100`
      : "Ingestion metadata N/A";
    const layer2State = trace?.layer_trace?.layer_2 || "NOT_RUN";
    const layer3State = trace?.layer_trace?.layer_3 || "NOT_RUN";

    return (
      <div className="flow-row detailed">
        <FlowNode icon={UserRound} title="User Query" subtitle={trace?.query || "Awaiting query"} />
        <Edge />
        <FlowNode
          icon={FileText}
          title="Matched File"
          subtitle={matchedSource?.filename || "Awaiting source"}
          meta={matchedSource?.tenant_id || "No source yet"}
          state={matchedSource ? "source" : "muted"}
        />
        <Edge />
        <FlowNode
          icon={FileCheck2}
          title="Layer 1"
          subtitle="Ingestion Guard"
          meta={scanMeta}
          state={matchedSource ? "safe" : "muted"}
        />
        <Edge />
        <FlowNode
          icon={LockKeyhole}
          title="Layer 2"
          subtitle="Retrieval Guard"
          meta={layer2State === "PASSED" || layer2State === "PASSED_NO_MATCH"
            ? `${trace?.tenant || "Tenant"} scope · ${layer2State}`
            : layer2State}
          state={layer2State.startsWith("PASSED") ? "safe" : layer2State === "NOT_RUN" ? "muted" : "danger"}
        />
        <Edge />
        <FlowNode
          icon={Sparkles}
          title="Groq"
          subtitle={trace?.layer_trace?.generation === "COMPLETED" ? "GPT OSS 20B generation" : "Not run"}
          state={trace?.layer_trace?.generation === "COMPLETED" ? "safe" : "muted"}
        />
        <Edge danger={outputBlocked} />
        <FlowNode
          icon={ShieldCheck}
          title="Layer 3"
          subtitle="Output Guard"
          meta={layer3State}
          state={layer3State === "PASSED" ? "safe" : layer3State === "BLOCKED" ? "danger" : "muted"}
        />
        <Edge danger={outputBlocked} />
        <FlowNode
          icon={outputBlocked ? TriangleAlert : CheckCircle2}
          title={outputBlocked ? "Blocked Response" : layer3State === "PASSED" ? "Safe Response" : "Response Pending"}
          subtitle={outputBlocked ? "Not delivered" : layer3State === "PASSED" ? "Delivered" : "Awaiting verification"}
          state={outputBlocked ? "danger" : layer3State === "PASSED" ? "safe" : "muted"}
        />
      </div>
    );
  }

  return (
    <div className="flow-column">
      <FlowNode icon={UserRound} title="User Query" subtitle={trace?.query || "Waiting for a message"} />
      <div className="vertical-edge"><span /></div>
      <FlowNode icon={LockKeyhole} title="Retrieval Guard" subtitle="Authorization + tenant scope" />
      <div className="vertical-edge"><span /></div>
      <FlowNode icon={Database} title="Vector Search" subtitle="Authorized documents only" />
      <div className="vertical-edge"><span /></div>
      <FlowNode icon={Sparkles} title="Groq" subtitle="GPT OSS 20B generation" />
      <div className={`vertical-edge ${outputBlocked ? "danger" : ""}`}><span /></div>
      <FlowNode
        icon={ShieldCheck}
        title="Output Guard"
        subtitle={outputBlocked ? "Response blocked" : "Safety + grounding"}
        state={outputBlocked ? "danger" : "safe"}
      />
      <div className={`vertical-edge ${outputBlocked ? "danger" : ""}`}><span /></div>
      <FlowNode
        icon={outputBlocked ? TriangleAlert : CheckCircle2}
        title={outputBlocked ? "Blocked" : "Safe Response"}
        subtitle={trace ? (outputBlocked ? "Stopped" : "Verified") : "Awaiting response"}
        state={outputBlocked ? "danger" : "safe"}
      />
    </div>
  );
}

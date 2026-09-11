import { useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Copy,
  FileText,
  LoaderCircle,
  Paperclip,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  UserRound,
} from "lucide-react";
import FlowGraph from "../components/FlowGraph";
import SourceList from "../components/SourceList";
import { secureSearch, uploadAndScan } from "../services/api";
import { getDemoPrompts } from "../config/prompts";

function formatTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function Message({ message, onViewTrace }) {
  const assistant = message.role === "assistant";
  const baseline = assistant && message.ragshield_enabled === false;
  return (
    <article className={`message-card ${assistant ? "assistant" : "user"} ${message.safe === false ? "blocked" : ""}`}>
      <div className="message-avatar">
        {assistant ? <ShieldCheck size={18} /> : <UserRound size={18} />}
      </div>
      <div className="message-body">
        <div className="message-header">
          <strong>{assistant ? "RAGShield" : "You"}</strong>
          <time>{message.time}</time>
        </div>
        <p>{message.text}</p>

        {assistant && message.sources?.length > 0 && (
          <div className="inline-sources">
            <span>Sources</span>
            <div>
              {message.sources.slice(0, 3).map((source, index) => (
                <span className="inline-source" key={`${source.document_id}-${index}`}>
                  <FileText size={13} />
                  {source.filename}
                </span>
              ))}
            </div>
          </div>
        )}

        {assistant && (
          <div className="message-footer">
            <div className={baseline ? "secured-tag baseline" : message.safe === false ? "secured-tag danger" : "secured-tag"}>
              {baseline || message.safe === false ? <TriangleAlert size={14} /> : <CheckCircle2 size={14} />}
              {baseline
                ? "Baseline / Unverified"
                : message.safe === false
                  ? "Blocked by RAGShield"
                  : "Secured by RAGShield"}
            </div>
            <div className="message-actions">
              <button
                title="Copy answer"
                onClick={() => navigator.clipboard?.writeText(message.text)}
              >
                <Copy size={14} />
              </button>
              <button className="trace-link" onClick={onViewTrace}>
                View trace <ArrowUpRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>
    </article>
  );
}

export default function ChatPage({
  activeUser,
  protectionOn,
  setProtectionOn,
  messages,
  addMessages,
  updateTrace,
  trace,
  setPage,
  registerScan,
  notify,
}) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [rightTab, setRightTab] = useState("graph");
  const fileInput = useRef(null);

  const currentTrace = trace?.userId === activeUser.id ? trace : null;
  const latestSources = currentTrace?.sources || [];
  const demoPrompts = useMemo(() => getDemoPrompts(activeUser.id), [activeUser.id]);

  const headline = useMemo(() => {
    if (messages.length) return "Secure document chat";
    return "How can I help you today?";
  }, [messages.length]);

  async function sendMessage(promptOverride = null) {
    const query = (typeof promptOverride === "string" ? promptOverride : input).trim();
    if (!query || sending) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: query,
      time: formatTime(),
    };

    addMessages([userMessage]);
    setInput("");
    setSending(true);

    try {
      const { payload, latencyMs } = await secureSearch(activeUser.id, query, protectionOn);
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
        answer: payload.answer,
        safe: payload.safe,
        blocked: Boolean(payload.blocked),
        threats: payload.threats || [],
        reason: payload.reason || "",
        sources: payload.sources || [],
        latencyMs,
        userId: activeUser.id,
        tenant: activeUser.tenant,
        authorizedTenant: payload.ragshield_enabled === false ? null : activeUser.tenant,
        ragshield_enabled: payload.ragshield_enabled ?? protectionOn,
        mode: payload.mode || (protectionOn ? "RAGSHIELD" : "BASELINE"),
        security_bypassed: Boolean(payload.security_bypassed),
        layer_trace: payload.layer_trace || null,
        timestamp: Date.now(),
        kind,
      };

      updateTrace(nextTrace);

      addMessages([
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: payload.answer || "No answer returned.",
          sources: payload.sources || [],
          safe: payload.safe,
          ragshield_enabled: payload.ragshield_enabled ?? protectionOn,
          mode: payload.mode || (protectionOn ? "RAGSHIELD" : "BASELINE"),
          time: formatTime(),
        },
      ]);
    } catch (error) {
      const kind = error.status === 403 ? "authorization-error" : "request-error";
      updateTrace({
        id: crypto.randomUUID(),
        query,
        answer: "",
        safe: false,
        blocked: true,
        sources: [],
        latencyMs: null,
        userId: activeUser.id,
        tenant: activeUser.tenant,
        authorizedTenant: protectionOn ? activeUser.tenant : null,
        ragshield_enabled: protectionOn,
        mode: protectionOn ? "RAGSHIELD" : "BASELINE",
        security_bypassed: !protectionOn,
        layer_trace: null,
        timestamp: Date.now(),
        kind,
        reason: error.message,
      });

      addMessages([
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: error.status === 403 ? "Access denied for this user." : `Backend error: ${error.message}`,
          sources: [],
          safe: false,
          ragshield_enabled: protectionOn,
          mode: protectionOn ? "RAGSHIELD" : "BASELINE",
          time: formatTime(),
        },
      ]);
      notify(error.message, "error");
    } finally {
      setSending(false);
    }
  }

  async function handleFile(file) {
    if (!file) return;
    setUploading(true);
    notify(
      protectionOn
        ? `Scanning ${file.name} for ${activeUser.tenant}...`
        : `Uploading ${file.name} to the baseline collection...`,
      "info"
    );

    try {
      const result = await uploadAndScan(file, activeUser.tenant, protectionOn);
      registerScan({
        document_id: result.upload.document_id,
        filename: result.upload.filename,
        tenant_id: result.upload.tenant_id,
        sha256: result.upload.sha256,
        ...result.scan,
        vector_store: result.scan.vector_store || result.upload.vector_store,
        scannedAt: Date.now(),
      });

      if (result.scan.ragshield_enabled === false || result.scan.status === "BASELINE_INDEXED") {
        notify(`${file.name} indexed in baseline mode with security bypassed.`, "info");
      } else if (result.scan.status === "APPROVED") {
        notify(`${file.name} approved and indexed.`, "success");
      } else {
        notify(`${file.name} quarantined. Risk ${result.scan.risk_score}/100.`, "error");
      }
    } catch (error) {
      notify(`File processing failed: ${error.message}`, "error");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function keyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="chat-layout">
      <section className="chat-panel panel-shell">
        <div className="chat-hero">
          <div className="hero-orbit">
            <span /><i /><b />
          </div>
          <h1>{headline}</h1>
          <p>
            Ask questions about your authorized documents. RAGShield keeps retrieval tenant-scoped and verifies generated output before delivery.
          </p>
          <div className="identity-line">
            <span className={`mini-avatar ${activeUser.accent}`}>{activeUser.short}</span>
            <span>{activeUser.id}</span>
            <i />
            <span>{activeUser.tenant}</span>
          </div>
        </div>

        <div className="message-stream">
          {messages.length === 0 ? (
            <div className="chat-empty-state prompt-empty-state">
              <div className="empty-state-head">
                <Sparkles size={24} />
                <div>
                  <strong>Demo-ready prompts</strong>
                  <span>Use a prepared test so the right tenant and security behavior are easy to demonstrate.</span>
                </div>
              </div>

              <div className="demo-prompt-grid">
                {demoPrompts.map((item) => (
                  <button
                    key={item.id}
                    className={`demo-prompt-card ${item.tone}`}
                    onClick={() => sendMessage(item.prompt)}
                    disabled={sending}
                  >
                    <span className="demo-prompt-icon"><Search size={15} /></span>
                    <span className="demo-prompt-copy">
                      <strong>{item.label}</strong>
                      <small>{item.prompt}</small>
                      <em>{item.hint}</em>
                    </span>
                    <ArrowUpRight size={15} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <Message
                key={message.id}
                message={message}
                onViewTrace={() => setPage("verification")}
              />
            ))
          )}
          {sending && (
            <div className="thinking-row">
              <LoaderCircle className="spin" size={18} />
              RAGShield is retrieving authorized evidence and verifying the response...
            </div>
          )}
        </div>

        <div className="composer-area">
          <input
            ref={fileInput}
            type="file"
            accept=".txt,.pdf,text/plain,application/pdf"
            hidden
            onChange={(event) => handleFile(event.target.files?.[0])}
          />
          <div className="composer-box">
            <button
              className="composer-tool"
              title={`Upload + scan a TXT/PDF as ${activeUser.tenant}`}
              disabled={uploading}
              onClick={() => fileInput.current?.click()}
            >
              {uploading ? <LoaderCircle className="spin" size={19} /> : <Paperclip size={19} />}
            </button>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={keyDown}
              placeholder="Ask a question about your documents..."
              rows={1}
            />
            <button className="send-btn" onClick={sendMessage} disabled={!input.trim() || sending}>
              <Send size={18} />
            </button>
          </div>
          <div className="composer-note">
            <ShieldCheck size={12} />
            {protectionOn
              ? "RAGShield is ON. The next query uses the protected backend pipeline."
              : "RAGShield is OFF. The next query uses the baseline backend path with security layers bypassed."}
          </div>
        </div>
      </section>

      <aside className="pipeline-panel panel-shell">
        <div className="pipeline-tabs">
          <button className={rightTab === "graph" ? "active" : ""} onClick={() => setRightTab("graph")}>Execution Graph</button>
          <button className={rightTab === "sources" ? "active" : ""} onClick={() => setRightTab("sources")}>Sources <span>{latestSources.length}</span></button>
        </div>

        {rightTab === "graph" ? (
          <>
            <div className="comparison-heading">
              <div className={protectionOn ? "status-dot-line active" : "status-dot-line"}>
                <i />
                <div>
                  <strong>{protectionOn ? "RAGShield ON" : "RAGShield OFF"}</strong>
                  <span>{protectionOn ? "Secured execution" : "Baseline / unprotected"}</span>
                </div>
              </div>
              <button className="mini-toggle" onClick={() => setProtectionOn(!protectionOn)}>
                {protectionOn ? "Protected" : "Baseline"}
              </button>
            </div>
            <div className="pipeline-flow-wrap">
              <FlowGraph protectedView={protectionOn} trace={currentTrace} />
            </div>
            <div className={`pipeline-insight ${protectionOn ? "safe" : "warn"}`}>
              {protectionOn ? <ShieldCheck size={20} /> : <TriangleAlert size={20} />}
              <div>
                <strong>{protectionOn ? "Protected pipeline" : "Baseline / unprotected"}</strong>
                <span>
                  {protectionOn
                    ? "Authorization, tenant-scoped retrieval and output checks stay visible end to end."
                    : "The backend bypasses RAGShield security layers and returns the raw baseline RAG response."}
                </span>
              </div>
            </div>
          </>
        ) : (
          <SourceList sources={latestSources} tenant={activeUser.tenant} />
        )}
      </aside>
    </div>
  );
}

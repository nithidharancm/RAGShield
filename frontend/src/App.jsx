import { useEffect, useMemo, useState } from "react";
import { Activity, CircleDot, Menu, ShieldCheck, X } from "lucide-react";
import Sidebar from "./components/Sidebar";
import ShieldToggle from "./components/ShieldToggle";
import Toast from "./components/Toast";
import ChatPage from "./pages/ChatPage";
import VerificationPage from "./pages/VerificationPage";
import UploadPage from "./pages/UploadPage";
import usePersistentState from "./hooks/usePersistentState";
import { DEMO_USERS, getUser } from "./config/users";
import { checkHealth } from "./services/api";

function makeChat(userId) {
  const user = getUser(userId);
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    tenant: user.tenant,
    userId,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
}

export default function App() {
  const [page, setPage] = useState("chat");
  const [protectionOn, setProtectionOn] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [health, setHealth] = useState("checking");
  const [toast, setToast] = useState(null);

  const [activeUserId, setActiveUserId] = usePersistentState("ragshield.user.v2", DEMO_USERS[0].id);
  const [histories, setHistories] = usePersistentState("ragshield.history.v2", []);
  const [activeChatId, setActiveChatId] = usePersistentState("ragshield.activeChat.v2", null);
  const [trace, setTrace] = usePersistentState("ragshield.trace.v2", null);
  const [scans, setScans] = usePersistentState("ragshield.scans.v2", []);
  const [latencyHistory, setLatencyHistory] = usePersistentState("ragshield.latencies.v2", []);

  const activeUser = getUser(activeUserId);

  const activeChat = useMemo(
    () => histories.find((chat) => chat.id === activeChatId) || null,
    [histories, activeChatId]
  );

  const messages = activeChat?.messages || [];

  useEffect(() => {
    let alive = true;
    checkHealth()
      .then((result) => alive && setHealth(result?.status === "ok" ? "online" : "offline"))
      .catch(() => alive && setHealth("offline"));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!activeChatId && histories.length) setActiveChatId(histories[0].id);
  }, [activeChatId, histories, setActiveChatId]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3800);
    return () => clearTimeout(timer);
  }, [toast]);

  function notify(message, type = "info") {
    setToast({ id: Date.now(), message, type });
  }

  function createNewChat() {
    const next = makeChat(activeUserId);
    setHistories((current) => [next, ...current].slice(0, 20));
    setActiveChatId(next.id);
    setTrace(null);
    setPage("chat");
    setMobileOpen(false);
  }

  function ensureChat() {
    if (activeChat) return activeChat.id;
    const next = makeChat(activeUserId);
    setHistories((current) => [next, ...current].slice(0, 20));
    setActiveChatId(next.id);
    return next.id;
  }

  function addMessages(nextMessages) {
    const chatId = ensureChat();
    setHistories((current) => {
      const exists = current.some((chat) => chat.id === chatId);
      const base = exists ? current : [{ ...makeChat(activeUserId), id: chatId }, ...current];

      return base.map((chat) => {
        if (chat.id !== chatId) return chat;
        const combined = [...(chat.messages || []), ...nextMessages];
        const firstUser = combined.find((message) => message.role === "user");
        const title = firstUser
          ? firstUser.text.slice(0, 36) + (firstUser.text.length > 36 ? "…" : "")
          : chat.title;
        return {
          ...chat,
          userId: activeUserId,
          tenant: activeUser.tenant,
          title,
          messages: combined,
          updatedAt: Date.now(),
        };
      }).sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 20);
    });
  }

  function updateTrace(nextTrace) {
    setTrace(nextTrace);
    if (nextTrace?.latencyMs != null) {
      setLatencyHistory((history) => [...history, nextTrace.latencyMs].slice(-12));
    }
  }

  function registerScan(scan) {
    setScans((current) => [scan, ...current.filter((item) => item.document_id !== scan.document_id)].slice(0, 30));
  }

  function loadChat(chatId) {
    const chat = histories.find((item) => item.id === chatId);
    if (!chat) return;
    setActiveChatId(chatId);
    if (chat.userId) setActiveUserId(chat.userId);
    setPage("chat");
    setMobileOpen(false);
  }

  function changeUser(userId) {
    const user = getUser(userId);
    setActiveUserId(userId);

    if (page === "chat") {
      const next = makeChat(userId);
      setHistories((current) => [next, ...current].slice(0, 20));
      setActiveChatId(next.id);
    }

    notify(`Active identity: ${userId} → ${user.tenant}`, "info");
  }

  return (
    <div className="app-shell">
      <div className={`mobile-scrim ${mobileOpen ? "visible" : ""}`} onClick={() => setMobileOpen(false)} />
      <div className={`sidebar-wrap ${mobileOpen ? "mobile-open" : ""}`}>
        <button className="mobile-close" onClick={() => setMobileOpen(false)}><X size={18} /></button>
        <Sidebar
          page={page}
          setPage={(next) => { setPage(next); setMobileOpen(false); }}
          histories={histories}
          activeChatId={activeChatId}
          loadChat={loadChat}
          newChat={createNewChat}
          activeUserId={activeUserId}
          setActiveUserId={changeUser}
        />
      </div>

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu size={19} /></button>
            <div className="page-kicker">
              <span className="kicker-icon"><ShieldCheck size={14} /></span>
              <div>
                <strong>{
                  page === "chat"
                    ? "Secure Knowledge Assistant"
                    : page === "verification"
                      ? "Security Trace & Verification"
                      : "Manual Upload & Verification"
                }</strong>
                <span>{page === "verification" && trace
                  ? `${trace.userId || "trace user"} · ${trace.tenant || "trace tenant"} · saved trace`
                  : `${activeUser.id} · ${activeUser.tenant}`}</span>
              </div>
            </div>
          </div>

          <div className="topbar-right">
            <div className={`health-pill ${health}`}>
              <CircleDot size={12} />
              <span>{health === "online" ? "Backend Online" : health === "checking" ? "Checking Backend" : "Backend Offline"}</span>
            </div>
            <ShieldToggle enabled={protectionOn} onChange={setProtectionOn} />
          </div>
        </header>

        <main className="content-area">
          {page === "chat" ? (
            <ChatPage
              activeUser={activeUser}
              protectionOn={protectionOn}
              setProtectionOn={setProtectionOn}
              messages={messages}
              addMessages={addMessages}
              updateTrace={updateTrace}
              trace={trace}
              setPage={setPage}
              registerScan={registerScan}
              notify={notify}
            />
          ) : page === "verification" ? (
            <VerificationPage
              trace={trace}
              activeUser={activeUser}
              scans={scans}
              latencyHistory={latencyHistory}
            />
          ) : (
            <UploadPage
              activeUser={activeUser}
              protectionOn={protectionOn}
              registerScan={registerScan}
              updateTrace={updateTrace}
              setPage={setPage}
              notify={notify}
            />
          )}
        </main>
      </div>

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}

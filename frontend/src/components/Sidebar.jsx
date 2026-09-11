import {
  FileClock,
  MessageSquareText,
  Plus,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import Brand from "./Brand";
import UserSwitcher from "./UserSwitcher";

export default function Sidebar({
  page,
  setPage,
  histories,
  activeChatId,
  loadChat,
  newChat,
  activeUserId,
  setActiveUserId,
}) {
  return (
    <aside className="sidebar">
      <Brand />

      <button className="new-chat-btn" onClick={newChat}>
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      <nav className="main-nav">
        <button
          className={`nav-button ${page === "chat" ? "active" : ""}`}
          onClick={() => setPage("chat")}
        >
          <MessageSquareText size={17} />
          <span>Chat</span>
        </button>
        <button
          className={`nav-button ${page === "verification" ? "active" : ""}`}
          onClick={() => setPage("verification")}
        >
          <ShieldCheck size={17} />
          <span>Verification</span>
        </button>
        <button
          className={`nav-button ${page === "upload" ? "active" : ""}`}
          onClick={() => setPage("upload")}
        >
          <UploadCloud size={17} />
          <span>Upload & Verify</span>
        </button>
      </nav>

      <div className="sidebar-divider" />

      <div className="history-block">
        <div className="sidebar-section-heading">
          <span>Recent</span>
          <FileClock size={14} />
        </div>
        <div className="history-list">
          {histories.length === 0 ? (
            <div className="sidebar-empty">No conversations yet.</div>
          ) : (
            histories.slice(0, 6).map((chat) => (
              <button
                key={chat.id}
                className={`history-item ${
                  activeChatId === chat.id ? "active" : ""
                }`}
                onClick={() => loadChat(chat.id)}
              >
                <MessageSquareText size={15} />
                <span>
                  <strong>{chat.title || "New conversation"}</strong>
                  <small>{chat.tenant}</small>
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="sidebar-divider" />
      <UserSwitcher activeUserId={activeUserId} onSelect={setActiveUserId} />

      <div className="sidebar-footer">
        <Sparkles size={14} />
        <span>Three-layer secure RAG</span>
      </div>
    </aside>
  );
}

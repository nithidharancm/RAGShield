import { UsersRound } from "lucide-react";
import { DEMO_USERS } from "../config/users";

export default function UserSwitcher({ activeUserId, onSelect }) {
  return (
    <div className="user-switcher">
      <div className="sidebar-section-heading">
        <span>Demo identities</span>
        <UsersRound size={14} />
      </div>

      <div className="user-list">
        {DEMO_USERS.map((user) => (
          <button
            key={user.id}
            className={`user-option ${
              activeUserId === user.id ? "active" : ""
            }`}
            onClick={() => onSelect(user.id)}
          >
            <span className={`user-avatar ${user.accent}`}>{user.short}</span>
            <span className="user-option-copy">
              <strong>{user.label}</strong>
              <small>{user.id}</small>
            </span>
            <span className="tenant-chip">{user.tenant}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

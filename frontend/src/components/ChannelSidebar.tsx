import { useState } from "react";
import { useAuth } from "../store/auth";
import { useChat } from "../store/chat";
import { HexAvatar } from "./HexAvatar";

export function ChannelSidebar() {
  const { user, logout } = useAuth();
  const { servers, activeServerId, channels, activeChannelId, selectChannel, createChannel } = useChat();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");

  const server = servers.find((s) => s.id === activeServerId);
  const serverChannels = activeServerId ? channels[activeServerId] ?? [] : [];

  const copyInvite = () => {
    if (server) navigator.clipboard.writeText(server.invite_code);
  };

  const submitChannel = async () => {
    if (!activeServerId || !name.trim()) return;
    await createChannel(activeServerId, name.trim());
    setName("");
    setAdding(false);
  };

  if (!server) {
    return <div className="sidebar" />;
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>{server.name}</h2>
        <button className="sidebar-invite" onClick={copyInvite} title="Copy invite code">
          {server.invite_code}
        </button>
      </div>

      <div className="channel-list">
        <div className="channel-list-label">Text channels</div>
        {serverChannels.map((c) => (
          <div
            key={c.id}
            className={`channel-row ${c.id === activeChannelId ? "active" : ""}`}
            onClick={() => selectChannel(c.id)}
          >
            <span className="glyph">#</span>
            {c.name}
          </div>
        ))}

        {adding ? (
          <div className="channel-add-form">
            <input
              autoFocus
              value={name}
              placeholder="new-channel"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitChannel();
                if (e.key === "Escape") setAdding(false);
              }}
              onBlur={() => !name && setAdding(false)}
            />
          </div>
        ) : (
          <div className="channel-row" onClick={() => setAdding(true)}>
            <span className="glyph">+</span>
            Add channel
          </div>
        )}
      </div>

      {user && (
        <div className="sidebar-user">
          <HexAvatar name={user.display_name} hue={user.avatar_hue} size={32} status="online" />
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user.display_name}</div>
            <div className="sidebar-user-status">{user.custom_status ?? "online"}</div>
          </div>
          <button className="sidebar-logout" onClick={logout} title="Log out">
            Exit
          </button>
        </div>
      )}
    </div>
  );
}

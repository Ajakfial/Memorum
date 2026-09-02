import { useState } from "react";
import { useChat } from "../store/chat";
import { hueToBackground } from "../lib/color";
import { ServerModal } from "./ServerModal";

export function ServerRail() {
  const { servers, activeServerId, selectServer } = useChat();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="rail">
      <div className="hex rail-brand" title="Memorum">
        M
      </div>
      <div className="rail-divider" />

      {servers.map((server) => (
        <div
          key={server.id}
          className={`hex rail-server ${server.id === activeServerId ? "active" : ""}`}
          style={server.id === activeServerId ? { background: hueToBackground(server.icon_hue) } : undefined}
          title={server.name}
          onClick={() => selectServer(server.id)}
        >
          <span className="indicator" />
          {server.name
            .split(/\s+/)
            .map((w) => w[0])
            .slice(0, 2)
            .join("")
            .toUpperCase()}
        </div>
      ))}

      <div className="hex rail-server add" title="Add a hive" onClick={() => setModalOpen(true)}>
        +
      </div>

      {modalOpen && <ServerModal onClose={() => setModalOpen(false)} />}
    </div>
  );
}

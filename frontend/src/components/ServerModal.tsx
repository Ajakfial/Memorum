import { useState } from "react";
import { useChat } from "../store/chat";

export function ServerModal({ onClose }: { onClose: () => void }) {
  const { createServer, joinServer } = useChat();
  const [tab, setTab] = useState<"create" | "join">("create");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (tab === "create") {
        if (!name.trim()) return;
        await createServer(name.trim());
      } else {
        if (!code.trim()) return;
        await joinServer(code.trim());
      }
      onClose();
    } catch (err: any) {
      setError(err.message ?? "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">Start or join a hive</h3>
        <p className="modal-subtitle">A hive is Memorum's take on a server — your own space with channels.</p>

        <div className="modal-tabs">
          <div className={`modal-tab ${tab === "create" ? "active" : ""}`} onClick={() => setTab("create")}>
            Create a hive
          </div>
          <div className={`modal-tab ${tab === "join" ? "active" : ""}`} onClick={() => setTab("join")}>
            Join with a code
          </div>
        </div>

        {error && <div className="auth-error">{error}</div>}

        {tab === "create" ? (
          <div className="auth-field">
            <label>Hive name</label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Late Night Coders"
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
        ) : (
          <div className="auth-field">
            <label>Invite code</label>
            <input
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="a1b2c3d4"
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
        )}

        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose}>
            Cancel
          </button>
          <button className="modal-confirm" disabled={busy} onClick={submit}>
            {tab === "create" ? "Create hive" : "Join hive"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useChat } from "../store/chat";
import { HexAvatar } from "./HexAvatar";

export function MemberList() {
  const { activeServerId, members, onlineUserIds } = useChat();
  const list = activeServerId ? members[activeServerId] ?? [] : [];

  const online = list.filter((m) => onlineUserIds.has(m.user.id));
  const offline = list.filter((m) => !onlineUserIds.has(m.user.id));

  const renderRow = (m: (typeof list)[number], isOnline: boolean) => (
    <div className={`member-row ${isOnline ? "" : "offline"}`} key={m.user.id}>
      <HexAvatar name={m.user.display_name} hue={m.user.avatar_hue} size={32} status={isOnline ? "online" : "offline"} />
      <div>
        <div className="member-name">{m.nickname ?? m.user.display_name}</div>
        {m.role !== "member" && <div className="member-role">{m.role}</div>}
      </div>
    </div>
  );

  return (
    <div className="member-list">
      {online.length > 0 && (
        <>
          <div className="member-list-label">Online — {online.length}</div>
          {online.map((m) => renderRow(m, true))}
        </>
      )}
      {offline.length > 0 && (
        <>
          <div className="member-list-label" style={{ marginTop: 14 }}>
            Offline — {offline.length}
          </div>
          {offline.map((m) => renderRow(m, false))}
        </>
      )}
    </div>
  );
}

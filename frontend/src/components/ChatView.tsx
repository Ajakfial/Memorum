import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../store/auth";
import { useChat } from "../store/chat";
import { HexAvatar } from "./HexAvatar";
import { socketRef } from "../hooks/useSocket";
import type { Message } from "../lib/api";

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// Group consecutive messages from the same author within a 5-minute window,
// the way Discord collapses avatars/usernames for a fast-moving conversation.
function groupMessages(messages: Message[]) {
  const groups: { author: Message["author"]; time: string; items: Message[] }[] = [];
  for (const m of messages) {
    const last = groups[groups.length - 1];
    const closeInTime =
      last && new Date(m.created_at).getTime() - new Date(last.items[last.items.length - 1].created_at).getTime() < 5 * 60 * 1000;
    if (last && last.author.id === m.author.id && closeInTime) {
      last.items.push(m);
    } else {
      groups.push({ author: m.author, time: m.created_at, items: [m] });
    }
  }
  return groups;
}

export function ChatView() {
  const { user } = useAuth();
  const { activeChannelId, activeServerId, channels, messages, sendMessage, typingByChannel, members } = useChat();
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const channel = useMemo(() => {
    if (!activeServerId || !activeChannelId) return null;
    return (channels[activeServerId] ?? []).find((c) => c.id === activeChannelId) ?? null;
  }, [channels, activeServerId, activeChannelId]);

  const channelMessages = activeChannelId ? messages[activeChannelId] ?? [] : [];
  const grouped = useMemo(() => groupMessages(channelMessages), [channelMessages]);

  const typingUserIds = activeChannelId ? [...(typingByChannel[activeChannelId] ?? [])] : [];
  const typingNames = typingUserIds
    .map((id) => members[activeServerId ?? ""]?.find((m) => m.user.id === id)?.user.display_name)
    .filter(Boolean);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [channelMessages.length, activeChannelId]);

  if (!channel || !activeChannelId) {
    return (
      <div className="chat-main">
        <div className="empty-channel" style={{ margin: "auto" }}>
          <div className="hex">M</div>
          <p>Pick a channel, or start a new hive from the rail on the left.</p>
        </div>
      </div>
    );
  }

  const submit = async () => {
    const content = draft.trim();
    if (!content || !activeChannelId) return;
    setDraft("");
    await sendMessage(activeChannelId, content);
  };

  return (
    <div className="chat-main">
      <div className="chat-header">
        <span className="glyph">#</span>
        <h3>{channel.name}</h3>
        {channel.topic && <span className="topic">{channel.topic}</span>}
      </div>

      <div className="message-scroll" ref={scrollRef}>
        {grouped.length === 0 && (
          <div className="empty-channel">
            <div className="hex">#</div>
            <p>This is the beginning of #{channel.name}. Say something.</p>
          </div>
        )}
        {grouped.map((g, i) => (
          <div className="message-group" key={i}>
            <HexAvatar name={g.author.display_name} hue={g.author.avatar_hue} size={38} />
            <div className="message-body">
              <div className="message-meta">
                <span className="message-author">{g.author.display_name}</span>
                <span className="message-time">{formatTime(g.time)}</span>
              </div>
              {g.items.map((m) => (
                <div className="message-text" key={m.id}>
                  {m.content}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="typing-row">
        {typingNames.length > 0 &&
          `${typingNames.join(", ")} ${typingNames.length === 1 ? "is" : "are"} typing…`}
      </div>

      <div className="composer">
        <div className="composer-box">
          <textarea
            rows={1}
            value={draft}
            placeholder={`Message #${channel.name}`}
            onChange={(e) => {
              setDraft(e.target.value);
              if (activeChannelId) socketRef.current?.sendTyping(activeChannelId);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <button className="composer-send" disabled={!draft.trim()} onClick={submit}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

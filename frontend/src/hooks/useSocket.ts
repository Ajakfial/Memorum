import { useEffect, useRef } from "react";
import { useAuth } from "../store/auth";
import { useChat } from "../store/chat";
import { MemorumSocket } from "../lib/ws";

// Exposed so lightweight UI bits (like the composer's typing ping) can reach
// the live socket without threading it through props or re-subscribing.
export const socketRef: { current: MemorumSocket | null } = { current: null };

export function useSocket() {
  const token = useAuth((s) => s.token);
  const { onMessageCreate, onPresence, onTyping, activeChannelId } = useChat();
  const activeChannelRef = useRef(activeChannelId);
  activeChannelRef.current = activeChannelId;

  useEffect(() => {
    if (!token) {
      socketRef.current?.close();
      socketRef.current = null;
      return;
    }

    const socket = new MemorumSocket(token);
    socketRef.current = socket;
    socket.connect();

    const unsubscribe = socket.on((event) => {
      switch (event.type) {
        case "message_create":
          onMessageCreate(event.channel_id, event.message);
          break;
        case "presence":
          onPresence(event.user_id, event.status);
          break;
        case "typing":
          onTyping(event.channel_id, event.user_id);
          break;
      }
    });

    return () => {
      unsubscribe();
      socket.close();
      socketRef.current = null;
    };
  }, [token]);

  // Keep the gateway's per-channel subscription in sync with what's on screen.
  useEffect(() => {
    if (activeChannelId) socketRef.current?.subscribeChannel(activeChannelId);
  }, [activeChannelId]);
}

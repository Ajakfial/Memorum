import { create } from "zustand";
import { api, Channel, Message, Server, ServerMember } from "../lib/api";

interface ChatState {
  servers: Server[];
  activeServerId: string | null;
  channels: Record<string, Channel[]>; // serverId -> channels
  activeChannelId: string | null;
  messages: Record<string, Message[]>; // channelId -> messages
  members: Record<string, ServerMember[]>; // serverId -> members
  typingByChannel: Record<string, Set<string>>; // channelId -> user_ids currently typing
  onlineUserIds: Set<string>;

  loadServers: () => Promise<void>;
  selectServer: (serverId: string) => Promise<void>;
  selectChannel: (channelId: string) => Promise<void>;
  createServer: (name: string) => Promise<Server>;
  joinServer: (code: string) => Promise<Server>;
  createChannel: (serverId: string, name: string, topic?: string) => Promise<void>;
  sendMessage: (channelId: string, content: string) => Promise<void>;

  // Realtime event handlers, wired up by the WS hook.
  onMessageCreate: (channelId: string, message: Message) => void;
  onPresence: (userId: string, status: string) => void;
  onTyping: (channelId: string, userId: string) => void;
}

export const useChat = create<ChatState>((set, get) => ({
  servers: [],
  activeServerId: null,
  channels: {},
  activeChannelId: null,
  messages: {},
  members: {},
  typingByChannel: {},
  onlineUserIds: new Set(),

  loadServers: async () => {
    const servers = await api.listServers();
    set({ servers });
    if (servers.length && !get().activeServerId) {
      await get().selectServer(servers[0].id);
    }
  },

  selectServer: async (serverId) => {
    set({ activeServerId: serverId });
    const [channels, members] = await Promise.all([api.listChannels(serverId), api.listMembers(serverId)]);
    set((s) => ({
      channels: { ...s.channels, [serverId]: channels },
      members: { ...s.members, [serverId]: members },
    }));
    if (channels.length) {
      await get().selectChannel(channels[0].id);
    }
  },

  selectChannel: async (channelId) => {
    set({ activeChannelId: channelId });
    if (!get().messages[channelId]) {
      const messages = await api.listMessages(channelId);
      set((s) => ({ messages: { ...s.messages, [channelId]: messages } }));
    }
  },

  createServer: async (name) => {
    const server = await api.createServer(name);
    set((s) => ({ servers: [...s.servers, server] }));
    await get().selectServer(server.id);
    return server;
  },

  joinServer: async (code) => {
    const server = await api.joinServer(code);
    set((s) => (s.servers.find((sv) => sv.id === server.id) ? s : { servers: [...s.servers, server] }));
    await get().selectServer(server.id);
    return server;
  },

  createChannel: async (serverId, name, topic) => {
    const channel = await api.createChannel(serverId, name, topic);
    set((s) => ({ channels: { ...s.channels, [serverId]: [...(s.channels[serverId] ?? []), channel] } }));
  },

  sendMessage: async (channelId, content) => {
    // Optimistic UI relies on the broadcast echo (message_create) coming
    // straight back over the socket, so we don't duplicate insertion here.
    await api.sendMessage(channelId, content);
  },

  onMessageCreate: (channelId, message) => {
    set((s) => {
      const existing = s.messages[channelId] ?? [];
      if (existing.some((m) => m.id === message.id)) return {};
      return { messages: { ...s.messages, [channelId]: [...existing, message] } };
    });
  },

  onPresence: (userId, status) => {
    set((s) => {
      const online = new Set(s.onlineUserIds);
      if (status === "online") online.add(userId);
      else online.delete(userId);
      return { onlineUserIds: online };
    });
  },

  onTyping: (channelId, userId) => {
    set((s) => {
      const current = new Set(s.typingByChannel[channelId] ?? []);
      current.add(userId);
      return { typingByChannel: { ...s.typingByChannel, [channelId]: current } };
    });
    setTimeout(() => {
      set((s) => {
        const current = new Set(s.typingByChannel[channelId] ?? []);
        current.delete(userId);
        return { typingByChannel: { ...s.typingByChannel, [channelId]: current } };
      });
    }, 3000);
  },
}));

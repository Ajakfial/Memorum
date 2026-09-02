const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let authToken: string | null = null;
export function setAuthToken(token: string | null) {
  authToken = token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* no JSON body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---- Types mirroring the backend's Pydantic schemas ----

export interface User {
  id: string;
  username: string;
  display_name: string;
  avatar_hue: number;
  status: "online" | "idle" | "dnd" | "offline";
  custom_status: string | null;
}

export interface Server {
  id: string;
  name: string;
  icon_hue: number;
  owner_id: string;
  invite_code: string;
  created_at: string;
}

export interface Channel {
  id: string;
  server_id: string | null;
  kind: "text" | "dm" | "group_dm";
  name: string | null;
  topic: string | null;
  position: number;
}

export interface Message {
  id: string;
  channel_id: string;
  content: string;
  created_at: string;
  edited_at: string | null;
  author: User;
}

export interface ServerMember {
  user: User;
  nickname: string | null;
  role: "owner" | "admin" | "member";
  joined_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const api = {
  register: (username: string, email: string, password: string) =>
    request<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),

  login: (identifier: string, password: string) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    }),

  me: () => request<User>("/api/auth/me"),

  listServers: () => request<Server[]>("/api/servers"),
  createServer: (name: string) =>
    request<Server>("/api/servers", { method: "POST", body: JSON.stringify({ name }) }),
  joinServer: (invite_code: string) =>
    request<Server>("/api/servers/join", { method: "POST", body: JSON.stringify({ invite_code }) }),
  listMembers: (serverId: string) => request<ServerMember[]>(`/api/servers/${serverId}/members`),

  listChannels: (serverId: string) => request<Channel[]>(`/api/servers/${serverId}/channels`),
  createChannel: (serverId: string, name: string, topic?: string) =>
    request<Channel>(`/api/servers/${serverId}/channels`, {
      method: "POST",
      body: JSON.stringify({ name, topic }),
    }),

  listMessages: (channelId: string, before?: string) =>
    request<Message[]>(`/api/channels/${channelId}/messages${before ? `?before=${before}` : ""}`),
  sendMessage: (channelId: string, content: string) =>
    request<Message>(`/api/channels/${channelId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  listFriends: () => request<{ id: string; status: string; user: User }[]>("/api/friends"),
  sendFriendRequest: (username: string) =>
    request(`/api/friends/requests`, { method: "POST", body: JSON.stringify({ username }) }),
  openDM: (username: string) => request<Channel & { participants: User[] }>(`/api/dms/${username}`, { method: "POST" }),
};

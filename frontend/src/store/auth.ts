import { create } from "zustand";
import { api, setAuthToken, User } from "../lib/api";

const STORAGE_KEY = "memorum.token";

interface AuthState {
  user: User | null;
  token: string | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  login: (identifier: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  restoreSession: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: null,
  status: "idle",
  error: null,

  login: async (identifier, password) => {
    set({ status: "loading", error: null });
    try {
      const res = await api.login(identifier, password);
      localStorage.setItem(STORAGE_KEY, res.access_token);
      setAuthToken(res.access_token);
      set({ user: res.user, token: res.access_token, status: "ready" });
    } catch (err: any) {
      set({ status: "error", error: err.message ?? "Login failed" });
      throw err;
    }
  },

  register: async (username, email, password) => {
    set({ status: "loading", error: null });
    try {
      const res = await api.register(username, email, password);
      localStorage.setItem(STORAGE_KEY, res.access_token);
      setAuthToken(res.access_token);
      set({ user: res.user, token: res.access_token, status: "ready" });
    } catch (err: any) {
      set({ status: "error", error: err.message ?? "Registration failed" });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEY);
    setAuthToken(null);
    set({ user: null, token: null, status: "idle" });
  },

  restoreSession: async () => {
    const token = localStorage.getItem(STORAGE_KEY);
    if (!token) {
      set({ status: "idle" });
      return;
    }
    setAuthToken(token);
    set({ status: "loading" });
    try {
      const user = await api.me();
      set({ user, token, status: "ready" });
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      setAuthToken(null);
      set({ user: null, token: null, status: "idle" });
    }
  },
}));

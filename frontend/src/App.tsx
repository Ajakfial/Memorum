import { useEffect } from "react";
import { useAuth } from "./store/auth";
import { useChat } from "./store/chat";
import { useSocket } from "./hooks/useSocket";
import { AuthScreen } from "./components/AuthScreen";
import { ServerRail } from "./components/ServerRail";
import { ChannelSidebar } from "./components/ChannelSidebar";
import { ChatView } from "./components/ChatView";
import { MemberList } from "./components/MemberList";

export default function App() {
  const { user, status, restoreSession } = useAuth();
  const loadServers = useChat((s) => s.loadServers);

  useEffect(() => {
    restoreSession();
  }, []);

  useEffect(() => {
    if (user) loadServers();
  }, [user]);

  useSocket();

  if (status === "loading" && !user) {
    return <div className="auth-screen" />;
  }

  if (!user) {
    return <AuthScreen />;
  }

  return (
    <div className="app-shell">
      <ServerRail />
      <ChannelSidebar />
      <ChatView />
      <MemberList />
    </div>
  );
}

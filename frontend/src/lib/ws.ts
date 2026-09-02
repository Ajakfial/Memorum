type EventHandler = (event: any) => void;

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export class MemorumSocket {
  private socket: WebSocket | null = null;
  private handlers = new Set<EventHandler>();
  private token: string;
  private reconnectDelay = 1000;
  private closedByUser = false;

  constructor(token: string) {
    this.token = token;
  }

  connect() {
    this.closedByUser = false;
    this.socket = new WebSocket(`${WS_URL}/ws?token=${encodeURIComponent(this.token)}`);

    this.socket.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        this.handlers.forEach((h) => h(data));
      } catch {
        /* ignore malformed frames */
      }
    };

    this.socket.onclose = () => {
      if (this.closedByUser) return;
      // Simple capped exponential backoff — keeps the client light and
      // avoids hammering the server if it's briefly unreachable.
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 15000);
    };

    this.socket.onopen = () => {
      this.reconnectDelay = 1000;
    };
  }

  send(event: object) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(event));
    }
  }

  subscribeChannel(channelId: string) {
    this.send({ type: "subscribe_channel", channel_id: channelId });
  }

  unsubscribeChannel(channelId: string) {
    this.send({ type: "unsubscribe_channel", channel_id: channelId });
  }

  sendTyping(channelId: string) {
    this.send({ type: "typing", channel_id: channelId });
  }

  on(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  close() {
    this.closedByUser = true;
    this.socket?.close();
  }
}

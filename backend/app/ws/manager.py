"""
Connection manager for Memorum's realtime gateway.

Kept intentionally simple and in-memory: one backend process holds a map of
user_id -> set of live WebSocket connections (a user can have multiple
devices/tabs open), plus a map of channel_id -> set of user_ids currently
subscribed to that channel's live updates.

This is the right amount of complexity for a single-process deployment.
If Memorum is ever scaled horizontally across multiple backend instances,
swap the in-memory dicts for a Redis pub/sub layer (channel events published
to a shared bus, each instance subscribes and fans out to its own local
sockets) — the public methods below (`broadcast_to_channel`,
`broadcast_presence`) are the seam where that change would happen.
"""
import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.user_sockets: dict[str, set[WebSocket]] = defaultdict(set)
        self.channel_subscribers: dict[str, set[str]] = defaultdict(set)  # channel_id -> user_ids

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.user_sockets[user_id].add(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        self.user_sockets[user_id].discard(ws)
        if not self.user_sockets[user_id]:
            del self.user_sockets[user_id]
        for subs in self.channel_subscribers.values():
            subs.discard(user_id)

    def subscribe(self, user_id: str, channel_id: str) -> None:
        self.channel_subscribers[channel_id].add(user_id)

    def unsubscribe(self, user_id: str, channel_id: str) -> None:
        self.channel_subscribers[channel_id].discard(user_id)

    async def send_to_user(self, user_id: str, event: dict) -> None:
        payload = json.dumps(event)
        for ws in list(self.user_sockets.get(user_id, [])):
            try:
                await ws.send_text(payload)
            except Exception:
                self.user_sockets[user_id].discard(ws)

    async def broadcast_to_channel(self, channel_id: str, event: dict, exclude_user: str | None = None) -> None:
        for user_id in list(self.channel_subscribers.get(channel_id, [])):
            if user_id == exclude_user:
                continue
            await self.send_to_user(user_id, event)

    async def broadcast_to_users(self, user_ids: list[str], event: dict) -> None:
        for uid in user_ids:
            await self.send_to_user(uid, event)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.user_sockets and len(self.user_sockets[user_id]) > 0


manager = ConnectionManager()

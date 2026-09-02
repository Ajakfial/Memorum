import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_user_from_token
from app.models.enums import PresenceStatus
from app.models.models import ServerMember
from app.ws.manager import manager

router = APIRouter()


async def _user_channel_ids(user_id: str, db) -> list[str]:
    """All channel ids a user is allowed to receive live events for:
    every text channel in every server they belong to, plus their DMs
    (DM subscription happens on demand when the client opens that DM)."""
    from app.models.models import Channel

    result = await db.execute(
        select(Channel.id)
        .join(ServerMember, ServerMember.server_id == Channel.server_id)
        .where(ServerMember.user_id == user_id)
    )
    return [str(r) for r in result.scalars().all()]


@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket, token: str):
    async with AsyncSessionLocal() as db:
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4401)
            return

        user_id = str(user.id)
        await manager.connect(user_id, websocket)

        # Auto-subscribe to every channel in every server the user belongs to.
        channel_ids = await _user_channel_ids(user_id, db)
        for cid in channel_ids:
            manager.subscribe(user_id, cid)

        was_offline = not manager.is_online(user_id)
        user.status = PresenceStatus.online.value
        await db.commit()

        # Tell everyone sharing a server with this user that they're online.
        for cid in channel_ids:
            await manager.broadcast_to_channel(
                cid, {"type": "presence", "user_id": user_id, "status": "online"}, exclude_user=user_id
            )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")

            if event_type == "subscribe_channel":
                cid = event.get("channel_id")
                if cid:
                    manager.subscribe(user_id, cid)

            elif event_type == "unsubscribe_channel":
                cid = event.get("channel_id")
                if cid:
                    manager.unsubscribe(user_id, cid)

            elif event_type == "typing":
                cid = event.get("channel_id")
                if cid:
                    await manager.broadcast_to_channel(
                        cid,
                        {"type": "typing", "channel_id": cid, "user_id": user_id},
                        exclude_user=user_id,
                    )

            elif event_type == "presence_update":
                # e.g. { "type": "presence_update", "status": "idle" }
                new_status = event.get("status")
                if new_status in {s.value for s in PresenceStatus}:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(ServerMember).where(ServerMember.user_id == user_id))
                        from app.models.models import User as UserModel

                        u = await db.get(UserModel, user_id)
                        if u:
                            u.status = new_status
                            await db.commit()
                    cids = await _own_channel_ids(user_id)
                    for cid in cids:
                        await manager.broadcast_to_channel(
                            cid, {"type": "presence", "user_id": user_id, "status": new_status}, exclude_user=user_id
                        )

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
        if not manager.is_online(user_id):
            async with AsyncSessionLocal() as db:
                from app.models.models import User as UserModel

                u = await db.get(UserModel, user_id)
                if u:
                    u.status = PresenceStatus.offline.value
                    await db.commit()
            cids = await _own_channel_ids(user_id)
            for cid in cids:
                await manager.broadcast_to_channel(
                    cid, {"type": "presence", "user_id": user_id, "status": "offline"}, exclude_user=user_id
                )


async def _own_channel_ids(user_id: str) -> list[str]:
    async with AsyncSessionLocal() as db:
        return await _user_channel_ids(user_id, db)

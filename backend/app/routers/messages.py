import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_channel_access
from app.core.security import get_current_user
from app.models.models import Channel, Message, User
from app.schemas.schemas import MessageCreate, MessageOut
from app.ws.manager import manager

router = APIRouter(prefix="/api/channels/{channel_id}/messages", tags=["messages"])


@router.get("", response_model=list[MessageOut])
async def list_messages(
    channel_id: uuid.UUID,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    _channel: Channel = Depends(require_channel_access),
):
    query = select(Message).options(selectinload(Message.author)).where(Message.channel_id == channel_id)
    if before:
        query = query.where(Message.created_at < before)
    query = query.order_by(Message.created_at.desc()).limit(limit)

    result = await db.execute(query)
    messages = list(result.scalars().all())
    messages.reverse()  # return oldest -> newest for easy rendering
    return [MessageOut.model_validate(m) for m in messages]


@router.post("", response_model=MessageOut, status_code=201)
async def send_message(
    channel_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    channel: Channel = Depends(require_channel_access),
    user: User = Depends(get_current_user),
):
    message = Message(channel_id=channel_id, author_id=user.id, content=payload.content)
    db.add(message)
    await db.commit()
    await db.refresh(message, attribute_names=["author"])

    out = MessageOut.model_validate(message)

    if channel.server_id is not None:
        await manager.broadcast_to_channel(
            str(channel_id),
            {"type": "message_create", "channel_id": str(channel_id), "message": out.model_dump(mode="json")},
        )
    else:
        from app.models.models import DMParticipant

        result = await db.execute(select(DMParticipant.user_id).where(DMParticipant.channel_id == channel_id))
        participant_ids = [str(uid) for uid in result.scalars().all()]
        await manager.broadcast_to_users(
            participant_ids,
            {"type": "message_create", "channel_id": str(channel_id), "message": out.model_dump(mode="json")},
        )

    return out

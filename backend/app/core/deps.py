import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Channel, ServerMember, User


async def require_server_member(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServerMember:
    result = await db.execute(
        select(ServerMember).where(ServerMember.server_id == server_id, ServerMember.user_id == user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this server")
    return member


async def require_channel_access(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Channel:
    channel = await db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Channel not found")

    if channel.server_id is not None:
        result = await db.execute(
            select(ServerMember).where(
                ServerMember.server_id == channel.server_id, ServerMember.user_id == user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this server")
    else:
        from app.models.models import DMParticipant

        result = await db.execute(
            select(DMParticipant).where(
                DMParticipant.channel_id == channel_id, DMParticipant.user_id == user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a participant of this DM")

    return channel

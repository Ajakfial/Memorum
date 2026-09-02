import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_server_member
from app.models.enums import ChannelKind
from app.models.models import Channel, ServerMember
from app.schemas.schemas import ChannelCreate, ChannelOut

router = APIRouter(prefix="/api/servers/{server_id}/channels", tags=["channels"])


@router.get("", response_model=list[ChannelOut])
async def list_channels(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _member: ServerMember = Depends(require_server_member),
):
    result = await db.execute(
        select(Channel).where(Channel.server_id == server_id).order_by(Channel.position)
    )
    return [ChannelOut.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(
    server_id: uuid.UUID,
    payload: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    _member: ServerMember = Depends(require_server_member),
):
    count_result = await db.execute(select(Channel).where(Channel.server_id == server_id))
    position = len(count_result.scalars().all())

    channel = Channel(
        server_id=server_id,
        kind=ChannelKind.text.value,
        name=payload.name,
        topic=payload.topic,
        position=position,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return ChannelOut.model_validate(channel)

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_server_member
from app.core.security import get_current_user
from app.models.enums import ChannelKind, ServerRole
from app.models.models import Channel, Server, ServerMember, User
from app.schemas.schemas import ServerCreate, ServerJoin, ServerMemberOut, ServerOut

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _generate_invite_code() -> str:
    return secrets.token_urlsafe(6).replace("_", "").replace("-", "")[:8]


@router.post("", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    server = Server(
        name=payload.name,
        icon_hue=hash(payload.name) % 360,
        owner_id=user.id,
        invite_code=_generate_invite_code(),
    )
    db.add(server)
    await db.flush()

    db.add(ServerMember(server_id=server.id, user_id=user.id, role=ServerRole.owner.value))
    db.add(Channel(server_id=server.id, name="general", kind=ChannelKind.text.value, position=0))
    db.add(Channel(server_id=server.id, name="off-topic", kind=ChannelKind.text.value, position=1))

    await db.commit()
    await db.refresh(server)
    return ServerOut.model_validate(server)


@router.get("", response_model=list[ServerOut])
async def list_my_servers(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Server).join(ServerMember, ServerMember.server_id == Server.id).where(ServerMember.user_id == user.id)
    )
    return [ServerOut.model_validate(s) for s in result.scalars().all()]


@router.post("/join", response_model=ServerOut)
async def join_server(payload: ServerJoin, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Server).where(Server.invite_code == payload.invite_code))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite code")

    existing = await db.execute(
        select(ServerMember).where(ServerMember.server_id == server.id, ServerMember.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        return ServerOut.model_validate(server)

    db.add(ServerMember(server_id=server.id, user_id=user.id, role=ServerRole.member.value))
    await db.commit()
    return ServerOut.model_validate(server)


@router.get("/{server_id}/members", response_model=list[ServerMemberOut])
async def list_members(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _member: ServerMember = Depends(require_server_member),
):
    result = await db.execute(
        select(ServerMember).options(selectinload(ServerMember.user)).where(ServerMember.server_id == server_id)
    )
    return [ServerMemberOut.model_validate(m) for m in result.scalars().all()]


@router.delete("/{server_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_server(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    member: ServerMember = Depends(require_server_member),
):
    if member.role == ServerRole.owner.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Transfer ownership before leaving your own hive")
    await db.delete(member)
    await db.commit()

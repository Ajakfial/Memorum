import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.enums import ChannelKind
from app.models.models import Channel, DMParticipant, Friendship, User
from app.schemas.schemas import DMChannelOut, FriendOut, FriendRequestCreate, UserOut

router = APIRouter(prefix="/api", tags=["friends"])


@router.post("/friends/requests", response_model=FriendOut, status_code=201)
async def send_friend_request(
    payload: FriendRequestCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(select(User).where(User.username == payload.username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that username")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't friend yourself")

    existing = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == user.id, Friendship.friend_id == target.id),
                and_(Friendship.user_id == target.id, Friendship.friend_id == user.id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "A friend request already exists")

    fr = Friendship(user_id=user.id, friend_id=target.id, status="pending")
    db.add(fr)
    await db.commit()
    await db.refresh(fr)
    return FriendOut(id=fr.id, status=fr.status, user=UserOut.model_validate(target))


@router.post("/friends/requests/{friendship_id}/accept", response_model=FriendOut)
async def accept_friend_request(
    friendship_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    fr = await db.get(Friendship, friendship_id)
    if not fr or fr.friend_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Friend request not found")
    fr.status = "accepted"
    await db.commit()

    result = await db.execute(select(User).where(User.id == fr.user_id))
    requester = result.scalar_one()
    return FriendOut(id=fr.id, status=fr.status, user=UserOut.model_validate(requester))


@router.get("/friends", response_model=list[FriendOut])
async def list_friends(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Friendship).where(
            or_(Friendship.user_id == user.id, Friendship.friend_id == user.id),
            Friendship.status == "accepted",
        )
    )
    friendships = result.scalars().all()
    out = []
    for fr in friendships:
        other_id = fr.friend_id if fr.user_id == user.id else fr.user_id
        other = await db.get(User, other_id)
        out.append(FriendOut(id=fr.id, status=fr.status, user=UserOut.model_validate(other)))
    return out


@router.post("/dms/{username}", response_model=DMChannelOut)
async def open_dm(username: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user")

    # Look for an existing 1:1 DM channel between exactly these two users.
    existing = await db.execute(
        select(Channel)
        .join(DMParticipant, DMParticipant.channel_id == Channel.id)
        .where(Channel.kind == ChannelKind.dm.value, DMParticipant.user_id.in_([user.id, target.id]))
        .group_by(Channel.id)
    )
    for ch in existing.scalars().all():
        participants = await db.execute(select(DMParticipant.user_id).where(DMParticipant.channel_id == ch.id))
        ids = set(participants.scalars().all())
        if ids == {user.id, target.id}:
            ch_full = await db.get(Channel, ch.id, options=[selectinload(Channel.dm_participants)])
            users = [await db.get(User, p.user_id) for p in ch_full.dm_participants]
            return DMChannelOut(id=ch.id, kind=ch.kind, participants=[UserOut.model_validate(u) for u in users])

    channel = Channel(kind=ChannelKind.dm.value)
    db.add(channel)
    await db.flush()
    db.add(DMParticipant(channel_id=channel.id, user_id=user.id))
    db.add(DMParticipant(channel_id=channel.id, user_id=target.id))
    await db.commit()

    return DMChannelOut(
        id=channel.id, kind=channel.kind, participants=[UserOut.model_validate(user), UserOut.model_validate(target)]
    )

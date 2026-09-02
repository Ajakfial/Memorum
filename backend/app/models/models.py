import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ChannelKind, PresenceStatus, ServerRole


def uuid_pk():
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_hue: Mapped[int] = mapped_column(default=0)  # drives the generated hex-avatar color
    status: Mapped[str] = mapped_column(String(16), default=PresenceStatus.offline.value)
    custom_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    memberships: Mapped[list["ServerMember"]] = relationship(back_populates="user")


class Server(Base):
    """A 'hive' — Memorum's equivalent of a Discord guild/server."""

    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    icon_hue: Mapped[int] = mapped_column(default=0)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    channels: Mapped[list["Channel"]] = relationship(back_populates="server", cascade="all, delete-orphan")
    members: Mapped[list["ServerMember"]] = relationship(back_populates="server", cascade="all, delete-orphan")


class ServerMember(Base):
    __tablename__ = "server_members"
    __table_args__ = (UniqueConstraint("server_id", "user_id", name="uq_server_user"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default=ServerRole.member.value)
    joined_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    server: Mapped["Server"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = uuid_pk()
    server_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), default=ChannelKind.text.value)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)  # null for DMs
    topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    position: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    server: Mapped["Server | None"] = relationship(back_populates="channels")
    messages: Mapped[list["Message"]] = relationship(back_populates="channel", cascade="all, delete-orphan")
    dm_participants: Mapped[list["DMParticipant"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )


class DMParticipant(Base):
    """Links users to a direct-message or group-DM channel."""

    __tablename__ = "dm_participants"
    __table_args__ = (UniqueConstraint("channel_id", "user_id", name="uq_dm_channel_user"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    channel: Mapped["Channel"] = relationship(back_populates="dm_participants")
    user: Mapped["User"] = relationship()


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), index=True)
    edited_at: Mapped[datetime | None] = mapped_column(nullable=True)

    channel: Mapped["Channel"] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship()


class Friendship(Base):
    """Directional friend-request / friendship edge, mirrored both ways once accepted."""

    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("user_id", "friend_id", name="uq_friend_pair"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    friend_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | accepted | blocked
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

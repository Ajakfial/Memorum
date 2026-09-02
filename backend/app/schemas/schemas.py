import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=64)


class LoginRequest(BaseModel):
    identifier: str  # username or email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ---------- Users ----------

class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    avatar_hue: int
    status: str
    custom_status: str | None = None

    class Config:
        from_attributes = True


# ---------- Servers ----------

class ServerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64)


class ServerJoin(BaseModel):
    invite_code: str


class ServerOut(BaseModel):
    id: uuid.UUID
    name: str
    icon_hue: int
    owner_id: uuid.UUID
    invite_code: str
    created_at: datetime

    class Config:
        from_attributes = True


class ServerMemberOut(BaseModel):
    user: UserOut
    nickname: str | None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


# ---------- Channels ----------

class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    topic: str | None = Field(default=None, max_length=256)

    @field_validator("name")
    @classmethod
    def slugify(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "-")


class ChannelOut(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID | None
    kind: str
    name: str | None
    topic: str | None
    position: int

    class Config:
        from_attributes = True


# ---------- Messages ----------

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    content: str
    created_at: datetime
    edited_at: datetime | None
    author: UserOut

    class Config:
        from_attributes = True


# ---------- Friends / DMs ----------

class FriendRequestCreate(BaseModel):
    username: str


class FriendOut(BaseModel):
    id: uuid.UUID
    status: str
    user: UserOut

    class Config:
        from_attributes = True


class DMChannelOut(BaseModel):
    id: uuid.UUID
    kind: str
    participants: list[UserOut]

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()

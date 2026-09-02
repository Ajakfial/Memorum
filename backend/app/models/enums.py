import enum


class ServerRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class ChannelKind(str, enum.Enum):
    text = "text"          # a channel inside a server
    dm = "dm"               # one-to-one direct message
    group_dm = "group_dm"   # multi-person direct message


class PresenceStatus(str, enum.Enum):
    online = "online"
    idle = "idle"
    dnd = "dnd"
    offline = "offline"

import ipaddress
import re

from pydantic import BaseModel, field_validator

from app.models import UserRole, ConnectionMode

LABEL_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


# ---------------- Auth ----------------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = v.strip()
        if not LABEL_RE.match(v):
            raise ValueError("Username can only contain English letters, digits, hyphens, and underscores.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v


class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole

    class Config:
        from_attributes = True


# ---------------- Nodes ----------------
class NodeCreate(BaseModel):
    label: str
    public_ip: str | None = None
    subnet_cidr: str | None = ""

    @field_validator("label")
    @classmethod
    def validate_label(cls, v):
        v = v.strip()
        if not LABEL_RE.match(v):
            raise ValueError(
                "Label can only contain English letters, digits, hyphens, and underscores (no spaces)."
            )
        return v

    @field_validator("subnet_cidr")
    @classmethod
    def validate_subnet(cls, v):
        v = v.strip()
        if not v:
            return v
        try:
            # strict=False allows both single IPs (e.g. 192.168.1.50) and subnets
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            raise ValueError(
                f"'{v}' is not a valid IP or CIDR range (example: 192.168.10.0/24 or 192.168.10.5)."
            )
        return v


class NodeUpdate(NodeCreate):
    pass


class NodeOut(BaseModel):
    id: int
    label: str
    tunnel_ip: str
    subnet_cidr: str

    class Config:
        from_attributes = True


# ---------------- Connections ----------------
class ConnectionCreate(BaseModel):
    label: str
    source_node_id: int
    target_node_id: int
    mode: ConnectionMode = ConnectionMode.two_way
    enable_l7_proxy: bool = False

    @field_validator("label")
    @classmethod
    def validate_label(cls, v):
        v = v.strip()
        if not LABEL_RE.match(v):
            raise ValueError(
                "Label can only contain English letters, digits, hyphens, and underscores (no spaces)."
            )
        return v

    @field_validator("target_node_id")
    @classmethod
    def validate_not_self(cls, v, info):
        src = info.data.get("source_node_id")
        if src is not None and src == v:
            raise ValueError("Source and target node cannot be the same (prevents an infinite proxy loop).")
        return v


class ConnectionOut(BaseModel):
    id: int
    label: str
    source_node_id: int
    target_node_id: int
    port: int | None
    enable_l7_proxy: bool
    mode: ConnectionMode

    class Config:
        from_attributes = True

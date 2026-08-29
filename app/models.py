import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    viewer = "viewer"


class ConnectionMode(str, enum.Enum):
    one_way = "one_way"
    two_way = "two_way"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.viewer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Node(Base):
    """
    Important (fixes a phase-2 issue): each node has both a unique
    tunnel_ip (the L2TP tunnel endpoint, e.g. 10.10.10.2) and a unique
    subnet_cidr (the LAN behind the router, e.g. 192.168.10.0/24).
    These two concepts used to be conflated.
    """
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, unique=True, nullable=False, index=True)
    public_ip = Column(String, nullable=True)
    tunnel_ip = Column(String, unique=True, nullable=False)
    subnet_cidr = Column(String, nullable=False, default="")
    # PSK and PPP password are never stored raw - only encrypted (Fernet)
    # with a key from env, never hardcoded. They're only decrypted at the
    # moment the server rebuilds ipsec.secrets/chap-secrets on disk.
    encrypted_psk = Column(String, nullable=True)
    encrypted_ppp_password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    outgoing_connections = relationship(
        "Connection", foreign_keys="Connection.source_node_id",
        back_populates="source_node", cascade="all, delete-orphan"
    )
    incoming_connections = relationship(
        "Connection", foreign_keys="Connection.target_node_id",
        back_populates="target_node", cascade="all, delete-orphan"
    )


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = (
        UniqueConstraint("source_node_id", "target_node_id", name="uq_source_target"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, unique=True, nullable=False)
    source_node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    # port is only set when enable_l7_proxy is on (a dedicated Nginx
    # service-level proxy for one connection). The default is no longer
    # port-proxying - it's real subnet-to-subnet routing via iptables
    # FORWARD, per the design decision that "a pure Nginx reverse-proxy
    # fits host-to-host, not network-to-network".
    port = Column(Integer, unique=True, nullable=True)
    enable_l7_proxy = Column(Integer, nullable=False, default=0)  # 0/1 (SQLite bool)
    mode = Column(SAEnum(ConnectionMode), nullable=False, default=ConnectionMode.two_way)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_node = relationship("Node", foreign_keys=[source_node_id], back_populates="outgoing_connections")
    target_node = relationship("Node", foreign_keys=[target_node_id], back_populates="incoming_connections")

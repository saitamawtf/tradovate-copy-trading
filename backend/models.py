from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    broker: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(128))
    env: Mapped[str] = mapped_column(String(32), default="live")
    credentials_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    external_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CopyGroup(Base):
    __tablename__ = "copy_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    name: Mapped[str] = mapped_column(String(128))
    leader_account_id: Mapped[int] = mapped_column(ForeignKey("broker_accounts.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    mappings: Mapped[list["CopyMapping"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", lazy="selectin"
    )


class CopyMapping(Base):
    __tablename__ = "copy_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("copy_groups.id", ondelete="CASCADE"))
    follower_account_id: Mapped[int] = mapped_column(ForeignKey("broker_accounts.id"))
    size_mode: Mapped[str] = mapped_column(String(32), default="ratio")
    size_value: Mapped[float] = mapped_column(Float, default=1.0)
    reverse: Mapped[bool] = mapped_column(Boolean, default=False)

    group: Mapped[CopyGroup] = relationship(back_populates="mappings")


class TradeLog(Base):
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("copy_groups.id"), nullable=True)
    source_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("broker_accounts.id"), nullable=True
    )
    target_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("broker_accounts.id"), nullable=True
    )
    symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    side: Mapped[str | None] = mapped_column(String(16), nullable=True)
    qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str | None] = mapped_column(String, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

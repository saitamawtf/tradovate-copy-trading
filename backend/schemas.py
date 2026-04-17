from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Broker = Literal["tradovate", "projectx"]
SizeMode = Literal["fixed", "ratio", "equity_scaled"]


class TradovateCredentials(BaseModel):
    name: str
    password: str
    cid: int
    sec: str


class ProjectXCredentials(BaseModel):
    username: str
    api_key: str
    base_url: str | None = None


class AccountCreate(BaseModel):
    broker: Broker
    label: str
    env: Literal["live", "demo"] = "live"
    credentials: TradovateCredentials | ProjectXCredentials


class AccountOut(BaseModel):
    id: int
    broker: Broker
    label: str
    env: str
    external_account_id: str | None
    status: str
    last_seen_at: datetime | None


class AccountTestResult(BaseModel):
    ok: bool
    message: str
    accounts: list[dict] = Field(default_factory=list)


class MappingIn(BaseModel):
    follower_account_id: int
    size_mode: SizeMode = "ratio"
    size_value: float = 1.0
    reverse: bool = False


class MappingOut(MappingIn):
    id: int


class GroupCreate(BaseModel):
    name: str
    leader_account_id: int
    mappings: list[MappingIn]


class GroupOut(BaseModel):
    id: int
    name: str
    leader_account_id: int
    is_active: bool
    mappings: list[MappingOut]


class GroupStatus(BaseModel):
    id: int
    is_active: bool
    leader_connected: bool
    followers_connected: int
    followers_total: int
    last_events: list[dict] = Field(default_factory=list)

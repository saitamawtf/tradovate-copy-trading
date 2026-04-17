from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Side = Literal["Buy", "Sell"]
EventKind = Literal[
    "position_opened",
    "position_closed",
    "position_sized",
    "order_filled",
    "connected",
    "disconnected",
    "error",
]


@dataclass
class AccountInfo:
    id: str
    name: str
    balance: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    symbol: str
    root_symbol: str
    side: Side
    quantity: int
    account_id: str
    avg_price: float | None = None


@dataclass
class OrderRequest:
    account_id: str
    symbol: str  # broker-native symbol
    root_symbol: str  # normalized, e.g. "MNQ"
    side: Side
    quantity: int
    order_type: Literal["Market", "Limit", "Stop"] = "Market"
    price: float | None = None


@dataclass
class OrderResult:
    ok: bool
    order_id: str | None = None
    message: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class BrokerEvent:
    kind: EventKind
    account_id: str
    root_symbol: str | None = None
    native_symbol: str | None = None
    side: Side | None = None
    quantity: int = 0
    price: float | None = None
    ts: datetime = field(default_factory=datetime.utcnow)
    raw: dict[str, Any] = field(default_factory=dict)


class BrokerAdapter(ABC):
    """Common interface each broker must implement."""

    broker_name: str = "base"

    @abstractmethod
    async def authenticate(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def list_accounts(self) -> list[AccountInfo]: ...

    @abstractmethod
    async def get_positions(self, account_id: str) -> list[Position]: ...

    @abstractmethod
    async def place_order(self, req: OrderRequest) -> OrderResult: ...

    @abstractmethod
    async def close_position(self, account_id: str, root_symbol: str) -> OrderResult: ...

    @abstractmethod
    def stream_events(self, account_id: str) -> AsyncIterator[BrokerEvent]:
        """Async iterator of broker events for this account."""
        ...

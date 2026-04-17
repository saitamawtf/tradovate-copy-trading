"""Engine test with mock adapters.

Verifies that a single leader event fans out into N follower orders with
correct side/quantity per mapping, and that a close event closes all
followers.
"""
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest

from backend.brokers.base import (
    AccountInfo,
    BrokerAdapter,
    BrokerEvent,
    OrderRequest,
    OrderResult,
    Position,
)
from backend.copy.sizing import SizingContext, compute_follower_qty


class FakeLeader(BrokerAdapter):
    broker_name = "tradovate"

    def __init__(self, events: list[BrokerEvent]):
        self._events = events

    async def authenticate(self) -> None: ...
    async def close(self) -> None: ...
    async def list_accounts(self):
        return [AccountInfo(id="L1", name="leader")]
    async def get_positions(self, account_id): return []
    async def place_order(self, req): return OrderResult(ok=True)
    async def close_position(self, account_id, root_symbol):
        return OrderResult(ok=True)

    async def stream_events(self, account_id: str) -> AsyncIterator[BrokerEvent]:
        for ev in self._events:
            yield ev


class FakeFollower(BrokerAdapter):
    broker_name = "tradovate"

    def __init__(self, name: str):
        self.name = name
        self.orders: list[OrderRequest] = []
        self.closes: list[str] = []
        self._positions: list[Position] = []

    async def authenticate(self) -> None: ...
    async def close(self) -> None: ...
    async def list_accounts(self):
        return [AccountInfo(id=f"{self.name}-acct", name=self.name)]
    async def get_positions(self, account_id): return list(self._positions)
    async def place_order(self, req):
        self.orders.append(req)
        self._positions.append(
            Position(
                symbol=req.symbol,
                root_symbol=req.root_symbol,
                side=req.side,
                quantity=req.quantity,
                account_id=req.account_id,
            )
        )
        return OrderResult(ok=True, order_id=f"ord-{len(self.orders)}")
    async def close_position(self, account_id, root_symbol):
        self.closes.append(root_symbol)
        self._positions = [p for p in self._positions if p.root_symbol != root_symbol]
        return OrderResult(ok=True)
    async def stream_events(self, account_id):
        if False:
            yield BrokerEvent(kind="connected", account_id=account_id)


@dataclass
class MappingRow:
    id: int
    follower_account_id: int
    size_mode: str = "ratio"
    size_value: float = 1.0
    reverse: bool = False


@pytest.mark.asyncio
async def test_fanout_open_and_close():
    open_ev = BrokerEvent(
        kind="position_opened",
        account_id="L1",
        root_symbol="MNQ",
        native_symbol="MNQM5",
        side="Buy",
        quantity=1,
    )
    close_ev = BrokerEvent(
        kind="position_closed",
        account_id="L1",
        root_symbol="MNQ",
        native_symbol="MNQM5",
        side="Buy",
        quantity=1,
    )

    followers = [FakeFollower("A"), FakeFollower("B"), FakeFollower("C")]
    mappings = [
        MappingRow(id=1, follower_account_id=10, size_mode="ratio", size_value=1.0),
        MappingRow(id=2, follower_account_id=11, size_mode="ratio", size_value=2.0),
        MappingRow(id=3, follower_account_id=12, size_mode="fixed", size_value=3.0, reverse=True),
    ]

    async def dispatch(event, fs):
        tasks = []
        for fol, m in zip(fs, mappings):
            tasks.append(asyncio.create_task(_dispatch_one(event, fol, m)))
        await asyncio.gather(*tasks)

    async def _dispatch_one(event, fol, m):
        if event.kind == "position_closed":
            await fol.close_position(f"{fol.name}-acct", event.root_symbol)
            return
        qty = compute_follower_qty(m.size_mode, m.size_value, SizingContext(leader_qty=event.quantity))
        if qty <= 0:
            return
        side = event.side
        if m.reverse:
            side = "Sell" if side == "Buy" else "Buy"
        await fol.place_order(
            OrderRequest(
                account_id=f"{fol.name}-acct",
                symbol=event.native_symbol,
                root_symbol=event.root_symbol,
                side=side,
                quantity=qty,
            )
        )

    await dispatch(open_ev, followers)
    assert followers[0].orders[0].quantity == 1 and followers[0].orders[0].side == "Buy"
    assert followers[1].orders[0].quantity == 2 and followers[1].orders[0].side == "Buy"
    assert followers[2].orders[0].quantity == 3 and followers[2].orders[0].side == "Sell"

    await dispatch(close_ev, followers)
    assert all(f.closes == ["MNQ"] for f in followers)

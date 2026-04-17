"""Async ProjectX Gateway adapter (REST + SignalR User Hub).

ProjectX is the backend used by Topstep (TopstepX), TickTickTrader, and others.
Each prop firm exposes its own base URL; the default is TopstepX.
"""
import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx

from ..config import get_settings
from .base import (
    AccountInfo,
    BrokerAdapter,
    BrokerEvent,
    OrderRequest,
    OrderResult,
    Position,
)
from .symbols import extract_root

log = logging.getLogger(__name__)

# ProjectX order/side enums
ORDER_TYPE_MARKET = 2
ORDER_TYPE_LIMIT = 1
ORDER_TYPE_STOP = 4
SIDE_BUY = 0
SIDE_SELL = 1


class ProjectXAdapter(BrokerAdapter):
    broker_name = "projectx"

    def __init__(
        self,
        *,
        username: str,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        self._username = username
        self._api_key = api_key
        self._base = (base_url or get_settings().projectx_default_base).rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)
        self._token: str | None = None
        self._hub_task: asyncio.Task | None = None
        self._queue: asyncio.Queue[BrokerEvent] = asyncio.Queue(maxsize=1000)

    # ---------- lifecycle ----------
    async def close(self) -> None:
        if self._hub_task is not None:
            self._hub_task.cancel()
            try:
                await self._hub_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._hub_task = None
        await self._client.aclose()

    # ---------- REST ----------
    async def authenticate(self) -> None:
        url = f"{self._base}/api/Auth/loginKey"
        r = await self._client.post(
            url, json={"userName": self._username, "apiKey": self._api_key}
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success") or not data.get("token"):
            raise RuntimeError(f"ProjectX auth failed: {data}")
        self._token = data["token"]

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("not authenticated")
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def _post(self, path: str, body: dict) -> dict:
        r = await self._client.post(
            f"{self._base}{path}", json=body, headers=self._headers()
        )
        r.raise_for_status()
        return r.json()

    async def list_accounts(self) -> list[AccountInfo]:
        data = await self._post("/api/Account/search", {"onlyActiveAccounts": True})
        accts = data.get("accounts", [])
        return [
            AccountInfo(
                id=str(a["id"]),
                name=a.get("name", ""),
                balance=a.get("balance"),
                extra=a,
            )
            for a in accts
        ]

    async def get_positions(self, account_id: str) -> list[Position]:
        data = await self._post(
            "/api/Position/searchOpen", {"accountId": int(account_id)}
        )
        out: list[Position] = []
        for p in data.get("positions", []):
            qty = int(p.get("size", 0))
            if qty == 0:
                continue
            # ProjectX: type 1 = long, 2 = short (varies by firm; use positionType field)
            ptype = p.get("type") or p.get("positionType") or 1
            side = "Buy" if ptype == 1 else "Sell"
            sym = p.get("contractId", "")
            out.append(
                Position(
                    symbol=sym,
                    root_symbol=extract_root(sym),
                    side=side,
                    quantity=abs(qty),
                    account_id=str(account_id),
                    avg_price=p.get("averagePrice"),
                )
            )
        return out

    async def resolve_contract(self, root_symbol: str, *, live: bool = True) -> str | None:
        data = await self._post(
            "/api/Contract/search", {"searchText": root_symbol, "live": live}
        )
        contracts = data.get("contracts", [])
        # Front-month: smallest expiry in the future
        if not contracts:
            return None
        contracts.sort(key=lambda c: c.get("expirationDate") or "")
        return contracts[0].get("id")

    async def place_order(self, req: OrderRequest) -> OrderResult:
        contract_id = req.symbol or await self.resolve_contract(req.root_symbol)
        if not contract_id:
            return OrderResult(ok=False, message=f"contract not found for {req.root_symbol}")
        type_map = {
            "Market": ORDER_TYPE_MARKET,
            "Limit": ORDER_TYPE_LIMIT,
            "Stop": ORDER_TYPE_STOP,
        }
        payload = {
            "accountId": int(req.account_id),
            "contractId": contract_id,
            "type": type_map[req.order_type],
            "side": SIDE_BUY if req.side == "Buy" else SIDE_SELL,
            "size": int(req.quantity),
        }
        if req.order_type == "Limit" and req.price is not None:
            payload["limitPrice"] = req.price
        if req.order_type == "Stop" and req.price is not None:
            payload["stopPrice"] = req.price
        try:
            data = await self._post("/api/Order/place", payload)
            if data.get("success"):
                return OrderResult(ok=True, order_id=str(data.get("orderId")), raw=data)
            return OrderResult(ok=False, message=data.get("errorMessage"), raw=data)
        except Exception as e:  # noqa: BLE001
            return OrderResult(ok=False, message=str(e))

    async def close_position(self, account_id: str, root_symbol: str) -> OrderResult:
        positions = await self.get_positions(account_id)
        for p in positions:
            if p.root_symbol == root_symbol:
                opposite = "Sell" if p.side == "Buy" else "Buy"
                return await self.place_order(
                    OrderRequest(
                        account_id=account_id,
                        symbol=p.symbol,
                        root_symbol=root_symbol,
                        side=opposite,
                        quantity=p.quantity,
                    )
                )
        return OrderResult(ok=True, message="no open position")

    # ---------- SignalR User Hub ----------
    async def stream_events(self, account_id: str) -> AsyncIterator[BrokerEvent]:
        if self._hub_task is None or self._hub_task.done():
            self._hub_task = asyncio.create_task(self._hub_loop(account_id))
        while True:
            ev = await self._queue.get()
            yield ev

    async def _hub_loop(self, account_id: str) -> None:
        """Run the SignalR hub in a thread since signalrcore is sync."""
        backoff = 1.0
        loop = asyncio.get_running_loop()

        def enqueue(ev: BrokerEvent) -> None:
            loop.call_soon_threadsafe(self._queue.put_nowait, ev)

        while True:
            try:
                await loop.run_in_executor(None, self._run_hub_sync, account_id, enqueue)
                backoff = 1.0
            except Exception as e:  # noqa: BLE001
                log.warning("ProjectX hub error: %s (reconnecting in %.1fs)", e, backoff)
                enqueue(
                    BrokerEvent(
                        kind="disconnected", account_id=account_id, raw={"error": str(e)}
                    )
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def _run_hub_sync(self, account_id: str, enqueue) -> None:
        # Import here to avoid import cost at module load
        from signalrcore.hub_connection_builder import HubConnectionBuilder

        url = f"{self._base}/hubs/user?access_token={self._token}"
        hub = (
            HubConnectionBuilder()
            .with_url(
                url,
                options={
                    "access_token_factory": lambda: self._token,
                    "skip_negotiation": True,
                },
            )
            .with_automatic_reconnect(
                {"type": "raw", "keep_alive_interval": 15, "reconnect_interval": 5, "max_attempts": 5}
            )
            .build()
        )

        last_positions: dict[str, Position] = {}
        connected = threading_event()

        def on_open():
            enqueue(BrokerEvent(kind="connected", account_id=account_id))
            try:
                hub.send("SubscribeAccounts", [])
                hub.send("SubscribePositions", [int(account_id)])
                hub.send("SubscribeOrders", [int(account_id)])
                hub.send("SubscribeTrades", [int(account_id)])
            except Exception as e:  # noqa: BLE001
                log.warning("ProjectX subscribe error: %s", e)
            connected.set()

        def on_close():
            connected.clear()

        def on_position(args: list[Any]) -> None:
            for payload in args:
                ev = self._position_to_event(payload, account_id, last_positions)
                if ev:
                    enqueue(ev)

        def on_trade(args: list[Any]) -> None:
            for payload in args:
                sym = str(payload.get("contractId", ""))
                enqueue(
                    BrokerEvent(
                        kind="order_filled",
                        account_id=account_id,
                        root_symbol=extract_root(sym),
                        native_symbol=sym,
                        side="Buy" if payload.get("side") == SIDE_BUY else "Sell",
                        quantity=int(payload.get("size", 0)),
                        price=payload.get("price"),
                        raw=payload,
                    )
                )

        hub.on_open(on_open)
        hub.on_close(on_close)
        hub.on("GatewayUserPosition", on_position)
        hub.on("GatewayUserTrade", on_trade)

        hub.start()
        # Block this thread until connection drops
        connected.wait(timeout=30)
        while connected.is_set():
            connected.wait(timeout=5)
        try:
            hub.stop()
        except Exception:
            pass

    def _position_to_event(
        self,
        payload: dict[str, Any],
        account_id: str,
        last_positions: dict[str, Position],
    ) -> BrokerEvent | None:
        if str(payload.get("accountId")) != str(account_id):
            return None
        qty = int(payload.get("size", 0))
        sym = str(payload.get("contractId", ""))
        root = extract_root(sym)
        prev = last_positions.get(root)
        if qty == 0:
            if prev:
                last_positions.pop(root, None)
                return BrokerEvent(
                    kind="position_closed",
                    account_id=account_id,
                    root_symbol=root,
                    native_symbol=sym,
                    side=prev.side,
                    quantity=prev.quantity,
                    ts=datetime.utcnow(),
                    raw=payload,
                )
            return None
        ptype = payload.get("type") or payload.get("positionType") or 1
        side = "Buy" if ptype == 1 else "Sell"
        pos = Position(
            symbol=sym,
            root_symbol=root,
            side=side,
            quantity=abs(qty),
            account_id=str(account_id),
            avg_price=payload.get("averagePrice"),
        )
        if prev is None:
            last_positions[root] = pos
            return BrokerEvent(
                kind="position_opened",
                account_id=account_id,
                root_symbol=root,
                native_symbol=sym,
                side=side,
                quantity=abs(qty),
                price=payload.get("averagePrice"),
                raw=payload,
            )
        if prev.quantity != abs(qty) or prev.side != side:
            last_positions[root] = pos
            return BrokerEvent(
                kind="position_sized",
                account_id=account_id,
                root_symbol=root,
                native_symbol=sym,
                side=side,
                quantity=abs(qty),
                price=payload.get("averagePrice"),
                raw=payload,
            )
        return None


def threading_event():
    import threading

    return threading.Event()

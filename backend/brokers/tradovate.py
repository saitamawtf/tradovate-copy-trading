"""Async Tradovate adapter (REST + WebSocket)."""
import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx
import websockets

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


class TradovateAdapter(BrokerAdapter):
    broker_name = "tradovate"

    def __init__(
        self,
        *,
        name: str = "",
        password: str = "",
        cid: int = 0,
        sec: str = "",
        env: str = "live",
        access_token: str | None = None,
    ) -> None:
        s = get_settings()
        self._name = name
        self._password = password
        self._cid = cid
        self._sec = sec
        self._env = env
        # Pre-seeded OAuth token — skip password auth when present
        if access_token:
            self._token = access_token
        self._api_base = s.tradovate_api_base if env == "live" else s.tradovate_demo_api_base
        self._ws_url = s.tradovate_ws_url if env == "live" else s.tradovate_demo_ws_url
        self._app_id = s.app_id
        self._app_version = s.app_version
        self._client = httpx.AsyncClient(timeout=20.0)
        self._token: str | None = None
        self._user_id: int | None = None
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._msg_id = 0

    # ---------- lifecycle ----------
    async def close(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        await self._client.aclose()

    # ---------- REST ----------
    async def authenticate(self) -> None:
        if self._token:
            # Already have a token (OAuth path) — just resolve user_id
            await self._resolve_user_id()
            return
        url = f"{self._api_base}/auth/accesstokenrequest"
        payload = {
            "name": self._name,
            "password": self._password,
            "appId": self._app_id,
            "appVersion": self._app_version,
            "cid": self._cid,
            "sec": self._sec,
        }
        r = await self._client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        token = data.get("accessToken") or data.get("mdAccessToken")
        if not token:
            raise RuntimeError(f"Tradovate auth failed: {data}")
        self._token = token
        self._user_id = data.get("userId")

    async def _resolve_user_id(self) -> None:
        """Fetch user info to populate _user_id when using an OAuth token."""
        try:
            r = await self._client.get(
                f"{self._api_base}/user/self", headers=self._headers()
            )
            if r.status_code == 200:
                self._user_id = r.json().get("id")
        except Exception:
            pass

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("not authenticated")
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def list_accounts(self) -> list[AccountInfo]:
        r = await self._client.get(f"{self._api_base}/account/list", headers=self._headers())
        r.raise_for_status()
        raw = r.json() or []
        items = raw if isinstance(raw, list) else raw.get("json", [])
        return [
            AccountInfo(id=str(it["id"]), name=it.get("name", ""), extra=it) for it in items
        ]

    async def get_positions(self, account_id: str) -> list[Position]:
        url = f"{self._api_base}/position/list"
        r = await self._client.get(url, headers=self._headers())
        r.raise_for_status()
        raw = r.json() or []
        items = raw if isinstance(raw, list) else raw.get("json", [])
        out: list[Position] = []
        for it in items:
            if str(it.get("accountId")) != str(account_id):
                continue
            qty = int(it.get("netPos", 0))
            if qty == 0:
                continue
            side = "Buy" if qty > 0 else "Sell"
            sym = it.get("contractSymbol") or str(it.get("contractId", ""))
            out.append(
                Position(
                    symbol=sym,
                    root_symbol=extract_root(sym),
                    side=side,
                    quantity=abs(qty),
                    account_id=str(account_id),
                    avg_price=it.get("netPrice"),
                )
            )
        return out

    async def place_order(self, req: OrderRequest) -> OrderResult:
        url = f"{self._api_base}/order/placeorder"
        payload = {
            "accountId": int(req.account_id),
            "accountSpec": self._name,
            "symbol": req.symbol,
            "orderQty": int(req.quantity),
            "action": req.side,
            "orderType": req.order_type,
            "isAutomated": True,
        }
        if req.order_type == "Limit" and req.price is not None:
            payload["price"] = req.price
        if req.order_type == "Stop" and req.price is not None:
            payload["stopPrice"] = req.price
        try:
            r = await self._client.post(url, json=payload, headers=self._headers())
            data = r.json() if r.content else {}
            if r.status_code == 200 and data.get("orderId"):
                return OrderResult(ok=True, order_id=str(data["orderId"]), raw=data)
            return OrderResult(
                ok=False, message=data.get("failureText") or r.text, raw=data
            )
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

    # ---------- WebSocket streaming ----------
    async def _ws_connect(self) -> websockets.WebSocketClientProtocol:
        ws = await websockets.connect(self._ws_url, ping_interval=20)
        # Tradovate frame format: "<op>\n<id>\n<query>\n<body>"
        # First server frame is "o" (open). Then authorize.
        await ws.recv()  # discard "o"
        self._msg_id += 1
        await ws.send(f"authorize\n{self._msg_id}\n\n{self._token}")
        self._ws = ws
        return ws

    async def _ws_send(self, op: str, query: str = "", body: dict | None = None) -> None:
        assert self._ws is not None
        self._msg_id += 1
        payload = json.dumps(body) if body else ""
        await self._ws.send(f"{op}\n{self._msg_id}\n{query}\n{payload}")

    async def _ws_subscribe_user(self) -> None:
        # user/syncrequest pushes account/position/order events continuously
        if self._user_id is None:
            # fetch user
            r = await self._client.get(f"{self._api_base}/user/list", headers=self._headers())
            items = r.json() or []
            if isinstance(items, list) and items:
                self._user_id = items[0].get("id")
        if self._user_id:
            await self._ws_send("user/syncrequest", body={"users": [self._user_id]})

    async def stream_events(self, account_id: str) -> AsyncIterator[BrokerEvent]:
        backoff = 1.0
        last_positions: dict[str, Position] = {}
        while True:
            try:
                ws = await self._ws_connect()
                await self._ws_subscribe_user()
                yield BrokerEvent(kind="connected", account_id=account_id)
                backoff = 1.0

                async for raw in ws:
                    if not raw:
                        continue
                    kind = raw[0]
                    if kind in ("h", "o"):  # heartbeat / open
                        continue
                    if kind != "a":
                        continue
                    try:
                        frames: list[dict[str, Any]] = json.loads(raw[1:])
                    except json.JSONDecodeError:
                        continue
                    for frame in frames:
                        ev = self._frame_to_event(frame, account_id, last_positions)
                        if ev is not None:
                            yield ev
            except Exception as e:  # noqa: BLE001
                log.warning("Tradovate WS error: %s (reconnecting in %.1fs)", e, backoff)
                yield BrokerEvent(
                    kind="disconnected", account_id=account_id, raw={"error": str(e)}
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def _frame_to_event(
        self,
        frame: dict[str, Any],
        account_id: str,
        last_positions: dict[str, Position],
    ) -> BrokerEvent | None:
        entity = frame.get("e")
        data = frame.get("d") or {}
        if entity != "props":
            return None
        ent_type = data.get("entityType")
        ent = data.get("entity") or {}
        if ent_type == "position":
            if str(ent.get("accountId")) != str(account_id):
                return None
            qty = int(ent.get("netPos", 0))
            sym = ent.get("contractSymbol") or str(ent.get("contractId", ""))
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
                        raw=ent,
                    )
                return None
            side = "Buy" if qty > 0 else "Sell"
            pos = Position(
                symbol=sym,
                root_symbol=root,
                side=side,
                quantity=abs(qty),
                account_id=str(account_id),
                avg_price=ent.get("netPrice"),
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
                    price=ent.get("netPrice"),
                    raw=ent,
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
                    price=ent.get("netPrice"),
                    raw=ent,
                )
        elif ent_type == "fill":
            if str(ent.get("accountId")) != str(account_id):
                return None
            sym = ent.get("contractSymbol") or str(ent.get("contractId", ""))
            return BrokerEvent(
                kind="order_filled",
                account_id=account_id,
                root_symbol=extract_root(sym),
                native_symbol=sym,
                side="Buy" if ent.get("action") == "Buy" else "Sell",
                quantity=int(ent.get("qty", 0)),
                price=ent.get("price"),
                raw=ent,
            )
        return None

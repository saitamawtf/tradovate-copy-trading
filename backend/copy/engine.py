"""Copy trading engine.

Spins up one task per active CopyGroup. Each task:
  1. authenticates the leader adapter + all follower adapters,
  2. subscribes to the leader's event stream,
  3. for each ``position_opened``/``position_sized``/``position_closed`` event,
     dispatches the appropriate order to every follower concurrently.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..brokers.base import BrokerAdapter, BrokerEvent, OrderRequest
from ..brokers.factory import build_adapter
from ..models import BrokerAccount, CopyGroup, CopyMapping, TradeLog
from ..security import decrypt
from .sizing import SizingContext, compute_follower_qty

log = logging.getLogger(__name__)

EventCallback = Callable[[int, dict], Awaitable[None]]


@dataclass
class FollowerCtx:
    mapping_id: int
    account_id: int
    external_account_id: str
    adapter: BrokerAdapter
    size_mode: str
    size_value: float
    reverse: bool


@dataclass
class GroupRuntime:
    group_id: int
    task: asyncio.Task
    leader_connected: bool = False
    followers_connected: int = 0
    followers_total: int = 0
    last_events: list[dict] = field(default_factory=list)


class CopyEngine:
    def __init__(self, session_factory, event_callback: EventCallback | None = None) -> None:
        self._session_factory = session_factory
        self._on_event = event_callback
        self._groups: dict[int, GroupRuntime] = {}
        self._lock = asyncio.Lock()

    # ---------- public API ----------
    async def start_group(self, group_id: int) -> None:
        async with self._lock:
            if group_id in self._groups:
                raise RuntimeError(f"group {group_id} already running")
            task = asyncio.create_task(self._run_group(group_id))
            self._groups[group_id] = GroupRuntime(group_id=group_id, task=task)

    async def stop_group(self, group_id: int) -> None:
        async with self._lock:
            rt = self._groups.pop(group_id, None)
        if not rt:
            return
        rt.task.cancel()
        try:
            await rt.task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass

    def is_running(self, group_id: int) -> bool:
        return group_id in self._groups

    def status(self, group_id: int) -> dict[str, Any]:
        rt = self._groups.get(group_id)
        if not rt:
            return {
                "is_active": False,
                "leader_connected": False,
                "followers_connected": 0,
                "followers_total": 0,
                "last_events": [],
            }
        return {
            "is_active": True,
            "leader_connected": rt.leader_connected,
            "followers_connected": rt.followers_connected,
            "followers_total": rt.followers_total,
            "last_events": list(rt.last_events),
        }

    async def shutdown(self) -> None:
        for gid in list(self._groups.keys()):
            await self.stop_group(gid)

    # ---------- internals ----------
    async def _run_group(self, group_id: int) -> None:
        leader_adapter: BrokerAdapter | None = None
        followers: list[FollowerCtx] = []
        try:
            leader_adapter, leader_ext_id, followers = await self._bootstrap(group_id)
            rt = self._groups.get(group_id)
            if rt:
                rt.followers_total = len(followers)
            await self._emit(group_id, "engine", f"Group {group_id} started")

            async for event in leader_adapter.stream_events(leader_ext_id):
                self._record_event(group_id, event)
                if event.kind == "connected":
                    if rt:
                        rt.leader_connected = True
                    await self._emit(group_id, "connected", "leader connected")
                    continue
                if event.kind == "disconnected":
                    if rt:
                        rt.leader_connected = False
                    await self._emit(group_id, "disconnected", "leader disconnected")
                    continue
                if event.kind not in (
                    "position_opened",
                    "position_closed",
                    "position_sized",
                ):
                    continue
                await self._dispatch(group_id, event, followers)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("Group %s crashed: %s", group_id, e)
            await self._emit(group_id, "error", f"crashed: {e}")
        finally:
            if leader_adapter is not None:
                await leader_adapter.close()
            for f in followers:
                await f.adapter.close()

    async def _bootstrap(
        self, group_id: int
    ) -> tuple[BrokerAdapter, str, list[FollowerCtx]]:
        async with self._session_factory() as session:
            session: AsyncSession  # type: ignore[no-redef]
            group = (
                await session.execute(
                    select(CopyGroup).where(CopyGroup.id == group_id)
                )
            ).scalar_one()
            leader = (
                await session.execute(
                    select(BrokerAccount).where(
                        BrokerAccount.id == group.leader_account_id
                    )
                )
            ).scalar_one()
            mappings = (
                (
                    await session.execute(
                        select(CopyMapping).where(CopyMapping.group_id == group_id)
                    )
                )
                .scalars()
                .all()
            )

            follower_accounts: dict[int, BrokerAccount] = {}
            for m in mappings:
                acc = (
                    await session.execute(
                        select(BrokerAccount).where(
                            BrokerAccount.id == m.follower_account_id
                        )
                    )
                ).scalar_one()
                follower_accounts[m.id] = acc

        leader_adapter = build_adapter(
            leader.broker, leader.env, decrypt(leader.credentials_encrypted)
        )
        await leader_adapter.authenticate()
        leader_ext_id = leader.external_account_id or ""
        if not leader_ext_id:
            accts = await leader_adapter.list_accounts()
            if not accts:
                raise RuntimeError("leader has no accounts")
            leader_ext_id = accts[0].id

        followers: list[FollowerCtx] = []
        for m in mappings:
            acc = follower_accounts[m.id]
            adapter = build_adapter(acc.broker, acc.env, decrypt(acc.credentials_encrypted))
            await adapter.authenticate()
            ext_id = acc.external_account_id
            if not ext_id:
                accts = await adapter.list_accounts()
                ext_id = accts[0].id if accts else ""
            followers.append(
                FollowerCtx(
                    mapping_id=m.id,
                    account_id=acc.id,
                    external_account_id=ext_id,
                    adapter=adapter,
                    size_mode=m.size_mode,
                    size_value=m.size_value,
                    reverse=m.reverse,
                )
            )
        rt = self._groups.get(group_id)
        if rt:
            rt.followers_connected = len(followers)
        return leader_adapter, leader_ext_id, followers

    async def _dispatch(
        self, group_id: int, event: BrokerEvent, followers: list[FollowerCtx]
    ) -> None:
        tasks = [
            asyncio.create_task(self._dispatch_one(group_id, event, f))
            for f in followers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_one(
        self, group_id: int, event: BrokerEvent, f: FollowerCtx
    ) -> None:
        try:
            if event.kind == "position_closed":
                res = await f.adapter.close_position(
                    f.external_account_id, event.root_symbol or ""
                )
                await self._log_trade(
                    group_id, event, f, event_type="close", ok=res.ok, message=res.message
                )
                return

            qty = compute_follower_qty(
                f.size_mode,
                f.size_value,
                SizingContext(leader_qty=event.quantity),
            )
            if qty <= 0:
                return
            side = event.side or "Buy"
            if f.reverse:
                side = "Sell" if side == "Buy" else "Buy"

            if event.kind == "position_sized":
                # For MVP, align follower to new leader size by closing & reopening.
                await f.adapter.close_position(
                    f.external_account_id, event.root_symbol or ""
                )

            # Resolve native symbol for the follower. Tradovate followers can
            # reuse the leader's native symbol when both are Tradovate; cross-
            # broker (Tradovate leader -> ProjectX follower) we rely on the
            # root symbol and let the ProjectX adapter resolve the front month.
            native_symbol = event.native_symbol or ""
            if f.adapter.broker_name == "projectx" and (
                not native_symbol.startswith("CON.")
            ):
                contract_id = await f.adapter.resolve_contract(  # type: ignore[attr-defined]
                    event.root_symbol or ""
                )
                native_symbol = contract_id or native_symbol

            req = OrderRequest(
                account_id=f.external_account_id,
                symbol=native_symbol,
                root_symbol=event.root_symbol or "",
                side=side,
                quantity=qty,
            )
            res = await f.adapter.place_order(req)
            await self._log_trade(
                group_id,
                event,
                f,
                event_type="open" if event.kind == "position_opened" else "resize",
                ok=res.ok,
                message=res.message,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("dispatch failed for follower %s: %s", f.account_id, e)
            await self._log_trade(
                group_id, event, f, event_type="error", ok=False, message=str(e)
            )

    async def _log_trade(
        self,
        group_id: int,
        event: BrokerEvent,
        f: FollowerCtx,
        *,
        event_type: str,
        ok: bool,
        message: str | None,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                TradeLog(
                    group_id=group_id,
                    target_account_id=f.account_id,
                    symbol=event.root_symbol,
                    side=event.side,
                    qty=event.quantity,
                    event_type=f"{event_type}:{'ok' if ok else 'fail'}",
                    payload_json=json.dumps(
                        {"message": message, "event": event.kind}
                    ),
                )
            )
            await session.commit()
        await self._emit(
            group_id,
            event_type,
            f"{'OK' if ok else 'FAIL'} follower={f.account_id} {event.side} {event.quantity} {event.root_symbol}",
        )

    def _record_event(self, group_id: int, event: BrokerEvent) -> None:
        rt = self._groups.get(group_id)
        if not rt:
            return
        rt.last_events.insert(
            0,
            {
                "ts": event.ts.isoformat(),
                "kind": event.kind,
                "symbol": event.root_symbol,
                "side": event.side,
                "qty": event.quantity,
            },
        )
        rt.last_events[:] = rt.last_events[:50]

    async def _emit(self, group_id: int, kind: str, message: str) -> None:
        if self._on_event is None:
            return
        try:
            await self._on_event(
                group_id,
                {
                    "ts": datetime.utcnow().isoformat(),
                    "group_id": group_id,
                    "kind": kind,
                    "message": message,
                },
            )
        except Exception:  # noqa: BLE001
            log.debug("on_event callback failed", exc_info=True)

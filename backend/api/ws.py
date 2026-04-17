import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)

router = APIRouter()


class WSHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            targets = list(self._clients)
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                await self.disconnect(ws)


hub = WSHub()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            # Keep connection alive; we don't expect client messages.
            await ws.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(ws)
    except Exception:  # noqa: BLE001
        await hub.disconnect(ws)

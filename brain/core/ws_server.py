import asyncio
import json
import uuid
from dataclasses import dataclass, field
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from . import engine
from .logger import get_logger

log = get_logger("ws_server")

app = FastAPI(title="T Brain", docs_url=None, redoc_url=None)


@dataclass
class Client:
    id:        str
    websocket: WebSocket
    _lock:     asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _closed:   bool         = field(default=False, repr=False)

    async def send(self, payload: dict) -> None:
        if self._closed:
            return
        async with self._lock:
            if self._closed:
                return
            try:
                await self.websocket.send_text(json.dumps(payload))
            except Exception as e:
                # Only log if it's not an expected post-close race
                msg = str(e)
                if "websocket.close" not in msg and "already completed" not in msg:
                    log.warning(f"send failed for {self.id}: {e}")

    def close(self) -> None:
        self._closed = True


_clients: dict[str, Client] = {}


async def broadcast(payload: dict) -> None:
    """Send a message to all currently connected clients."""
    for client in list(_clients.values()):
        await client.send(payload)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client = Client(id=str(uuid.uuid4())[:8], websocket=ws)
    _clients[client.id] = client
    log.info(f"client connected: {client.id}  total={len(_clients)}")

    await client.send({"type": "brain_status", "online": True})

    try:
        while True:
            raw = await ws.receive_text()
            asyncio.create_task(engine.handle(client, raw))
    except WebSocketDisconnect:
        log.info(f"client disconnected: {client.id}")
    finally:
        client.close()
        _clients.pop(client.id, None)
        engine.on_disconnect(client.id)

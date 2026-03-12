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

    async def send(self, payload: dict) -> None:
        async with self._lock:
            try:
                await self.websocket.send_text(json.dumps(payload))
            except Exception as e:
                log.warning(f"send failed for {self.id}: {e}")


_clients: dict[str, Client] = {}


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
        _clients.pop(client.id, None)
        engine.on_disconnect(client.id)

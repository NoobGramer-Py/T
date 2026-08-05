"""
WebSocket Gateway Server for T AI Operating System.
Provides a real-time event streaming interface for Tauri GUI, CLI clients, and distributed host nodes.
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from brain.core.engine import kernel
from brain.api.router import api_router
from brain.logging.logger import get_logger

log = get_logger("core.ws_server")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """FastAPI Lifespan context manager booting system kernel."""
    log.info("Starting T OS WebSocket Gateway Server...")
    await kernel.boot()
    yield
    await kernel.shutdown()


app = FastAPI(title="T AI Operating System Gateway", lifespan=_lifespan, docs_url=None, redoc_url=None)
app.include_router(api_router)


@dataclass
class Client:
    id: str
    websocket: WebSocket
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _closed: bool = field(default=False, repr=False)

    async def send(self, payload: Dict[str, Any]) -> None:
        if self._closed:
            return
        async with self._lock:
            if self._closed:
                return
            try:
                await self.websocket.send_text(json.dumps(payload))
            except Exception as e:
                msg = str(e)
                if "websocket.close" not in msg and "already completed" not in msg:
                    log.warning(f"WebSocket send failed for client {self.id}: {e}")

    def close(self) -> None:
        self._closed = True


_clients: Dict[str, Client] = {}


async def broadcast(payload: Dict[str, Any]) -> None:
    """Send a message payload to all connected clients."""
    for client in list(_clients.values()):
        await client.send(payload)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client = Client(id=str(uuid.uuid4())[:8], websocket=ws)
    _clients[client.id] = client
    log.info(f"Client connected: {client.id} (Total active: {len(_clients)})")

    await client.send({
        "type": "system_status",
        "status": "operational",
        "node_id": "host-primary",
        "kernel_ready": kernel.initialized
    })

    try:
        while True:
            raw_text = await ws.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                data = {"type": "chat", "content": raw_text}

            msg_type = data.get("type", "chat")

            if msg_type in ["chat", "user_message"]:
                query = data.get("content", data.get("text", ""))
                user_auth = data.get("authorized", False)

                async def _stream_job(q: str, auth: bool):
                    async for evt in kernel.process_user_query(q, user_authorized=auth):
                        await client.send(evt)

                asyncio.create_task(_stream_job(query, user_auth))

            elif msg_type == "ping":
                await client.send({"type": "pong", "timestamp": asyncio.get_event_loop().time()})

    except WebSocketDisconnect:
        log.info(f"Client disconnected: {client.id}")
    finally:
        client.close()
        _clients.pop(client.id, None)

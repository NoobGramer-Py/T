import os
import asyncio
import uvicorn
from dotenv import load_dotenv
from core.ws_server import app
from core.logger    import get_logger

load_dotenv()
log = get_logger("main")

HOST = "127.0.0.1"
PORT = 7891


async def _startup() -> None:
    from proactive.engine import start as start_proactive
    await start_proactive()
    log.info("proactive engine running")


@app.on_event("startup")
async def on_startup() -> None:
    asyncio.create_task(_startup())


def main() -> None:
    log.info("T brain starting...")
    log.info(f"WebSocket server → ws://{HOST}:{PORT}/ws")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()

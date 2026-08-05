import uvicorn
from dotenv import load_dotenv
from brain.core.ws_server import app  # noqa: F401
from brain.logging.logger import get_logger
from brain.config.config import config

load_dotenv()
log = get_logger("main")


def main() -> None:
    log.info("T AI Operating System starting...")
    log.info(f"Gateway Server running → ws://{config.network.host}:{config.network.port}/ws")
    log.info(f"REST API available → http://{config.network.host}:{config.network.port}/api/v1/status")
    uvicorn.run(app, host=config.network.host, port=config.network.port, log_level="warning")


if __name__ == "__main__":
    main()

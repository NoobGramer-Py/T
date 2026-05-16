"""
Serial handler for T's hardware module.
Manages connections to Arduino and other serial devices.
Uses a simple newline-terminated protocol (see arduino_sketch.ino).

Protocol:
  T sends:  "DWRITE 13 HIGH\n"  →  Arduino replies: "OK 13 HIGH\n"
  T sends:  "DREAD 7\n"         →  Arduino replies:  "OK 7 LOW\n"
  T sends:  "AREAD A0\n"        →  Arduino replies:  "OK A0 512\n"
  T sends:  "DHT 2\n"           →  Arduino replies:  "OK 22.5 61.0\n"
  T sends:  "PING\n"            →  Arduino replies:  "PONG\n"
  T sends:  "PWM 9 128\n"       →  Arduino replies:  "OK 9 128\n"
"""

import asyncio
from core.logger import get_logger

log = get_logger("hardware.serial")

_READ_TIMEOUT  = 3.0   # seconds to wait for a response
_CONNECT_TIMEOUT = 5.0
_BAUD_RATES    = [9600, 115200, 57600, 38400]

# Active connections: device_id → serial.Serial instance
_connections: dict[str, object] = {}


def discover() -> list[dict]:
    """
    Scan all serial ports and return a list of {port, description, hwid}.
    Safe to call when pyserial is not installed — returns an error entry.
    """
    try:
        from serial.tools import list_ports  # type: ignore
        ports = []
        for p in list_ports.comports():
            ports.append({
                "port":        p.device,
                "description": p.description,
                "hwid":        p.hwid or "",
            })
        return ports or [{"port": "", "description": "No serial ports found", "hwid": ""}]
    except ImportError:
        return [{"port": "", "description": "pyserial not installed — run: pip install pyserial", "hwid": ""}]
    except Exception as e:
        return [{"port": "", "description": f"Discovery error: {e}", "hwid": ""}]


async def connect(device_id: str, port: str, baud: int = 0) -> str:
    """
    Open a serial connection to the device.
    If baud=0, auto-detect from _BAUD_RATES.
    Returns "OK: connected at {baud}" or an error string.
    """
    try:
        import serial  # type: ignore
    except ImportError:
        return "[ERROR] pyserial not installed. Run: pip install pyserial"

    if device_id in _connections:
        return f"OK: already connected to {port}"

    try:
        working_baud = baud if baud else await _auto_detect_baud(port)
        if not working_baud:
            return f"[ERROR] Could not establish connection on {port}. Check the port and device."

        conn = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: serial.Serial(port, working_baud, timeout=_READ_TIMEOUT),
        )
        _connections[device_id] = conn
        log.info(f"serial connected  device={device_id}  port={port}  baud={working_baud}")
        return f"OK: connected to {port} at {working_baud} baud"
    except Exception as e:
        return f"[ERROR] Cannot open {port}: {e}"


async def send_command(device_id: str, command: str, value: str = "") -> str:
    """
    Send one command line to the device and return the response.
    command: e.g. "DWRITE", value: e.g. "13 HIGH"
    Full line sent: "DWRITE 13 HIGH\n"
    """
    conn = _connections.get(device_id)
    if conn is None:
        return f"[ERROR] Device '{device_id}' not connected. Connect first."

    line = f"{command} {value}".strip() + "\n"
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _sync_send_recv(conn, line)
        )
        return response
    except Exception as e:
        return f"[ERROR] Serial communication failed: {e}"


def disconnect(device_id: str) -> str:
    """Close the serial connection for this device."""
    conn = _connections.pop(device_id, None)
    if conn is None:
        return f"Device '{device_id}' was not connected."
    try:
        conn.close()  # type: ignore
        log.info(f"serial disconnected  device={device_id}")
        return "OK: disconnected"
    except Exception as e:
        return f"[ERROR] {e}"


def is_connected(device_id: str) -> bool:
    return device_id in _connections


# ─── Internal ─────────────────────────────────────────────────────────────────

def _sync_send_recv(conn, line: str) -> str:
    """Blocking send + read. Runs in executor thread."""
    conn.write(line.encode("ascii"))
    conn.flush()
    response = conn.readline().decode("ascii", errors="replace").strip()
    return response or "[no response]"


async def _auto_detect_baud(port: str) -> int:
    """Try each baud rate, send PING, return first working baud or 0."""
    try:
        import serial  # type: ignore
    except ImportError:
        return 0

    for baud in _BAUD_RATES:
        try:
            conn = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda b=baud: serial.Serial(port, b, timeout=1.0),
            )
            try:
                resp = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _sync_send_recv(conn, "PING\n")
                )
                if "PONG" in resp.upper():
                    conn.close()
                    log.info(f"auto-baud detected  port={port}  baud={baud}")
                    return baud
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception:
            continue
    return 0

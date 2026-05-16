"""
Safety checks and temp file management for T's local access module.
All checks run before any elevated operation begins.
Results are warnings — Abdul is the authority on whether to proceed.
"""

import asyncio
import os
import glob
import secrets
import tempfile
from pathlib import Path
from core.logger import get_logger

log = get_logger("local_access.safety")

_TEMP_PREFIX = "T_lac_"


async def _ps(cmd: str, timeout: int = 10) -> str:
    """Run a PowerShell command, return output string."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-NonInteractive", "-Command", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        return out or stderr.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"[ERROR] {e}"


async def run_checks() -> list[dict]:
    """
    Run all pre-session safety checks.
    Returns a list of {check, status, message} dicts.
    status is "ok" | "warn" — never a hard block.
    """
    results = []
    results.append(await _check_firewall())
    results.append(await _check_av())
    results.append(await _check_connections())
    return results


async def _check_firewall() -> dict:
    out = await _ps(
        "Get-NetFirewallProfile | Select-Object Name, Enabled | "
        "Where-Object { $_.Enabled -eq $false } | "
        "Select-Object -ExpandProperty Name"
    )
    disabled = [l.strip() for l in out.splitlines() if l.strip()]
    if disabled:
        return {
            "check":   "Firewall",
            "status":  "warn",
            "message": f"Windows Firewall disabled on: {', '.join(disabled)}",
        }
    return {"check": "Firewall", "status": "ok", "message": "Windows Firewall active on all profiles"}


async def _check_av() -> dict:
    out = await _ps(
        "Get-MpComputerStatus | Select-Object -ExpandProperty AntivirusEnabled"
    )
    if "true" in out.lower():
        return {"check": "Antivirus", "status": "ok", "message": "Windows Defender is running"}
    return {
        "check":   "Antivirus",
        "status":  "warn",
        "message": "Windows Defender not running — AV may be disabled or replaced",
    }


async def _check_connections() -> dict:
    out = await _ps(
        "Get-NetTCPConnection -State Established | "
        "Where-Object { $_.RemoteAddress -notlike '127.*' -and $_.RemoteAddress -ne '::1' } | "
        "Select-Object RemoteAddress, RemotePort, OwningProcess | "
        "Select-Object -First 10 | Format-Table -AutoSize | Out-String"
    )
    lines = [l for l in out.splitlines() if l.strip()]
    count = max(0, len(lines) - 2)   # subtract header rows
    if count > 5:
        return {
            "check":   "Connections",
            "status":  "warn",
            "message": f"{count} active outbound connections — review before proceeding",
        }
    return {
        "check":   "Connections",
        "status":  "ok",
        "message": f"{count} active outbound connections",
    }


# ─── Temp file management ─────────────────────────────────────────────────────

def temp_path(suffix: str = ".bin") -> Path:
    """Return a unique temp file path with T's prefix. Does not create the file."""
    name = _TEMP_PREFIX + secrets.token_hex(8) + suffix
    return Path(tempfile.gettempdir()) / name


def cleanup_temp() -> int:
    """Delete all T_lac_* temp files. Returns count deleted."""
    pattern = os.path.join(tempfile.gettempdir(), f"{_TEMP_PREFIX}*")
    deleted = 0
    for path in glob.glob(pattern):
        try:
            os.remove(path)
            deleted += 1
        except Exception as e:
            log.warning(f"failed to delete temp file {path}: {e}")
    if deleted:
        log.info(f"cleaned up {deleted} temp file(s)")
    return deleted


# ─── Temp file encryption ─────────────────────────────────────────────────────

def make_session_key() -> bytes:
    """Generate a 32-byte random session key."""
    return secrets.token_bytes(32)


def encrypt_data(data: bytes, key: bytes) -> bytes:
    """
    Encrypt data with AES-256-GCM using the provided key.
    Returns nonce (12 bytes) + tag (16 bytes) + ciphertext.
    Falls back to XOR-based obfuscation if cryptography is not installed.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce      = secrets.token_bytes(12)
        ciphertext = AESGCM(key).encrypt(nonce, data, None)
        return nonce + ciphertext          # nonce(12) + tag(16) + ct
    except ImportError:
        log.warning("cryptography not installed — using XOR obfuscation for temp files")
        return _xor_obfuscate(data, key)


def decrypt_data(blob: bytes, key: bytes) -> bytes:
    """Decrypt data produced by encrypt_data."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce      = blob[:12]
        ciphertext = blob[12:]
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except ImportError:
        return _xor_obfuscate(blob, key)


def _xor_obfuscate(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

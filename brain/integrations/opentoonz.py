"""
OpenToonz Consciousness Bridge for T — Expert Edition.

Full creative control of OpenToonz: from single dots to running animations.
Uses win32api (proven to work) for all input simulation.
All blocking I/O runs in executor threads for async safety.
"""

import asyncio
import math
import subprocess
import time
import os
from typing import TYPE_CHECKING

import win32api
import win32con
import win32gui

from core.logger import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("integrations.opentoonz")

OPENTOONZ_EXE = r"C:\Program Files\OpenToonz\OpenToonz.exe"

# ── Virtual key codes ─────────────────────────────────────────────────────────

VK = {
    "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23,
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12,
    "insert": 0x2D, "slash": 0xBF,
    "f4": 0x73,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59, "z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
}


# ══════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL INPUT (blocking — always run via asyncio.to_thread)
# ══════════════════════════════════════════════════════════════════════════════

def _key_down(vk: int):
    win32api.keybd_event(vk, 0, 0, 0)

def _key_up(vk: int):
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

def _press(vk: int):
    _key_down(vk)
    time.sleep(0.05)
    _key_up(vk)
    time.sleep(0.05)

def _combo(*vks: int):
    for vk in vks:
        _key_down(vk)
        time.sleep(0.03)
    time.sleep(0.08)
    for vk in reversed(vks):
        _key_up(vk)
        time.sleep(0.03)

def _click(x: int, y: int):
    win32api.SetCursorPos((x, y))
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.05)

def _drag(x1: int, y1: int, x2: int, y2: int, steps: int = 40, duration: float = 1.0):
    win32api.SetCursorPos((x1, y1))
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    for i in range(1, steps + 1):
        t = i / steps
        win32api.SetCursorPos((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
        time.sleep(duration / steps)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.05)

def _draw_path(points: list[tuple[int, int]], speed: float = 0.02):
    """Draw along a list of (x,y) points as one continuous stroke."""
    if not points:
        return
    win32api.SetCursorPos(points[0])
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    for pt in points[1:]:
        win32api.SetCursorPos(pt)
        time.sleep(speed)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.05)


# ══════════════════════════════════════════════════════════════════════════════
#  SHAPE GENERATORS — compute (x,y) point lists for geometric shapes
# ══════════════════════════════════════════════════════════════════════════════

def _gen_circle(cx: int, cy: int, r: int, segs: int = 60) -> list[tuple[int, int]]:
    pts = []
    for i in range(segs + 1):
        a = 2 * math.pi * i / segs
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    return pts

def _gen_oval(cx: int, cy: int, rx: int, ry: int, segs: int = 60) -> list[tuple[int, int]]:
    pts = []
    for i in range(segs + 1):
        a = 2 * math.pi * i / segs
        pts.append((int(cx + rx * math.cos(a)), int(cy + ry * math.sin(a))))
    return pts

def _gen_rectangle(x: int, y: int, w: int, h: int) -> list[tuple[int, int]]:
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]

def _gen_triangle(cx: int, cy: int, size: int) -> list[tuple[int, int]]:
    h = int(size * math.sqrt(3) / 2)
    return [
        (cx, cy - h // 2),
        (cx - size // 2, cy + h // 2),
        (cx + size // 2, cy + h // 2),
        (cx, cy - h // 2),
    ]

def _gen_star(cx: int, cy: int, r_out: int, r_in: int = 0, points: int = 5) -> list[tuple[int, int]]:
    if r_in == 0:
        r_in = r_out // 2
    pts = []
    for i in range(points * 2 + 1):
        a = math.pi * i / points - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    return pts

def _gen_heart(cx: int, cy: int, size: int, segs: int = 80) -> list[tuple[int, int]]:
    pts = []
    for i in range(segs + 1):
        t = 2 * math.pi * i / segs
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        pts.append((int(cx + x * size / 17), int(cy + y * size / 17)))
    return pts

def _gen_spiral(cx: int, cy: int, max_r: int, turns: float = 3, segs: int = 120) -> list[tuple[int, int]]:
    pts = []
    for i in range(segs + 1):
        t = turns * 2 * math.pi * i / segs
        r = max_r * i / segs
        pts.append((int(cx + r * math.cos(t)), int(cy + r * math.sin(t))))
    return pts

def _gen_line(x1: int, y1: int, x2: int, y2: int, segs: int = 30) -> list[tuple[int, int]]:
    return [(int(x1 + (x2 - x1) * i / segs), int(y1 + (y2 - y1) * i / segs)) for i in range(segs + 1)]

def _gen_zigzag(x: int, y: int, width: int, amplitude: int, teeth: int = 6) -> list[tuple[int, int]]:
    pts = []
    for i in range(teeth * 2 + 1):
        px = x + width * i / (teeth * 2)
        py = y + (amplitude if i % 2 == 1 else -amplitude if i % 2 == 0 and i > 0 else 0)
        pts.append((int(px), int(py)))
    return pts

def _gen_wave(x: int, y: int, width: int, amplitude: int, cycles: float = 2, segs: int = 80) -> list[tuple[int, int]]:
    pts = []
    for i in range(segs + 1):
        t = i / segs
        pts.append((int(x + width * t), int(y + amplitude * math.sin(2 * math.pi * cycles * t))))
    return pts

def _gen_arrow(cx: int, cy: int, size: int, direction: str = "right") -> list[tuple[int, int]]:
    s = size // 2
    if direction == "right":
        return [(cx - s, cy), (cx + s, cy), (cx + s//2, cy - s//2), (cx + s, cy), (cx + s//2, cy + s//2)]
    elif direction == "up":
        return [(cx, cy + s), (cx, cy - s), (cx - s//2, cy - s//2 + s//2), (cx, cy - s), (cx + s//2, cy - s//2 + s//2)]
    return [(cx - s, cy), (cx + s, cy)]

def _gen_stickman(cx: int, cy: int, height: int) -> list[list[tuple[int, int]]]:
    """Returns multiple strokes that form a stickman."""
    h = height
    head_r = h // 8
    head_cy = cy - h // 2 + head_r
    body_top = head_cy + head_r
    body_bot = cy + h // 6
    leg_bot = cy + h // 2
    arm_y = body_top + (body_bot - body_top) // 3
    arm_span = h // 3

    return [
        _gen_circle(cx, head_cy, head_r, segs=30),                             # head
        _gen_line(cx, body_top, cx, body_bot),                                  # body
        _gen_line(cx, arm_y, cx - arm_span, arm_y - h // 10),                  # left arm
        _gen_line(cx, arm_y, cx + arm_span, arm_y - h // 10),                  # right arm
        _gen_line(cx, body_bot, cx - arm_span // 2, leg_bot),                  # left leg
        _gen_line(cx, body_bot, cx + arm_span // 2, leg_bot),                  # right leg
    ]

def _gen_smiley(cx: int, cy: int, radius: int) -> list[list[tuple[int, int]]]:
    """Returns multiple strokes: face circle, two eyes, smile arc."""
    r = radius
    strokes = [_gen_circle(cx, cy, r, segs=50)]  # face outline

    # Eyes
    eye_r = r // 7
    eye_y = cy - r // 4
    strokes.append(_gen_circle(cx - r // 3, eye_y, eye_r, segs=16))
    strokes.append(_gen_circle(cx + r // 3, eye_y, eye_r, segs=16))

    # Smile arc
    smile_pts = []
    for i in range(25):
        a = math.pi * 0.15 + math.pi * 0.7 * i / 24
        smile_pts.append((int(cx + r * 0.55 * math.cos(a)), int(cy + r * 0.55 * math.sin(a))))
    strokes.append(smile_pts)
    return strokes

def _gen_house(cx: int, cy: int, size: int) -> list[list[tuple[int, int]]]:
    """Returns strokes: walls (rect), roof (triangle), door (rect)."""
    s = size
    half = s // 2
    # Walls
    walls = _gen_rectangle(cx - half, cy - half // 2, s, half + half // 2)
    # Roof
    roof = [(cx - half - s // 8, cy - half // 2), (cx, cy - s), (cx + half + s // 8, cy - half // 2)]
    # Door
    dw = s // 5
    dh = s // 3
    door = _gen_rectangle(cx - dw // 2, cy + half, dw, -dh)
    return [walls, roof, door]

def _gen_sun(cx: int, cy: int, r: int) -> list[list[tuple[int, int]]]:
    """Circle + radiating rays."""
    strokes = [_gen_circle(cx, cy, r, segs=40)]
    for i in range(8):
        a = 2 * math.pi * i / 8
        x1 = int(cx + (r + 5) * math.cos(a))
        y1 = int(cy + (r + 5) * math.sin(a))
        x2 = int(cx + (r + r // 2) * math.cos(a))
        y2 = int(cy + (r + r // 2) * math.sin(a))
        strokes.append(_gen_line(x1, y1, x2, y2, segs=8))
    return strokes

def _gen_tree(cx: int, cy: int, height: int) -> list[list[tuple[int, int]]]:
    """Trunk (rect) + foliage (circle)."""
    tw = height // 8
    th = height // 3
    trunk = _gen_rectangle(cx - tw // 2, cy + height // 4, tw, th)
    foliage = _gen_circle(cx, cy - height // 8, height // 3, segs=40)
    return [trunk, foliage]


# ══════════════════════════════════════════════════════════════════════════════
#  ASYNC WRAPPERS
# ══════════════════════════════════════════════════════════════════════════════

async def _apress(vk: int):
    await asyncio.to_thread(_press, vk)

async def _acombo(*vks: int):
    await asyncio.to_thread(_combo, *vks)

async def _aclick(x: int, y: int):
    await asyncio.to_thread(_click, x, y)

async def _adrag(x1, y1, x2, y2, steps=40, duration=1.0):
    await asyncio.to_thread(_drag, x1, y1, x2, y2, steps, duration)

async def _adraw_path(pts, speed=0.02):
    await asyncio.to_thread(_draw_path, pts, speed)

async def _adraw_shape(pts_or_strokes, speed=0.015):
    """Draw single stroke (list of pts) or multi-stroke (list of lists)."""
    if not pts_or_strokes:
        return
    if isinstance(pts_or_strokes[0], list):
        for stroke in pts_or_strokes:
            await asyncio.to_thread(_draw_path, stroke, speed)
            await asyncio.sleep(0.15)
    else:
        await asyncio.to_thread(_draw_path, pts_or_strokes, speed)


# ══════════════════════════════════════════════════════════════════════════════
#  WINDOW MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _find_hwnd() -> int | None:
    result = []
    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if "opentoonz" in win32gui.GetWindowText(hwnd).lower():
                result.append(hwnd)
    win32gui.EnumWindows(_cb, None)
    return result[0] if result else None

def _focus(hwnd: int) -> bool:
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
        win32api.keybd_event(VK["alt"], 0, 0, 0)
        time.sleep(0.02)
        win32api.keybd_event(VK["alt"], 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception as e:
        log.warning(f"focus error: {e}")
        return False

async def _afocus(hwnd: int) -> bool:
    return await asyncio.to_thread(_focus, hwnd)

def _is_running() -> bool:
    import psutil
    for p in psutil.process_iter(["name"]):
        if p.info["name"] and "opentoonz" in p.info["name"].lower():
            return True
    return False

async def _launch() -> bool:
    if not os.path.exists(OPENTOONZ_EXE):
        return False
    subprocess.Popen([OPENTOONZ_EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        await asyncio.sleep(0.5)
        if _find_hwnd():
            return True
    return False

def _canvas_center(hwnd: int) -> tuple[int, int]:
    rect = win32gui.GetWindowRect(hwnd)
    return (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2

def _canvas_size(hwnd: int) -> tuple[int, int]:
    rect = win32gui.GetWindowRect(hwnd)
    return (rect[2] - rect[0]) // 2, (rect[3] - rect[1]) // 2


# ══════════════════════════════════════════════════════════════════════════════
#  CONSCIOUSNESS
# ══════════════════════════════════════════════════════════════════════════════

async def _think(client: "Client", msg_id: str, thought: str):
    log.info(f"[consciousness] {thought}")
    await client.send({"type": "chat_chunk", "id": msg_id, "chunk": f"💭 *{thought}*\n"})
    await asyncio.sleep(0.08)


# ══════════════════════════════════════════════════════════════════════════════
#  ENSURE FOCUSED
# ══════════════════════════════════════════════════════════════════════════════

async def _ensure_focused(client: "Client", msg_id: str) -> int | None:
    hwnd = _find_hwnd()
    if not hwnd:
        if not _is_running():
            await _think(client, msg_id, "Launching OpenToonz...")
            if not await _launch():
                return None
            await _think(client, msg_id, "Waiting for full initialization...")
            await asyncio.sleep(10.0)
        hwnd = _find_hwnd()
    if hwnd:
        await _think(client, msg_id, "Focusing OpenToonz...")
        await _afocus(hwnd)
        await asyncio.sleep(1.0)
    return hwnd


async def _activate_canvas(client: "Client", msg_id: str, hwnd: int):
    """Click the canvas center and select brush tool."""
    cx, cy = _canvas_center(hwnd)
    await _aclick(cx, cy)
    await asyncio.sleep(0.5)
    await _apress(VK["b"])  # brush tool
    await asyncio.sleep(0.5)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN EXECUTE
# ══════════════════════════════════════════════════════════════════════════════

ACTIONS = {
    # App control
    "open": "Launch/focus OpenToonz", "close": "Close OpenToonz",
    "new_scene": "New scene (Ctrl+N)", "save": "Save (Ctrl+S)", "save_as": "Save As",
    "undo": "Undo (Ctrl+Z)", "redo": "Redo (Ctrl+Y)",
    # Playback
    "play": "Play/pause", "stop": "Stop",
    "next_frame": "Next frame", "prev_frame": "Previous frame",
    "first_frame": "First frame", "last_frame": "Last frame",
    # Tools
    "brush": "Brush (B)", "eraser": "Eraser (E)", "fill": "Fill (F)", "select": "Selection (S)",
    "clear_canvas": "Clear entire canvas",
    # Drawing primitives
    "draw_dot": "Draw a single dot",
    "draw_stroke": "Draw a freehand stroke",
    "draw_line": "Draw a straight line",
    "draw_circle": "Draw a circle",
    "draw_oval": "Draw an oval/ellipse",
    "draw_rectangle": "Draw a rectangle",
    "draw_triangle": "Draw a triangle",
    "draw_star": "Draw a 5-pointed star",
    "draw_heart": "Draw a heart shape",
    "draw_spiral": "Draw a spiral",
    "draw_wave": "Draw a sine wave",
    "draw_zigzag": "Draw a zigzag line",
    "draw_arrow": "Draw an arrow",
    # Complex illustrations
    "draw_ball": "Draw a filled circle (ball)",
    "draw_stickman": "Draw a stick figure",
    "draw_smiley": "Draw a smiley face",
    "draw_house": "Draw a simple house",
    "draw_sun": "Draw a sun with rays",
    "draw_tree": "Draw a tree",
    "draw_scene": "Draw a full scene (house + sun + tree)",
    # Animation
    "animate_bounce": "Animate a bouncing ball (multi-frame)",
    "animate_walk": "Animate a walking stickman (multi-frame)",
    "animate_spin": "Animate a spinning star (multi-frame)",
    "animate_grow": "Animate a circle growing (multi-frame)",
    "animate_wave": "Animate a waving line (multi-frame)",
    # Frame/timeline
    "add_frame": "Insert blank frame", "duplicate_frame": "Duplicate frame",
    "onion_skin": "Toggle onion skin",
    "render": "Render scene",
    "goto_frame": "Go to specific frame number",
}


async def execute(client: "Client", msg_id: str,
                  action: str, params: dict | None = None) -> str:
    params = params or {}
    action = action.lower().strip().replace(" ", "_")

    # ── App control ────────────────────────────────────────────────────────
    if action == "open":
        hwnd = await _ensure_focused(client, msg_id)
        if hwnd:
            await _think(client, msg_id, "OpenToonz is live and ready.")
            return "OpenToonz is open and focused."
        return "[ERROR] Could not find OpenToonz."

    hwnd = await _ensure_focused(client, msg_id)
    if not hwnd:
        return "[ERROR] OpenToonz window not found."
    cx, cy = _canvas_center(hwnd)
    cw, ch = _canvas_size(hwnd)

    if action == "new_scene":
        await _think(client, msg_id, "Creating new scene (Ctrl+N)...")
        await _acombo(VK["ctrl"], VK["n"])
        await asyncio.sleep(3.0)
        await _think(client, msg_id, "Confirming with Enter...")
        await _apress(VK["enter"])
        await asyncio.sleep(3.0)
        return "New scene created."

    elif action == "save":
        await _think(client, msg_id, "Saving (Ctrl+S)...")
        await _acombo(VK["ctrl"], VK["s"])
        await asyncio.sleep(1.5)
        return "Scene saved."

    elif action == "save_as":
        await _think(client, msg_id, "Save As (Ctrl+Shift+S)...")
        await _acombo(VK["ctrl"], VK["shift"], VK["s"])
        await asyncio.sleep(2.0)
        return "Save As dialog opened."

    elif action == "close":
        await _think(client, msg_id, "Closing OpenToonz...")
        await _acombo(VK["alt"], VK["f4"])
        await asyncio.sleep(2.0)
        await _apress(VK["tab"])
        await asyncio.sleep(0.3)
        await _apress(VK["enter"])
        return "OpenToonz closed."

    elif action == "undo":
        await _think(client, msg_id, "Undoing (Ctrl+Z)...")
        await _acombo(VK["ctrl"], VK["z"])
        await asyncio.sleep(0.5)
        return "Undo executed."

    elif action == "redo":
        await _think(client, msg_id, "Redoing (Ctrl+Y)...")
        await _acombo(VK["ctrl"], VK["y"])
        await asyncio.sleep(0.5)
        return "Redo executed."

    # ── Playback ───────────────────────────────────────────────────────────
    elif action in ("play", "stop"):
        await _think(client, msg_id, "Toggling playback...")
        await _apress(VK["enter"])
        await asyncio.sleep(0.5)
        return "Playback toggled."

    elif action == "next_frame":
        n = int(params.get("count", 1))
        await _think(client, msg_id, f"Advancing {n} frame(s)...")
        for _ in range(n):
            await _apress(VK["right"])
            await asyncio.sleep(0.15)
        return f"Advanced {n} frame(s)."

    elif action == "prev_frame":
        n = int(params.get("count", 1))
        await _think(client, msg_id, f"Going back {n} frame(s)...")
        for _ in range(n):
            await _apress(VK["left"])
            await asyncio.sleep(0.15)
        return f"Went back {n} frame(s)."

    elif action == "first_frame":
        await _apress(VK["home"])
        return "Jumped to first frame."

    elif action == "last_frame":
        await _apress(VK["end"])
        return "Jumped to last frame."

    elif action == "goto_frame":
        n = int(params.get("frame", 1))
        await _think(client, msg_id, f"Going to frame {n}...")
        await _apress(VK["home"])
        await asyncio.sleep(0.3)
        for _ in range(n - 1):
            await _apress(VK["right"])
            await asyncio.sleep(0.08)
        return f"Moved to frame {n}."

    # ── Tools ──────────────────────────────────────────────────────────────
    elif action == "brush":
        await _think(client, msg_id, "Selecting Brush (B)...")
        await _apress(VK["b"])
        await asyncio.sleep(0.5)
        return "Brush tool selected."

    elif action == "eraser":
        await _think(client, msg_id, "Selecting Eraser (E)...")
        await _apress(VK["e"])
        await asyncio.sleep(0.5)
        return "Eraser selected."

    elif action == "fill":
        await _think(client, msg_id, "Selecting Fill (F)...")
        await _apress(VK["f"])
        await asyncio.sleep(0.5)
        return "Fill tool selected."

    elif action == "select":
        await _think(client, msg_id, "Selecting Selection tool (S)...")
        await _apress(VK["s"])
        await asyncio.sleep(0.5)
        return "Selection tool selected."

    elif action == "onion_skin":
        await _apress(VK["slash"])
        return "Onion skin toggled."

    elif action == "clear_canvas":
        await _think(client, msg_id, "Clearing canvas (Ctrl+A then Delete)...")
        await _acombo(VK["ctrl"], VK["a"])
        await asyncio.sleep(0.5)
        await _apress(VK["delete"])
        await asyncio.sleep(0.5)
        return "Canvas cleared."

    # ── Drawing primitives ─────────────────────────────────────────────────
    elif action == "draw_dot":
        await _think(client, msg_id, "Drawing a dot...")
        await _activate_canvas(client, msg_id, hwnd)
        await _aclick(cx, cy)
        return "Dot drawn."

    elif action == "draw_stroke":
        await _think(client, msg_id, "Drawing a freehand stroke...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adrag(cx - 100, cy + 20, cx + 100, cy - 20, steps=50, duration=1.2)
        return "Stroke drawn."

    elif action == "draw_line":
        await _think(client, msg_id, "Drawing a straight line...")
        await _activate_canvas(client, msg_id, hwnd)
        pts = _gen_line(cx - 120, cy, cx + 120, cy)
        await _adraw_path(pts, speed=0.02)
        return "Line drawn."

    elif action == "draw_circle":
        r = int(params.get("radius", min(cw, ch) // 4))
        await _think(client, msg_id, f"Drawing a circle (radius={r})...")
        await _activate_canvas(client, msg_id, hwnd)
        pts = _gen_circle(cx, cy, r)
        await _adraw_path(pts, speed=0.015)
        return f"Circle drawn (r={r})."

    elif action in ("draw_ball", "draw_filled_circle"):
        r = int(params.get("radius", min(cw, ch) // 4))
        await _think(client, msg_id, f"Drawing a ball (circle r={r})...")
        await _activate_canvas(client, msg_id, hwnd)
        pts = _gen_circle(cx, cy, r)
        await _adraw_path(pts, speed=0.015)
        await asyncio.sleep(0.3)
        # Fill inside
        await _think(client, msg_id, "Filling the ball with color...")
        await _apress(VK["f"])  # fill tool
        await asyncio.sleep(0.5)
        await _aclick(cx, cy)  # click inside to fill
        await asyncio.sleep(0.5)
        await _apress(VK["b"])  # back to brush
        return f"Ball drawn and filled (r={r})."

    elif action == "draw_oval":
        rx = int(params.get("rx", cw // 3))
        ry = int(params.get("ry", ch // 5))
        await _think(client, msg_id, f"Drawing an oval ({rx}x{ry})...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_oval(cx, cy, rx, ry))
        return "Oval drawn."

    elif action == "draw_rectangle":
        w = int(params.get("width", cw // 2))
        h = int(params.get("height", ch // 3))
        await _think(client, msg_id, f"Drawing a rectangle ({w}x{h})...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_rectangle(cx - w // 2, cy - h // 2, w, h))
        return "Rectangle drawn."

    elif action == "draw_triangle":
        s = int(params.get("size", min(cw, ch) // 2))
        await _think(client, msg_id, f"Drawing a triangle (size={s})...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_triangle(cx, cy, s))
        return "Triangle drawn."

    elif action == "draw_star":
        r = int(params.get("radius", min(cw, ch) // 4))
        n = int(params.get("points", 5))
        await _think(client, msg_id, f"Drawing a {n}-pointed star...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_star(cx, cy, r, points=n))
        return f"{n}-pointed star drawn."

    elif action == "draw_heart":
        s = int(params.get("size", min(cw, ch) // 4))
        await _think(client, msg_id, "Drawing a heart shape...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_heart(cx, cy, s))
        return "Heart drawn."

    elif action == "draw_spiral":
        r = int(params.get("radius", min(cw, ch) // 4))
        await _think(client, msg_id, "Drawing a spiral...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_spiral(cx, cy, r))
        return "Spiral drawn."

    elif action == "draw_wave":
        w = int(params.get("width", cw // 2))
        a = int(params.get("amplitude", ch // 6))
        await _think(client, msg_id, "Drawing a sine wave...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_wave(cx - w // 2, cy, w, a))
        return "Wave drawn."

    elif action == "draw_zigzag":
        w = int(params.get("width", cw // 2))
        a = int(params.get("amplitude", ch // 8))
        await _think(client, msg_id, "Drawing a zigzag...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_zigzag(cx - w // 2, cy, w, a))
        return "Zigzag drawn."

    elif action == "draw_arrow":
        s = int(params.get("size", min(cw, ch) // 3))
        await _think(client, msg_id, "Drawing an arrow...")
        await _activate_canvas(client, msg_id, hwnd)
        await _adraw_path(_gen_arrow(cx, cy, s))
        return "Arrow drawn."

    # ── Complex illustrations ──────────────────────────────────────────────
    elif action == "draw_stickman":
        h = int(params.get("height", ch // 2))
        await _think(client, msg_id, "Drawing a stickman...")
        await _activate_canvas(client, msg_id, hwnd)
        strokes = _gen_stickman(cx, cy, h)
        await _adraw_shape(strokes)
        return "Stickman drawn."

    elif action == "draw_smiley":
        r = int(params.get("radius", min(cw, ch) // 4))
        await _think(client, msg_id, "Drawing a smiley face...")
        await _activate_canvas(client, msg_id, hwnd)
        strokes = _gen_smiley(cx, cy, r)
        await _adraw_shape(strokes)
        return "Smiley face drawn."

    elif action == "draw_house":
        s = int(params.get("size", min(cw, ch) // 3))
        await _think(client, msg_id, "Drawing a house...")
        await _activate_canvas(client, msg_id, hwnd)
        strokes = _gen_house(cx, cy, s)
        await _adraw_shape(strokes)
        return "House drawn."

    elif action == "draw_sun":
        r = int(params.get("radius", min(cw, ch) // 6))
        scx = cx + cw // 3
        scy = cy - ch // 3
        await _think(client, msg_id, "Drawing a sun with rays...")
        await _activate_canvas(client, msg_id, hwnd)
        strokes = _gen_sun(scx, scy, r)
        await _adraw_shape(strokes)
        return "Sun drawn."

    elif action == "draw_tree":
        h = int(params.get("height", ch // 3))
        await _think(client, msg_id, "Drawing a tree...")
        await _activate_canvas(client, msg_id, hwnd)
        strokes = _gen_tree(cx, cy, h)
        await _adraw_shape(strokes)
        return "Tree drawn."

    elif action == "draw_scene":
        await _think(client, msg_id, "Drawing a full scene: house + sun + tree...")
        await _activate_canvas(client, msg_id, hwnd)
        s = min(cw, ch) // 3

        await _think(client, msg_id, "Drawing the house...")
        h_strokes = _gen_house(cx - cw // 4, cy + ch // 8, s)
        await _adraw_shape(h_strokes)
        await asyncio.sleep(0.3)

        await _think(client, msg_id, "Drawing the sun...")
        s_strokes = _gen_sun(cx + cw // 3, cy - ch // 3, s // 3)
        await _adraw_shape(s_strokes)
        await asyncio.sleep(0.3)

        await _think(client, msg_id, "Drawing a tree...")
        t_strokes = _gen_tree(cx + cw // 5, cy + ch // 8, s)
        await _adraw_shape(t_strokes)

        return "Full scene drawn (house + sun + tree)."

    # ── Animation sequences ────────────────────────────────────────────────
    elif action == "animate_bounce":
        frames = int(params.get("frames", 8))
        r = int(params.get("radius", min(cw, ch) // 8))
        await _think(client, msg_id, f"Creating bouncing ball animation ({frames} frames)...")
        await _activate_canvas(client, msg_id, hwnd)

        for i in range(frames):
            if i > 0:
                await _apress(VK["insert"])  # add frame
                await asyncio.sleep(0.4)
                await _apress(VK["right"])   # move to new frame
                await asyncio.sleep(0.3)

            # Parabolic bounce
            t = i / max(frames - 1, 1)
            bx = int(cx - cw // 3 + (cw * 2 // 3) * t)
            bounce = abs(math.sin(t * math.pi * 2))
            by = int(cy + ch // 4 - ch // 3 * bounce)

            await _think(client, msg_id, f"Frame {i + 1}/{frames}: ball at ({bx}, {by})...")
            pts = _gen_circle(bx, by, r, segs=30)
            await _adraw_path(pts, speed=0.01)
            await asyncio.sleep(0.2)

        await _think(client, msg_id, "Animation complete! Playing back...")
        await _apress(VK["home"])
        await asyncio.sleep(0.5)
        await _apress(VK["enter"])
        return f"Bouncing ball animation created ({frames} frames)."

    elif action == "animate_walk":
        frames = int(params.get("frames", 6))
        h = int(params.get("height", ch // 3))
        await _think(client, msg_id, f"Creating walking stickman animation ({frames} frames)...")
        await _activate_canvas(client, msg_id, hwnd)

        for i in range(frames):
            if i > 0:
                await _apress(VK["insert"])
                await asyncio.sleep(0.4)
                await _apress(VK["right"])
                await asyncio.sleep(0.3)

            t = i / max(frames - 1, 1)
            sx = int(cx - cw // 3 + (cw * 2 // 3) * t)
            await _think(client, msg_id, f"Frame {i + 1}/{frames}: stickman at x={sx}...")

            # Generate stickman with walking offset on legs
            strokes = _gen_stickman(sx, cy, h)
            # Modify leg angles slightly per frame
            leg_offset = int(h // 6 * math.sin(i * math.pi / 2))
            strokes[4] = _gen_line(sx, cy + h // 6, sx - h // 6 + leg_offset, cy + h // 2)
            strokes[5] = _gen_line(sx, cy + h // 6, sx + h // 6 - leg_offset, cy + h // 2)
            # Arms swing too
            arm_y = cy - h // 2 + h // 8 + (cy + h // 6 - cy + h // 2 - h // 8) // 3
            strokes[2] = _gen_line(sx, arm_y, sx - h // 3 - leg_offset, arm_y - h // 10)
            strokes[3] = _gen_line(sx, arm_y, sx + h // 3 + leg_offset, arm_y - h // 10)

            await _adraw_shape(strokes, speed=0.01)
            await asyncio.sleep(0.2)

        await _think(client, msg_id, "Walk cycle complete! Playing...")
        await _apress(VK["home"])
        await asyncio.sleep(0.5)
        await _apress(VK["enter"])
        return f"Walking stickman animation created ({frames} frames)."

    elif action == "animate_spin":
        frames = int(params.get("frames", 8))
        r = int(params.get("radius", min(cw, ch) // 5))
        await _think(client, msg_id, f"Creating spinning star animation ({frames} frames)...")
        await _activate_canvas(client, msg_id, hwnd)

        for i in range(frames):
            if i > 0:
                await _apress(VK["insert"])
                await asyncio.sleep(0.4)
                await _apress(VK["right"])
                await asyncio.sleep(0.3)

            angle_offset = 2 * math.pi * i / frames
            await _think(client, msg_id, f"Frame {i + 1}/{frames}: star rotated {int(360 * i / frames)}°...")
            pts = []
            for j in range(11):
                a = angle_offset + math.pi * j / 5 - math.pi / 2
                rad = r if j % 2 == 0 else r // 2
                pts.append((int(cx + rad * math.cos(a)), int(cy + rad * math.sin(a))))
            await _adraw_path(pts, speed=0.01)
            await asyncio.sleep(0.2)

        await _think(client, msg_id, "Spin animation complete! Playing...")
        await _apress(VK["home"])
        await asyncio.sleep(0.5)
        await _apress(VK["enter"])
        return f"Spinning star animation created ({frames} frames)."

    elif action == "animate_grow":
        frames = int(params.get("frames", 6))
        max_r = int(params.get("radius", min(cw, ch) // 4))
        await _think(client, msg_id, f"Creating growing circle animation ({frames} frames)...")
        await _activate_canvas(client, msg_id, hwnd)

        for i in range(frames):
            if i > 0:
                await _apress(VK["insert"])
                await asyncio.sleep(0.4)
                await _apress(VK["right"])
                await asyncio.sleep(0.3)

            r = int(max_r * (i + 1) / frames)
            await _think(client, msg_id, f"Frame {i + 1}/{frames}: circle r={r}...")
            pts = _gen_circle(cx, cy, max(r, 3), segs=30)
            await _adraw_path(pts, speed=0.01)
            await asyncio.sleep(0.2)

        await _think(client, msg_id, "Growth animation complete! Playing...")
        await _apress(VK["home"])
        await asyncio.sleep(0.5)
        await _apress(VK["enter"])
        return f"Growing circle animation created ({frames} frames)."

    elif action == "animate_wave":
        frames = int(params.get("frames", 8))
        w = cw // 2
        a = ch // 8
        await _think(client, msg_id, f"Creating wave animation ({frames} frames)...")
        await _activate_canvas(client, msg_id, hwnd)

        for i in range(frames):
            if i > 0:
                await _apress(VK["insert"])
                await asyncio.sleep(0.4)
                await _apress(VK["right"])
                await asyncio.sleep(0.3)

            phase = 2 * math.pi * i / frames
            await _think(client, msg_id, f"Frame {i + 1}/{frames}: wave phase {int(360 * i / frames)}°...")
            pts = []
            for j in range(61):
                t = j / 60
                pts.append((int(cx - w // 2 + w * t), int(cy + a * math.sin(2 * math.pi * 2 * t + phase))))
            await _adraw_path(pts, speed=0.01)
            await asyncio.sleep(0.2)

        await _think(client, msg_id, "Wave animation complete! Playing...")
        await _apress(VK["home"])
        await asyncio.sleep(0.5)
        await _apress(VK["enter"])
        return f"Wave animation created ({frames} frames)."

    # ── Frame management ───────────────────────────────────────────────────
    elif action == "add_frame":
        await _apress(VK["insert"])
        await asyncio.sleep(0.5)
        return "Blank frame inserted."

    elif action == "duplicate_frame":
        await _acombo(VK["ctrl"], VK["c"])
        await asyncio.sleep(0.3)
        await _apress(VK["right"])
        await asyncio.sleep(0.2)
        await _acombo(VK["ctrl"], VK["v"])
        await asyncio.sleep(0.5)
        return "Frame duplicated."

    elif action == "render":
        await _think(client, msg_id, "Opening render dialog...")
        await _acombo(VK["ctrl"], VK["shift"], VK["r"])
        await asyncio.sleep(2.0)
        return "Render dialog opened."

    # ── Raw key fallback ───────────────────────────────────────────────────
    else:
        parts = action.split("+")
        vks = [VK.get(p.strip()) for p in parts]
        if all(vks):
            await _acombo(*vks)
            await asyncio.sleep(0.5)
            return f"Executed: {action}"
        return f"[ERROR] Unknown action: {action}"


def available_actions() -> str:
    lines = ["Available OpenToonz actions:"]
    for name, desc in ACTIONS.items():
        lines.append(f"  • {name}: {desc}")
    return "\n".join(lines)

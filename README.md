# T — AI Core v1.0.0

> A fully local JARVIS-inspired AI assistant. Voice, security, OSINT, autonomous operations, hardware control, red team tools — all in one.

---

## Requirements

| Dependency | Version | Notes |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Rust | stable | `winget install Rustlang.Rust.MSVC` |
| VirtualBox | 7.x | For offensive modules — optional |

---

## Quick Start

### 1. Clone and install

```powershell
git clone https://github.com/NoobGramer-Py/T.git
cd T
npm install
cd brain
pip install -r requirements.txt
cd ..
```

### 2. Configure

```powershell
copy .env.example .env
# Edit .env — add your GROQ_API_KEY at minimum
```

### 3. Run (development)

**Terminal 1 — Brain:**
```powershell
cd brain
python main.py
```

**Terminal 2 — Interface:**
```powershell
npm run tauri dev
```

Or use the single launcher:
```powershell
start.bat
```

---

## Production Build

Build a standalone `.exe` installer:

```powershell
npm run tauri build
```

Output: `src-tauri/target/release/bundle/nsis/T_1.0.0_x64-setup.exe`

Run the installer — T installs to your user AppData and gets a Start Menu entry.

---

## Persistence (Auto-start on boot)

Run once as Administrator:

```powershell
pip install pywin32 pystray pillow
cd brain
python service/install.py
```

This installs:
- **Windows service** — brain starts on boot, restarts on crash automatically
- **Tray icon** — cyan arc reactor in system tray, right-click to open/restart/stop T

To uninstall:
```powershell
python service/install.py --uninstall
```

---

## Kali VM Setup (Offensive Modules)

1. Download Kali VirtualBox image from [kali.org](https://www.kali.org/get-kali/#kali-virtual-machines)
2. Import `.ova` into VirtualBox
3. Settings → Network → Adapter 1 → **Host-Only Adapter**
4. Start VM — run `ip a` → note the `192.168.56.x` IP
5. `sudo systemctl enable ssh --now`
6. T → Settings → VM → enter IP `192.168.56.104`, user `kali`, password `kali`
7. Security → VM → REFRESH → `SSH: CONNECTED`

Install OSINT tools on Kali:
```bash
pip3 install sherlock-project maigret holehe --break-system-packages
wget https://github.com/sundowndev/phoneinfoga/releases/latest/download/phoneinfoga_Linux_x86_64.tar.gz
tar -xzf phoneinfoga_Linux_x86_64.tar.gz && sudo mv phoneinfoga /usr/local/bin/
```

---

## Architecture

```
┌─────────────────────────────────────┐
│  Tauri 2.0 Frontend (React + Rust)  │
│  ws://127.0.0.1:7891 ←──────────────┤
└─────────────────────────────────────┘
              │
┌─────────────▼────────────────────────┐
│  Python FastAPI Brain               │
│  LLM: Groq (llama-3.3-70b)          │
│  Fallback: Ollama (llama3.2)        │
│  DB: SQLite (6 tables)              │
└──────────────────────────────────────┘
              │
┌─────────────▼────────────────────────┐
│  Kali Linux VM (VirtualBox)         │
│  SSH via paramiko                   │
│  60+ tools: Metasploit, Nmap,       │
│  Sherlock, Maigret, Nuclei, ffuf... │
└──────────────────────────────────────┘
```

---

## Phases

| Phase | Feature |
|---|---|
| 1–6 | Foundation, memory, voice, agents, integrations, proactive engine |
| 7 | Hardware control (Arduino / MQTT / serial) |
| 8 | Offensive security — 9 categories, 60+ tools |
| 9 | Device exploitation — router, mobile, IoT |
| 10 | Red Team Lab — full attack chain, phishing, RAT, auto-report |
| 10+ | OPS tab — real-world scoped operations, CTF mode |
| 11 | Intelligence — phone/person/org OSINT, breach, dark web, relationship graph |
| 12 | Autonomous engine — goal → plan → execute → report |
| 13 | Stealth & evasion — AV bypass, log clearing, LOLBins, process migration |
| 14 | Persistence — Windows service, watchdog, tray icon |
| 15 | Packaging — installer, production build, single-click launcher |

---

## Logs

```
%APPDATA%\T\logs\brain.log      — brain output
%APPDATA%\T\logs\watchdog.log   — service watchdog
%APPDATA%\T\logs\service.log    — Windows service events
```

---

*For authorized use on systems you own or have explicit permission to test.*

# Project T — Execution Plan

> **Architecture**: Python brain ↔ WebSocket ↔ Tauri HUD  
> **Owner**: Abdul  
> **Status**: Active development

---

## Current State

The repo currently contains the **Tauri/React/Rust** desktop frontend (Structure 1).
It is the most complete codebase and serves as the foundation.

Two additional codebases exist outside this repo:
- **Python full backend** (Structure 2) — agents, hardware, integrations, perception, proactive engine
- **t-assistant** (Structure 3) — clean voice pipeline (Porcupine + Whisper + Kokoro)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Tauri HUD (this repo)           │
│  React/TS frontend + Rust system commands    │
│  Chat · Security · System · Network          │
│  Five panels, Three.js visualizer            │
└────────────────────┬────────────────────────┘
                     │ WebSocket (ws://localhost:7891)
┌────────────────────▼────────────────────────┐
│              Python Brain                    │
│  FastAPI + WebSocket server (port 7891)      │
│  core/engine.py — central router             │
│  agents/ — planner, executor, confirmation  │
│  memory/ — short-term + ChromaDB long-term  │
│  voice/ — Porcupine wake + Whisper + Kokoro │
│  integrations/ — calendar, email, web       │
│  proactive/ — alerts, monitors, suggestions │
│  hardware/ — serial, GPIO, MQTT              │
└─────────────────────────────────────────────┘
```

**Data ownership:**
- SQLite (Tauri) → UI state: messages, tasks, profile, scheduler, clipboard
- ChromaDB (Python) → long-term semantic memory, preferences, habits
- Python is authoritative on voice, agents, hardware, and integrations
- Rust is authoritative on OS-level commands: processes, files, network, security tools

---

## Repository Structure (target)

```
T/                                  ← Tauri desktop app (exists)
├── PLAN.md
├── .gitignore
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── postcss.config.js
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── ErrorBoundary.tsx
│   ├── vite-env.d.ts
│   ├── store/index.ts
│   ├── lib/
│   │   ├── ai.ts                   ← Groq/Ollama router
│   │   ├── tauri.ts                ← Rust command bridges
│   │   └── bridge.ts               ← [NEW] WebSocket client to Python brain
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useMemory.ts
│   │   ├── useSystemStats.ts
│   │   ├── useVoice.ts
│   │   └── useBridge.ts            ← [NEW] React hook for Python brain connection
│   └── components/
│       ├── hud/
│       │   ├── JarvisCoreVisualizer.tsx
│       │   ├── TopBar.tsx
│       │   └── SideNav.tsx
│       ├── chat/ChatPanel.tsx
│       ├── security/SecurityPanel.tsx
│       ├── system/SystemPanel.tsx
│       ├── network/NetworkPanel.tsx
│       └── settings/SettingsPanel.tsx
├── src-tauri/
│   ├── tauri.conf.json
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       ├── lib.rs
│       └── commands/
│           ├── mod.rs
│           ├── system.rs
│           ├── security.rs
│           ├── network.rs
│           └── memory.rs
│       └── db/
│           ├── mod.rs
│           └── memory.rs
└── brain/                          ← [NEW] Python brain (to be added)
    ├── main.py                     ← Entry point, starts brain + WebSocket server
    ├── requirements.txt
    ├── config/
    │   ├── settings.py
    │   ├── features.yaml
    │   ├── personality.yaml
    │   └── hardware_devices.yaml
    ├── core/
    │   ├── engine.py               ← Central router
    │   ├── bus.py                  ← Internal message bus
    │   ├── tool_registry.py
    │   ├── llm.py                  ← Ollama / Anthropic switch
    │   ├── ws_server.py            ← [NEW] FastAPI WebSocket server
    │   └── logger.py
    ├── memory/
    │   ├── short_term.py
    │   ├── long_term.py            ← ChromaDB
    │   └── summarizer.py
    ├── voice/
    │   ├── wake_word.py            ← Porcupine
    │   ├── stt.py                  ← Whisper
    │   ├── tts.py                  ← Kokoro (local) / ElevenLabs (cloud)
    │   └── vad.py
    ├── agents/
    │   ├── planner.py
    │   ├── executor.py
    │   ├── confirmation.py
    │   └── recovery.py
    ├── integrations/
    │   ├── calendar/
    │   ├── email/
    │   ├── smart_home/
    │   ├── web/
    │   └── system/
    ├── proactive/
    │   ├── alerts.py
    │   ├── monitor.py
    │   └── suggestions.py
    ├── hardware/
    │   ├── abstraction.py
    │   ├── device_registry.py
    │   ├── serial_controller.py
    │   ├── gpio_controller.py
    │   ├── mqtt_controller.py
    │   └── safety.py
    └── data/
        ├── memory/                 ← ChromaDB persistent store (gitignored)
        └── logs/                   ← Gitignored
```

---

## Execution Phases

### Phase 1 — Foundation & Bridge ← START HERE
**Goal**: Python brain starts, connects to Tauri HUD over WebSocket. Chat works end-to-end.

- [ ] `brain/main.py` — entry point, boots FastAPI + WebSocket server on port 7891
- [ ] `brain/core/ws_server.py` — WebSocket server, message dispatch
- [ ] `brain/core/engine.py` — receives messages, routes to LLM, returns response
- [ ] `brain/core/llm.py` — Ollama primary, Anthropic fallback
- [ ] `brain/core/logger.py` — unified structured logging
- [ ] `brain/requirements.txt`
- [ ] `src/lib/bridge.ts` — WebSocket client, connects to brain, send/receive
- [ ] `src/hooks/useBridge.ts` — React hook exposing bridge state and send fn
- [ ] Wire `ChatPanel.tsx` to use bridge when available, fallback to current Groq direct

**Done when**: `python brain/main.py` starts, Tauri connects, chat messages flow through Python brain.

---

### Phase 2 — Memory Unification
**Goal**: Python brain has persistent memory. Tauri SQLite remains for UI state only.

- [ ] `brain/memory/short_term.py` — conversation context window (last N turns)
- [ ] `brain/memory/long_term.py` — ChromaDB: store facts, preferences, habits
- [ ] `brain/memory/summarizer.py` — compress old context, retain key facts
- [ ] Brain injects long-term memory into every LLM system prompt
- [ ] Profile sync: on start, Tauri profile data pushed to brain via WebSocket

**Done when**: Brain remembers facts across sessions. "Remember that I prefer Python over JS" persists.

---

### Phase 3 — Voice Pipeline
**Goal**: Wake word → STT → brain → TTS. Fully local, no cloud required.

- [ ] `brain/voice/vad.py` — voice activity detection
- [ ] `brain/voice/wake_word.py` — Porcupine "Hey T" detection
- [ ] `brain/voice/stt.py` — Whisper transcription
- [ ] `brain/voice/tts.py` — Kokoro offline TTS, ElevenLabs optional
- [ ] Brain sends TTS audio back over WebSocket for Tauri to play
- [ ] Visualizer state (idle/listening/speaking) driven by brain events

**Done when**: Say "Hey T" → it listens → transcribes → responds with voice.

---

### Phase 4 — Agents & Planning
**Goal**: Complex multi-step requests are planned and executed, not just answered.

- [ ] `brain/core/tool_registry.py` — all callable tools registered here
- [ ] `brain/core/bus.py` — internal event bus connecting modules
- [ ] `brain/agents/planner.py` — breaks requests into ordered subtasks
- [ ] `brain/agents/executor.py` — executes steps, calls tools, handles Tauri commands
- [ ] `brain/agents/confirmation.py` — intercepts irreversible actions, asks user
- [ ] `brain/agents/recovery.py` — handles failed steps, retries alternatives

**Done when**: "Open Chrome, go to GitHub, clone my latest repo" executes as a plan.

---

### Phase 5 — Integrations
**Goal**: T can interact with calendar, email, web, and system apps.

- [ ] `brain/integrations/web/search.py` — web search
- [ ] `brain/integrations/web/weather.py` — weather
- [ ] `brain/integrations/web/news.py` — news headlines
- [ ] `brain/integrations/system/apps.py` — launch/control apps
- [ ] `brain/integrations/system/browser.py` — browser automation
- [ ] `brain/integrations/calendar/google_calendar.py`
- [ ] `brain/integrations/email/gmail.py`

**Done when**: "What's on my calendar tomorrow?" and "Search for recent CVEs in OpenSSL" both work.

---

### Phase 6 — Proactive Engine
**Goal**: T initiates — alerts, monitors, suggestions without being asked.
T becomes genuinely proactive: it watches the system in the background, detects anomalies,
fires scheduled alerts, and surfaces suggestions based on observed patterns.
All proactive messages arrive as chat_chunk events — no new UI required.

#### Architecture
```
brain/proactive/
├── __init__.py
├── engine.py          ← scheduler loop, starts all monitors, routes alerts to client
├── monitor.py         ← system health: CPU, RAM, disk, network anomalies
├── alerts.py          ← time-based + condition-based alert definitions
└── suggestions.py     ← pattern observer, surfaces contextual nudges
```

#### engine.py — Proactive Scheduler
- Runs as a background asyncio task started at brain boot
- Polls monitors every 30s
- Fires alert callbacks when thresholds are crossed
- Sends proactive messages to all connected clients via `ws_server.broadcast()`
- Tracks cooldowns — no alert fires more than once per 10 minutes

#### monitor.py — System Health
Checks every 30 seconds:
- CPU > 85% for 2+ consecutive checks → alert with top process name
- RAM > 90% → alert with top memory consumer
- Disk < 5GB free on any drive → alert with drive path
- Network: new listening port detected → alert with PID and process name
- Process crash: known process disappears from running list → alert

#### alerts.py — Time-based + Condition Alerts
- Scheduled reminders: Abdul can say "remind me in 2 hours" → stored alert fires via proactive engine
- Daily summary: at a configured time, T sends a brief system health summary
- Security: new outbound connection to unknown IP → log + alert (if suspicious)
- Alert schema: `{type, message, severity: info|warn|critical, cooldown_minutes}`

#### suggestions.py — Pattern Observer
Observes over time:
- If Abdul asks about the same topic 3+ times → suggest saving it to memory
- If CPU spikes repeatedly at same time → suggest investigating the schedule
- If a tool command fails repeatedly → suggest an alternative
- Suggestions are short, one-line, non-intrusive

#### WebSocket integration
New message type sent from brain to Tauri:
```json
{"type": "proactive_alert", "severity": "warn", "message": "CPU at 91% — chrome.exe consuming 4.2GB RAM"}
{"type": "proactive_alert", "severity": "info",  "message": "Daily summary: system healthy, 3 tasks completed today"}
{"type": "proactive_alert", "severity": "critical", "message": "New listening port 4444 opened by powershell.exe — possible reverse shell"}
```
Tauri displays these as non-blocking notifications in the chat panel (different styling from T responses).

#### Files to build
- [ ] `brain/proactive/__init__.py`
- [ ] `brain/proactive/engine.py` — background scheduler, broadcast loop
- [ ] `brain/proactive/monitor.py` — CPU/RAM/disk/network/process watchers
- [ ] `brain/proactive/alerts.py` — alert definitions, cooldown tracker, scheduled alerts
- [ ] `brain/proactive/suggestions.py` — pattern observer
- [ ] `brain/core/ws_server.py` — add `broadcast()` function for proactive messages
- [ ] `brain/core/engine.py` — start proactive engine on brain boot, handle `set_alert` message type
- [ ] `src/hooks/useBridge.ts` — handle `proactive_alert` message type
- [ ] `src/components/chat/ChatPanel.tsx` — render proactive alerts with distinct styling

**Done when**: T autonomously says "CPU has been at 95% for 10 minutes — chrome.exe is the culprit. Kill it?" and "Reminder: you asked me to check in at 3pm."

---

### Phase 7 — Hardware
**Goal**: T controls physical devices.

- [ ] `brain/hardware/abstraction.py`
- [ ] `brain/hardware/device_registry.py`
- [ ] `brain/hardware/serial_controller.py`
- [ ] `brain/hardware/gpio_controller.py`
- [ ] `brain/hardware/mqtt_controller.py`
- [ ] `brain/hardware/safety.py`
- [ ] `brain/config/hardware_devices.yaml`

**Done when**: T can toggle a GPIO pin or send a serial command to an Arduino.

---

## Communication Protocol (Tauri ↔ Brain)

All messages over WebSocket are JSON with this shape:

```json
// Tauri → Brain
{ "type": "chat", "id": "uuid", "content": "user message" }
{ "type": "profile_sync", "data": { "name": "Abdul", ... } }
{ "type": "voice_start" }
{ "type": "voice_stop" }

// Brain → Tauri
{ "type": "chat_response", "id": "uuid", "content": "T's reply" }
{ "type": "tts_audio", "data": "base64 wav" }
{ "type": "visualizer", "mode": "listening" | "speaking" | "idle" }
{ "type": "notification", "title": "...", "body": "..." }
{ "type": "brain_status", "online": true }
```

---

## Key Decisions (locked)

1. **Tauri is the UI shell. Python is the brain.** Never reverse this.
2. **Voice runs entirely in Python.** Tauri's current Web Speech API TTS is a temporary fallback only.
3. **SQLite (Tauri) = UI state. ChromaDB (Python) = long-term semantic memory.** No duplication.
4. **All Rust commands (system, security, network) stay in Rust.** Python calls them via Tauri invoke when needed from agent workflows — never reimplements them.
5. **T's personality lives in `brain/core/llm.py` system prompt.** The version in `src/lib/ai.ts` is the direct-API fallback only.
6. **WebSocket port: 7891.** Fixed. Brain always starts on this port.
7. **Python brain is optional at boot.** Tauri starts and functions without it (direct Groq). When brain connects, it takes over.

---

## Phase 8 — Offensive & Defensive Security (Full Spectrum)

**Goal**: T has every attack and defense capability. Nothing executes without explicit user confirmation.

### Confirmation Model
Every offensive action follows this exact flow — no exceptions:
```
T describes the action in plain English + shows exact command to be run
→ Single confirmation prompt in ChatPanel: "Confirm? [YES / NO]"
→ User types YES
→ Action executes, output streamed to SecurityPanel
→ Action logged to security_log table with timestamp, target, command, result
```
T never chains offensive actions without re-confirming each step.

### Architecture
```
SecurityPanel.tsx
    ↓
brain/offensive/orchestrator.py   ← plans, confirms, dispatches
    ├── src-tauri/commands/security.rs     (Windows-native execution)
    ├── brain/offensive/vm_bridge.py       (Linux VM via SSH)
    └── brain/offensive/stream.py          (streams stdout back to HUD)
```

### VirtualBox / Linux VM Integration
T controls the Linux VM via `VBoxManage` (VM lifecycle) + SSH (command execution).

**One-time user setup required:**
1. Enable SSH on VM: `sudo apt install openssh-server && sudo systemctl enable ssh`
2. Set VM network to Host-Only Adapter in VirtualBox → VM gets fixed IP (e.g. `192.168.56.101`)
3. On Windows host: generate SSH key → `ssh-keygen -t ed25519`
4. Copy public key to VM → `ssh-copy-id user@192.168.56.101`
5. In T Settings: enter VM name (exact VirtualBox name), VM IP, SSH user, SSH key path

**What T can then do:**
- Start / stop / snapshot the VM
- SSH in and run any command with streamed output
- Install tools after confirmation: `sudo apt install <tool> -y`
- Auto-detect if a required tool is missing, offer to install it

**New Settings fields (SettingsPanel.tsx):**
```
vm_name        → VirtualBox VM name (e.g. "Kali-Linux")
vm_ip          → Fixed IP (e.g. "192.168.56.101")
vm_ssh_user    → SSH username
vm_ssh_key     → Path to private key on Windows host
```

### Files to Add

**Python:**
```
brain/offensive/
├── orchestrator.py      ← receives action requests, handles confirmation flow
├── vm_bridge.py         ← VBoxManage + SSH client, streams output
├── stream.py            ← pipes subprocess stdout over WebSocket to HUD
└── tool_check.py        ← checks if a tool exists on VM, offers install
```

**Rust (src-tauri/src/commands/security.rs additions):**
- `credential_dump` — Windows LSASS memory read via Windows API
- `inject_analysis` — detect process injection (hollowing, DLL injection)
- `raw_packet_capture` — Windows raw socket capture (requires elevated)
- `arp_table` — read/manipulate ARP table

**TypeScript:**
- `src/lib/bridge.ts` — add `sendOffensiveAction(action, params)` + `onOffensiveStream(cb)`
- `src/components/security/SecurityPanel.tsx` — add offensive tabs (see below)

### Full Capability Map

| Capability | Executor | Tool | Location |
|---|---|---|---|
| Port scan (fast/full) | Rust | nmap | security.rs (exists) |
| Service fingerprinting | Rust | nmap -sV | security.rs |
| OS detection | Rust | nmap -O | security.rs |
| Vuln scan | Rust | nmap --script vuln | security.rs |
| Password hash cracking | VM | hashcat | vm_bridge.py |
| Online brute force | VM | hydra | vm_bridge.py |
| WiFi handshake capture | VM | hcxdumptool | vm_bridge.py |
| WPA cracking | VM | hashcat (mode 22000) | vm_bridge.py |
| WiFi deauth | VM | aireplay-ng | vm_bridge.py |
| Exploitation | VM | Metasploit msfconsole | vm_bridge.py |
| Payload generation | VM | msfvenom | vm_bridge.py |
| Reverse shell listener | VM | Metasploit multi/handler | vm_bridge.py |
| Packet capture | VM | tcpdump / tshark | vm_bridge.py |
| MITM (ARP poison) | VM | arpspoof + ettercap | vm_bridge.py |
| SSL strip | VM | sslstrip | vm_bridge.py |
| Web app scan | VM | nikto / sqlmap | vm_bridge.py |
| Fuzzing | VM | ffuf / wfuzz | vm_bridge.py |
| Steganography | VM | steghide / stegsolve | vm_bridge.py |
| Credential dump (Win) | Rust | Windows API (LSASS) | security.rs |
| Process injection detect | Rust | Windows API | security.rs |
| Packet capture (Win) | Rust | raw sockets | security.rs |
| OSINT (expanded) | Python | shodan + theHarvester | offensive/orchestrator.py |

### New SecurityPanel Tabs
Current tabs: NMAP, IP REP, IP INTEL, PORT SCAN, EMAIL OSINT, CVE, PORTS, AUDIT, DNS LEAK, VPN, FIREWALL, PASSWORD, URL SCAN, EVENT LOG

Add:
- `CRACK` — hash input + wordlist selection → hashcat/john via VM
- `EXPLOIT` — Metasploit module browser + payload generator
- `WIFI` — interface selection, handshake capture, deauth, WPA crack
- `MITM` — ARP poison setup, SSL strip toggle, traffic capture
- `PAYLOAD` — msfvenom wrapper, shellcode generator
- `VM` — VM status, start/stop, SSH terminal (embedded), tool installer

### Key Rules (locked)
1. **Every single offensive action requires YES confirmation** — no batching, no auto-chaining
2. **T describes what it will do before asking** — plain English + exact command shown
3. **All actions are logged** — target, command, timestamp, result → security_log table
4. **VM tools install only after confirmation** — T asks "hashcat not found on VM. Install it? [YES/NO]"
5. **T never initiates offensive actions proactively** — proactive engine is blocked from offensive module
6. **Elevated actions on Windows** — T warns when a command requires admin and explains why

---

## Development Notes

- `node_modules/`, `src-tauri/target/`, `brain/data/` are gitignored
- All work is committed directly to `main` for now
- Commit format: `[phase] description` e.g. `[P1] add brain WebSocket server`

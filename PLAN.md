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

### Phase 6b — Live System Access (Host Device)
**Goal**: T escalates its own privileges on Abdul's machine and gains live access to protected
system resources — credential stores, process memory, registry, SAM database, running sessions.
Every action is read-only by default. Nothing modifies, nothing persists, nothing exposes the host.

#### What This Is
T performs local privilege escalation and live system introspection on its own host machine.
This is for Abdul to:
- Retrieve his own stored credentials without needing external tools
- Inspect running processes at memory level
- Access protected system areas (SAM, LSASS, registry hives)
- Understand exactly what is exposed on his own machine

This is NOT:
- A backdoor or persistent implant
- A network-facing capability (no outbound connections from this module)
- An auto-executing feature (every single action requires explicit YES confirmation)

---

#### Safety Model — Non-Negotiable Rules
These rules are hardcoded at the implementation level, not just policy:

**1. Read-Only by Default**
Every operation reads data only. No files written, no registry keys modified, no processes
injected. The only exception is a temporary dump file written to `%TEMP%\T_dump_<timestamp>.bin`
which is automatically deleted within 60 seconds of creation.

**2. Confirmation Gate — Triple Layer**
```
Layer 1: T describes the action in plain English + shows exact command
Layer 2: Risk assessment shown — what this touches, what it reads, what could go wrong
Layer 3: User types YES (not a button click — must be typed) → action executes
```
No batching. Each individual action goes through all three layers.

**3. No Network Exposure**
The live access module has a firewall check at startup:
- Verifies Windows Firewall is active before proceeding
- All extracted data stays in memory only — never written to disk except temp files
- Temp files are encrypted with a session key that lives only in memory
- No data is sent over the WebSocket except the formatted text summary shown to Abdul

**4. Automatic Session Expiry**
Any elevated session expires automatically after 10 minutes of inactivity.
T notifies Abdul 2 minutes before expiry and drops privileges on timeout.
Expiry is enforced in code — not just a suggestion.

**5. No Persistence**
Nothing installed, nothing scheduled, no registry Run keys touched.
T's elevated access is a transient token that lives only for the duration of the operation.

**6. Integrity Check Before Every Operation**
Before executing any privileged operation, T checks:
- Is Windows Defender / AV running? If not → warn and ask if Abdul wants to proceed
- Are any network connections currently active to unknown IPs? → log and warn
- Is the Tauri process the parent? → verify chain of custody
If any check fails → halt and report, do not proceed without explicit re-confirmation.

---

#### Capability Map

| Capability | Method | Safety Level | What It Touches |
|---|---|---|---|
| UAC bypass (self-elevation) | fodhelper / eventvwr bypass | Read setup only | Windows registry (read) |
| LSASS memory read | MiniDump via comsvcs.dll | Temp file, auto-deleted | LSASS process memory |
| SAM + SYSTEM hive extract | reg save to temp | Temp files, auto-deleted | HKLM\SAM, HKLM\SYSTEM |
| Credential Manager dump | cmdkey + PowerShell | Read only | Windows Vault |
| Running session tokens | token impersonation check | Read only | Process token table |
| Registry credential scan | reg query on known paths | Read only | HKLM, HKCU credential paths |
| Browser credential extract | path-based file read | Read only | Chrome/Firefox profile dirs |
| WiFi password extract | netsh wlan show profiles | Read only | Windows WLAN service |
| Environment credential scan | process env vars | Read only | Running process memory |
| Scheduled task inspection | schtasks /query | Read only | Task Scheduler |

---

#### Architecture

```
brain/local_access/
├── __init__.py
├── orchestrator.py     ← entry point, safety checks, confirmation flow, session manager
├── escalation.py       ← UAC bypass, token manipulation, admin check
├── credential.py       ← LSASS, SAM, Credential Manager, browser, WiFi
├── inspection.py       ← process tokens, scheduled tasks, registry scan, env vars
├── safety.py           ← firewall check, AV check, integrity verification, temp cleanup
└── session.py          ← elevated session lifecycle, 10min expiry, privilege drop
```

#### orchestrator.py
- Receives action requests from engine.py via new message type `local_access`
- Runs safety.py integrity checks first — aborts if any fail
- Runs triple-confirmation flow before any action
- Manages the elevated session lifecycle via session.py
- Streams results back to Tauri as `local_access_result` messages
- Logs every action to `brain/data/local_access.log` (local only, never synced)

#### escalation.py
- `check_elevation()` → is current process already admin?
- `request_elevation()` → re-launch brain with admin rights via UAC prompt (standard, visible)
- `uac_bypass()` → silent elevation via fodhelper or eventvwr registry technique
  - Only used if Abdul explicitly asks for silent elevation
  - Clearly labelled as a UAC bypass in the confirmation prompt
- `get_system_token()` → impersonate SYSTEM via token duplication from a SYSTEM process

#### credential.py
- `dump_lsass()` → MiniDump via comsvcs.dll → parse with pypykatz → return credential dict → delete dump
- `extract_sam()` → reg save SAM + SYSTEM to temp → extract hashes via impacket → delete temp files
- `dump_credential_manager()` → PowerShell `Get-StoredCredential` or cmdkey → parse → return
- `extract_browser_creds(browser)` → read Chrome/Edge/Firefox encrypted credential DBs → decrypt with DPAPI
- `extract_wifi_passwords()` → netsh wlan → return SSID + password pairs
- `scan_registry_creds()` → query known credential storage paths in registry

#### inspection.py
- `list_session_tokens()` → enumerate process tokens, flag high-privilege ones
- `scan_env_credentials()` → check running processes' environment for API keys, passwords, tokens
- `inspect_scheduled_tasks()` → list tasks with credentials or unusual paths
- `scan_startup_items()` → registry Run keys, startup folder — flag suspicious entries

#### safety.py
- `check_firewall()` → verify Windows Firewall is active on all profiles
- `check_av()` → verify Defender or AV is running
- `verify_parent_chain()` → confirm Tauri → brain process lineage
- `check_active_connections()` → netstat for suspicious outbound connections
- `cleanup_temp()` → delete all T_dump_* files from %TEMP%
- `encrypt_temp(data, key)` / `decrypt_temp(path, key)` → session-keyed temp file encryption

#### session.py
- `ElevatedSession` class — context manager
- On enter: escalate, log start time, start expiry timer
- On exit: drop to original token, cleanup temp files, log end time
- `expire()` → called after 10min inactivity, force-drops privileges, notifies Abdul

---

#### WebSocket Protocol Additions

```json
// Tauri → Brain
{"type": "local_access", "action": "dump_credentials", "id": "uuid"}
{"type": "local_access_confirm", "id": "uuid", "confirmed": true}

// Brain → Tauri
{"type": "local_access_check", "id": "uuid", "action": "dump_lsass",
 "description": "Read LSASS process memory to extract cached credentials",
 "risk": "Requires SYSTEM token. Temp dump file created then deleted. AV may flag.",
 "command": "rundll32 C:\\Windows\\System32\\comsvcs.dll MiniDump <lsass_pid> %TEMP%\\T_dump.bin full"}
{"type": "local_access_result", "id": "uuid", "data": "...formatted credential output..."}
{"type": "local_access_error", "id": "uuid", "error": "AV is not running — aborting for safety"}
{"type": "local_access_expired", "message": "Elevated session expired after 10min inactivity"}
```

---

#### Dependencies to Add (brain/requirements.txt)
```
pypykatz>=0.6.9        ← parse LSASS dumps — pure Python, no native deps
impacket>=0.12.0       ← SAM/SYSTEM hash extraction
pywin32>=306           ← Windows token manipulation (Windows only)
```

#### Files to Build
- [ ] `brain/local_access/__init__.py`
- [ ] `brain/local_access/orchestrator.py`
- [ ] `brain/local_access/escalation.py`
- [ ] `brain/local_access/credential.py`
- [ ] `brain/local_access/inspection.py`
- [ ] `brain/local_access/safety.py`
- [ ] `brain/local_access/session.py`
- [ ] `brain/core/engine.py` — add `local_access` and `local_access_confirm` message handlers
- [ ] `brain/requirements.txt` — add pypykatz, impacket, pywin32
- [ ] `src/hooks/useBridge.ts` — handle `local_access_check`, `local_access_result`, `local_access_expired`
- [ ] `src/components/chat/ChatPanel.tsx` — render confirmation flow + results for local_access

**Done when**: Abdul says "dump credentials from this machine" → T shows what it will do → Abdul types YES → T extracts cached credentials from LSASS, Credential Manager, browsers, WiFi → displays them in chat → all temp files deleted → session expires.

---


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

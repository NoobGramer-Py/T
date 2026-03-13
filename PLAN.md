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
**Goal**: T escalates its own privileges on Abdul's machine and gains live access to all
credential stores and process memory. Results appear as a summary in chat and full output
in a dedicated Security panel tab. Everything is read-only. Nothing persists. Host stays clean.

---

#### Decisions — Locked

| Decision | Choice |
|---|---|
| Elevation method | Separate elevated helper process — brain stays running, no offline period |
| Display | Summary in chat + full output in Security panel LOCAL ACCESS tab |
| Extraction trigger | All sources at once — one YES confirms the full run |
| Credential sources | All 8 — LSASS, SAM, Credential Manager, Browser, WiFi, Env vars, Scheduled tasks, Registry |
| Hash cracking | Pipe NTLM hashes directly to VM hashcat after extraction |
| Save output | Yes — offer encrypted file export after display |
| Defender mid-operation | Auto-fallback to alternative method, report which method was used |
| Process memory inspector | Included — read arbitrary process memory by PID, string search for tokens/passwords |
| Session expiry | No auto-expiry — session lasts until Abdul ends it manually |
| Kill switch | Both chat command (`end session`) and UI button in Security panel |

---

#### Safety Model — Hardcoded, Non-Negotiable

**1. Read-Only by Default**
No files written, no registry modified, no processes injected or terminated.
Temp dump files written only to `%TEMP%\T_<timestamp>.bin`, encrypted with session key,
auto-deleted within 60 seconds of parsing. Session key lives in memory only.

**2. Single Confirmation Gate**
```
T describes every source it will hit + exact method for each
T shows the risk for each source in plain English
Abdul types YES → full extraction runs
```
One confirmation covers the entire run. No per-source interruptions.

**3. No Network Exposure**
Firewall check runs before session start. Extracted data never leaves the helper process
as raw binary — only as formatted text sent over the local WebSocket to Tauri.
The encrypted save file is written locally only, never transmitted.

**4. Manual Session Control**
Session persists until Abdul ends it. No auto-expiry.
Kill switch (`end session` in chat OR button in Security panel) instantly:
- Terminates elevated helper process
- Deletes all temp files from `%TEMP%`
- Clears extracted data from memory
- Reverts to normal brain operation
- Confirms completion to Abdul in chat

**5. Integrity Check Before Session Start**
Before UAC prompt appears, T checks:
- Windows Firewall active on all profiles → if off, warn + ask to proceed
- No suspicious outbound connections → if found, list them + ask to proceed
- AV running → if not, warn (but do not block — Abdul may have disabled it intentionally)
All checks are informational warnings, not hard blocks (Abdul is the authority).

---

#### Architecture

```
brain/local_access/
├── __init__.py
├── orchestrator.py     ← receives local_access message, runs safety checks,
│                          confirmation flow, launches helper, streams results
├── helper.py           ← runs as elevated subprocess, performs all privileged ops,
│                          communicates back to orchestrator via encrypted pipe
├── escalation.py       ← spawns helper.py via ShellExecuteEx runas (standard UAC prompt)
│                          chooses helper vs brain-restart based on stability check
├── credential.py       ← all extraction logic: LSASS, SAM, browser, WiFi, env, registry
├── memory_inspector.py ← live process memory read by PID, string/pattern search
├── safety.py           ← firewall check, AV check, connection scan, temp cleanup,
│                          temp file encryption/decryption
└── session.py          ← session state, kill switch handler, encrypted file export
```

---

#### Elevation — Separate Helper Process

Brain spawns `helper.py` as an elevated subprocess via `ShellExecuteEx` with `runas` verb.
Windows shows the standard UAC dialog. Abdul clicks Yes.
Brain stays running and connected to Tauri throughout — no WebSocket drop.

Communication channel: named pipe (`\\.\pipe\T_local_access_<session_id>`)
- Pipe is created by brain before helper launch
- Helper connects to pipe after elevation
- All data flows through pipe as encrypted JSON
- Pipe key is generated per-session, lives only in brain memory

This is safer and more stable than restarting brain because:
- WebSocket connection to Tauri stays alive — no reconnect delay
- Chat history preserved — Abdul can keep talking while extraction runs
- Helper process isolated — if it crashes, brain continues normally
- Principle of least privilege — only helper.py runs as admin, not the entire brain

---

#### Credential Sources — All 8

**LSASS** — `credential.py: dump_lsass()`
Primary method: `comsvcs.dll MiniDump` via rundll32 → parse with pypykatz → delete dump
Fallback (if Defender blocks): `NtReadVirtualMemory` direct API call via ctypes → parse in-memory
Second fallback: `ProcDump` if available on system
Returns: plaintext passwords (if cached), NTLM hashes, Kerberos tickets

**SAM Database** — `credential.py: extract_sam()`
Method: `reg save HKLM\SAM` + `reg save HKLM\SYSTEM` to temp → parse with impacket secretsdump → delete temp
Returns: local account NTLM hashes

**Windows Credential Manager** — `credential.py: dump_credential_manager()`
Method: `vaultcmd /listcreds` + PowerShell `Get-StoredCredential` + direct Vault API via ctypes
Returns: stored usernames, passwords, URLs, certificate credentials

**Browser Saved Passwords** — `credential.py: extract_browser_creds()`
Chrome/Edge: read `Login Data` SQLite DB → decrypt with DPAPI (`CryptUnprotectData`) → parse
Firefox: read `logins.json` + `key4.db` → decrypt with NSS library or pure Python mozillapassword
Returns: URL, username, plaintext password for each entry

**WiFi Passwords** — `credential.py: extract_wifi()`
Method: `netsh wlan show profiles` → for each SSID: `netsh wlan show profile name=X key=clear`
Returns: SSID + plaintext WPA key for every saved network

**Environment Variables** — `credential.py: scan_env_vars()`
Method: enumerate all running processes via WMI → read each process's environment block
Filter for known patterns: `API_KEY`, `SECRET`, `PASSWORD`, `TOKEN`, `PASSWD`, `PWD`, `KEY`
Returns: process name, variable name, value for each hit

**Scheduled Tasks** — `credential.py: inspect_scheduled_tasks()`
Method: `schtasks /query /fo LIST /v` → parse for RunAs credentials, embedded passwords
Returns: task name, run-as user, command, any embedded credentials found

**Registry Credential Paths** — `credential.py: scan_registry()`
Queries known paths:
- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` (DefaultPassword)
- `HKCU\Software\SimonTatham\PuTTY\Sessions` (SSH saved sessions)
- `HKLM\SYSTEM\CurrentControlSet\Services` (service account passwords)
- `HKCU\Software\ORL\WinVNC3` (VNC passwords)
- `HKCU\Software\TightVNC\Server` (VNC passwords)
- `HKLM\SOFTWARE\RealVNC\WinVNC4` (VNC passwords)
Returns: registry path, value name, decrypted value

---

#### Process Memory Inspector — `memory_inspector.py`

`inspect_process(pid, patterns)`
- Opens process handle with `PROCESS_VM_READ` via ctypes
- Enumerates memory regions via `VirtualQueryEx`
- Reads readable regions via `ReadProcessMemory`
- Searches for patterns: regex list supplied by Abdul or predefined (passwords, tokens, keys)
- Returns matching strings with surrounding context (50 chars each side)

`search_all_processes(pattern)`
- Runs `inspect_process` across all running processes
- Skips System, Idle, and protected processes gracefully
- Returns hits grouped by process name + PID

Predefined search patterns:
- `password\s*[:=]\s*\S+`
- `token\s*[:=]\s*[A-Za-z0-9+/]{20,}`
- `api[_-]?key\s*[:=]\s*\S+`
- `Bearer [A-Za-z0-9\-._~+/]+=*`
- `Authorization: [^\r\n]+`

---

#### Hash Cracking Pipeline

After SAM/LSASS extraction, if NTLM hashes are found:
1. T displays hashes in Security panel immediately
2. T sends hashes to VM via `vm_bridge.py` (Phase 8 — if VM is configured)
3. If VM not configured: T generates the hashcat command for Abdul to run manually:
   ```
   hashcat -m 1000 -a 0 hashes.txt rockyou.txt --show
   ```
4. Results stream back to Security panel via existing vm_bridge stream

---

#### Encrypted File Export

After extraction completes, T offers:
```
T: Extraction complete. Save to encrypted file?
Abdul: yes
T: Saved to C:\Users\abdul\Desktop\T_extract_<timestamp>.enc
   Password: <32-char random password shown once in chat>
   Decrypt: openssl enc -d -aes-256-cbc -in T_extract.enc -out T_extract.txt
```

Encryption: AES-256-CBC via Python `cryptography` library
Password: 32-char random, shown once in chat, never stored anywhere

---

#### WebSocket Protocol Additions

```json
// Tauri → Brain
{"type": "local_access_start", "id": "uuid"}
{"type": "local_access_confirm", "id": "uuid", "confirmed": true}
{"type": "local_access_end"}
{"type": "memory_inspect", "id": "uuid", "pid": 1234, "pattern": "password"}

// Brain → Tauri
{"type": "local_access_ready", "id": "uuid",
 "sources": ["LSASS","SAM","CredManager","Browsers","WiFi","EnvVars","ScheduledTasks","Registry"],
 "risk_summary": "Requires admin. LSASS dump may trigger AV — fallback ready. All temp files auto-deleted."}
{"type": "local_access_progress", "id": "uuid", "source": "LSASS", "status": "running|done|fallback|failed"}
{"type": "local_access_summary", "id": "uuid", "chat_summary": "Found 12 credentials across 5 sources"}
{"type": "local_access_full", "id": "uuid", "data": "...full formatted output for Security panel..."}
{"type": "local_access_hashes", "id": "uuid", "hashes": ["aad3b...", "31d6c..."]}
{"type": "local_access_ended", "message": "Session ended. All temp files deleted."}
{"type": "memory_inspect_result", "id": "uuid", "hits": [...]}
```

---

#### New UI — Security Panel LOCAL ACCESS Tab

```
┌─ LOCAL ACCESS ──────────────────────────────────────────────┐
│  [START SESSION]                           [END SESSION ■]  │
│  Status: ● Active / ○ Idle                                  │
│                                                             │
│  ┌─ Sources ──────────────────────────────────────────────┐ │
│  │ ✓ LSASS        ✓ SAM           ✓ CredManager          │ │
│  │ ✓ Browsers     ✓ WiFi          ✓ EnvVars               │ │
│  │ ✓ Sched.Tasks  ✓ Registry                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  [EXTRACT ALL]   [INSPECT PROCESS]   [SAVE ENCRYPTED]      │
│                                                             │
│  ┌─ Results ──────────────────────────────────────────────┐ │
│  │ (full extraction output streamed here)                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

`[END SESSION ■]` button = kill switch — same effect as typing `end session` in chat.

---

#### Dependencies to Add

```
pypykatz>=0.6.9        ← LSASS dump parsing — pure Python
impacket>=0.12.0       ← SAM/SYSTEM hash extraction
pywin32>=306           ← Windows token/process APIs
cryptography>=42.0.0   ← AES-256 encrypted file export (already may be installed)
```

---

#### Files to Build

- [ ] `brain/local_access/__init__.py`
- [ ] `brain/local_access/orchestrator.py`
- [ ] `brain/local_access/helper.py`
- [ ] `brain/local_access/escalation.py`
- [ ] `brain/local_access/credential.py`
- [ ] `brain/local_access/memory_inspector.py`
- [ ] `brain/local_access/safety.py`
- [ ] `brain/local_access/session.py`
- [ ] `brain/core/engine.py` — add `local_access_start`, `local_access_confirm`, `local_access_end`, `memory_inspect` handlers
- [ ] `brain/requirements.txt` — add pypykatz, impacket, pywin32, cryptography
- [ ] `src/hooks/useBridge.ts` — handle all local_access message types
- [ ] `src/components/security/SecurityPanel.tsx` — add LOCAL ACCESS tab
- [ ] `src-tauri/tauri.conf.json` — no new permissions needed (helper runs separately)

**Done when**: Abdul says "extract credentials" → T shows what it will hit → Abdul types YES →
UAC prompt appears → Abdul clicks Yes → helper runs → LSASS/SAM/browsers/WiFi/etc extracted →
summary in chat, full output in Security panel → NTLM hashes piped to VM hashcat →
Abdul types `end session` or clicks ■ → all temp files deleted → session closed.

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

## Phase 7 — Hardware Control

**Goal**: T controls physical devices connected to Abdul's machine — Arduino, sensors, relays,
anything that speaks serial/GPIO/MQTT. T understands the device, confirms before any state change,
and logs every action. Nothing fires without Abdul's explicit command.

---

### What This Phase Covers

Abdul says "turn on the relay on pin 4" or "read temperature from Arduino" or "send MQTT command
to bedroom light" and T handles it — discovering the device, sending the command, reading back
the response, and reporting the result. Every state-changing command requires a YES confirmation.
Every result is logged.

---

### Architecture

```
brain/hardware/
├── __init__.py
├── registry.py          ← device registry — what's connected, what each device can do
├── serial_handler.py    ← serial port discovery, connect, send, read, auto-detect baud
├── gpio_handler.py      ← GPIO pin control via serial passthrough (Arduino) or direct RPi GPIO
├── mqtt_handler.py      ← MQTT pub/sub client, connects to broker, sends/receives messages
├── command_router.py    ← receives hardware commands from engine, routes to right handler
└── safety.py            ← rate limiting, state validation, command blocklist
```

---

### Device Registry — `registry.py`

The registry is the single source of truth for what hardware T knows about.
Loaded from `brain/config/hardware_devices.yaml` at startup.
Abdul can add devices via chat ("register this device as relay_board on COM3").

```yaml
# brain/config/hardware_devices.yaml
devices:
  - id: arduino_uno
    type: serial
    port: COM3          # Windows COM port or /dev/ttyUSB0 on Linux
    baud: 9600
    description: Arduino Uno — relay board + DHT22 sensor
    capabilities:
      - digital_write   # turn pin on/off
      - digital_read    # read pin state
      - analog_read     # read analog pin
      - dht_read        # read temperature/humidity from DHT sensor

  - id: bedroom_light
    type: mqtt
    broker: 192.168.1.100
    port: 1883
    topic_pub: home/bedroom/light/set
    topic_sub: home/bedroom/light/state
    description: Smart bedroom light via MQTT
    capabilities:
      - publish         # send on/off/dim commands
      - subscribe       # receive state updates
```

`registry.py` functions:
- `load()` — read hardware_devices.yaml, build device objects
- `get(device_id)` — return device config
- `list_all()` — return all registered devices with status
- `register(config_dict)` — add a new device at runtime, persist to YAML
- `unregister(device_id)` — remove device from registry

---

### Serial Handler — `serial_handler.py`

Controls all serial devices (Arduino, ESP32, any serial device).

- `discover()` — scan all COM ports, return list of active ports with device description
- `connect(port, baud)` — open serial connection, verify with ping
- `send_command(device_id, command, value)` — send formatted command string, return response
- `read_response(device_id, timeout)` — read until newline or timeout
- `disconnect(device_id)` — close connection cleanly

**Protocol**: T sends simple newline-terminated commands. Arduino sketch must follow this protocol:
```
T sends:  "DWRITE 13 HIGH\n"   → Arduino replies: "OK 13 HIGH\n"
T sends:  "DREAD 7\n"          → Arduino replies:  "OK 7 LOW\n"
T sends:  "AREAD A0\n"         → Arduino replies:  "OK A0 512\n"
T sends:  "DHT 2\n"            → Arduino replies:  "OK 22.5 61.0\n"  (temp, humidity)
T sends:  "PING\n"             → Arduino replies:  "PONG\n"
```
T provides a ready-to-flash Arduino sketch at `brain/hardware/arduino_sketch.ino`.

Auto-baud detection: if baud is not specified, T tries 9600 → 115200 → 57600 until `PING/PONG` succeeds.

---

### GPIO Handler — `gpio_handler.py`

For direct GPIO control (Raspberry Pi or similar Linux SBC).

- Detects if running on RPi via `/proc/cpuinfo`
- Uses `RPi.GPIO` if available, falls back to serial passthrough via Arduino
- `set_pin(pin, state)` → HIGH / LOW
- `read_pin(pin)` → HIGH / LOW
- `pwm(pin, frequency, duty_cycle)` → PWM output

If not on RPi, GPIO commands are forwarded to the registered serial device.

---

### MQTT Handler — `mqtt_handler.py`

Connects to any MQTT broker (local Mosquitto, Home Assistant, etc.).

- `connect(broker, port, user, password)` — establish MQTT connection
- `publish(topic, payload, qos)` — send a message
- `subscribe(topic, callback)` — listen for messages on a topic
- `disconnect()` — clean disconnect

Incoming MQTT messages matching a watched topic are forwarded to Tauri as:
```json
{"type": "hardware_event", "device_id": "bedroom_light", "topic": "...", "payload": "..."}
```
This allows T to report state changes proactively ("Bedroom light turned off").

---

### Command Router — `command_router.py`

Single entry point from engine.py.
Receives a hardware command, validates it against the device registry,
runs the safety check, shows confirmation if destructive, then executes.

```python
route(device_id, action, params) -> str
```

**Routing logic:**
- Lookup device in registry → get handler type (serial / gpio / mqtt)
- Pass to correct handler
- Receive response string
- Return formatted result

**Non-destructive** (no confirmation needed): read, status, ping, list
**Destructive** (YES required): write, set, send, publish, reset, power

---

### Safety — `safety.py`

Three hard rules enforced in code:

**1. Rate limiting** — no device can receive more than 10 commands per 10 seconds.
Any burst above this is rejected with an explanation. Prevents runaway loops.

**2. Pin blocklist** — certain pins are blocked from write operations entirely.
Default blocklist: pins 0, 1 (Arduino serial TX/RX — writing these breaks comms).
Abdul can add to blocklist via config.

**3. State validation** — before writing a value, T reads the current state.
If the device returns an unexpected state after write (within 500ms), T reports it.
Does not retry automatically — reports and lets Abdul decide.

---

### Natural Language Interface

T understands hardware commands from plain chat:
```
"turn on pin 13"           → DWRITE 13 HIGH to arduino_uno
"read temperature"         → DHT 2 to arduino_uno
"turn off bedroom light"   → publish "OFF" to home/bedroom/light/set
"what devices do I have"   → list_all() from registry
"scan for serial devices"  → discover() from serial_handler
"read pin A0"              → AREAD A0 to arduino_uno
```

Detection added to `engine.py` `_detect_integration()` — hardware commands route directly
without going through the LLM, same pattern as weather/search integrations.

---

### WebSocket Protocol Additions

```json
// Brain → Tauri
{"type": "hardware_result",  "device_id": "arduino_uno", "command": "DWRITE 13 HIGH", "response": "OK 13 HIGH"}
{"type": "hardware_event",   "device_id": "bedroom_light", "payload": "OFF"}
{"type": "hardware_error",   "device_id": "arduino_uno", "error": "Serial port not responding"}
{"type": "hardware_devices", "devices": [...]}   // response to list request
```

---

### New Settings Fields

`brain/config/hardware_devices.yaml` — device registry (file-based, human-readable)

New fields in SettingsPanel.tsx `Hardware` section:
- Default serial port scan on startup: on/off
- MQTT broker address + port + credentials (optional)
- Proactive MQTT event alerts: on/off (T notifies Abdul of incoming MQTT state changes)

---

### Arduino Sketch

`brain/hardware/arduino_sketch.ino` — ready-to-flash sketch implementing the T serial protocol.
Abdul flashes this once. T handles the rest.

Implements:
- `PING` / `PONG` handshake
- `DWRITE <pin> <HIGH|LOW>` — digital write
- `DREAD <pin>` — digital read
- `AREAD <pin>` — analog read (0–1023)
- `DHT <pin>` — read DHT11/DHT22 temperature + humidity
- `PWM <pin> <0-255>` — PWM output

---

### Dependencies to Add

```
pyserial>=3.5        ← serial port communication
paho-mqtt>=2.0.0     ← MQTT client
RPi.GPIO>=0.7.0; sys_platform == "linux"   ← Raspberry Pi GPIO (optional)
```

---

### Files to Build

- [ ] `brain/hardware/__init__.py`
- [ ] `brain/hardware/registry.py`
- [ ] `brain/hardware/serial_handler.py`
- [ ] `brain/hardware/gpio_handler.py`
- [ ] `brain/hardware/mqtt_handler.py`
- [ ] `brain/hardware/command_router.py`
- [ ] `brain/hardware/safety.py`
- [ ] `brain/hardware/arduino_sketch.ino`
- [ ] `brain/config/hardware_devices.yaml`
- [ ] `brain/core/engine.py` — add hardware intent detection + `hardware_command` message handler
- [ ] `brain/requirements.txt` — add pyserial, paho-mqtt, RPi.GPIO
- [ ] `src/hooks/useBridge.ts` — handle `hardware_result`, `hardware_event`, `hardware_error`, `hardware_devices`
- [ ] `src/components/settings/SettingsPanel.tsx` — add Hardware section

**Done when**: Abdul says "turn on pin 13" → T shows what it will do → Abdul types YES → Arduino pin 13 goes HIGH → T reports "OK 13 HIGH". And "read temperature" returns temp + humidity from DHT22 with no confirmation needed.

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

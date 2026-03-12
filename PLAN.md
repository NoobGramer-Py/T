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

- [ ] `brain/proactive/alerts.py` — time-based and condition-based alerts
- [ ] `brain/proactive/monitor.py` — system health, anomaly detection
- [ ] `brain/proactive/suggestions.py` — pattern learning, proactive nudges

**Done when**: T says "CPU has been at 95% for 10 minutes — process X is the culprit."

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

## Development Notes

- `node_modules/`, `src-tauri/target/`, `brain/data/` are gitignored
- All work is committed directly to `main` for now
- Commit format: `[phase] description` e.g. `[P1] add brain WebSocket server`

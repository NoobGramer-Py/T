# Project T — Phase Ω: Ultron Architecture Documentation

Welcome to **Project T**, an AI Operating System platform designed from the ground up for multi-device hosts, distributed intelligence, modular expansion, and strict user control.

---

## 1. Core Architecture Principles

1. **Explicit User Control**: High capability with strictly authorized execution (Permission enforcement, RBAC policies, security audit logs).
2. **Host & Hardware Agnostic**: PC is the primary host, but the architecture abstracts devices and networking to support future Robots, Drones, ESP32 Microcontrollers, Wearables, IoT, and Vehicles.
3. **Decoupled System Modules**: Every module communicates via typed interfaces or the asynchronous `EventBus`. Zero circular dependencies or monolithic coupling.
4. **Interchangeable AI Models**: Model providers (OpenAI, Anthropic, Ollama, Groq, local models) are managed through dynamic configuration and fallback routers.

---

## 2. Directory Structure

```
c:\Users\abdul\T\
├── brain/
│   ├── api/             ← REST HTTP API gateway & diagnostics endpoints
│   ├── automation/      ← Workflow trigger & event automation engine
│   ├── config/          ← Central system settings, env flags, policies
│   ├── conversation/    ← Context formatting & dialogue manager
│   ├── core/            ← System Kernel, EventBus, StateManager, HealthMonitor, LLMRouter
│   ├── devices/         ← Device Abstraction Layer (Robots, MCUs, Drones, Wearables)
│   ├── diagnostics/     ← System health probe & automated self-test runner
│   ├── execution/       ← Safe execution engine (authorized, interruptible, audited)
│   ├── knowledge/       ← Knowledge graph indexer & semantic nodes
│   ├── learning/        ← Preference collection & feedback ingestion hooks
│   ├── logging/         ← Structured JSON logger & trace context
│   ├── memory/          ← Multi-tier memory (Short-term, Working, Long-term, Preferences)
│   ├── networking/      ← Multi-host node messaging & RPC protocol
│   ├── planning/        ← Task plan step graph generator (DAG)
│   ├── plugins/         ← Dynamic plugin registry & interface contracts
│   ├── reasoning/       ← Cognitive decision engine (decoupled from dialogue)
│   ├── scheduler/       ← One-shot & delayed task scheduler
│   ├── security/        ← Permission enforcement, policy evaluator, audit logger
│   ├── simulation/      ← Action execution dry-run sandbox
│   ├── skills/          ← Tool & skill registry wrapper
│   ├── telemetry/       ← System counters, uptime, latency metrics
│   ├── tests/           ← Automated unittest test suite
│   ├── vision/          ← Multimodal visual perception frame handler
│   ├── voice/           ← Audio STT (Whisper) & TTS (Kokoro) pipeline
│   └── main.py          ← Brain server startup entry point
├── src/                 ← React / TypeScript frontend (Tauri HUD)
├── src-tauri/           ← Rust backend for Tauri desktop app
├── PLAN.md              ← Execution plan
└── DOCUMENTATION.md     ← System Architecture & Developer Guide
```

---

## 3. Subsystem Module Breakdown

### Core Kernel (`brain/core/`)
- `engine.py` (`SystemKernel`): Central brain orchestrating module boot, query processing pipelines, and event dispatches.
- `event_bus.py` (`EventBus`): Asynchronous publish-subscribe event router.
- `state_manager.py` (`StateManager`): Central state store with real-time change notifications.
- `health_monitor.py` (`HealthMonitor`): Subsystem heartbeat and readiness tracker.
- `module_loader.py` (`ModuleLoader`): Dynamic module registration and lifecycle coordinator.
- `llm.py` (`LLMRouter`): Provider-agnostic AI model router.

### Memory (`brain/memory/`)
- `short_term.py`: Transient dialogue message history context window.
- `working_memory.py`: Scratchpad variables during active task execution.
- `long_term.py`: Persistent document store & semantic search interface.
- `preferences.py`: User preference store and system defaults.

### Reasoning & Planning (`brain/reasoning/`, `brain/planning/`)
- `reasoning/engine.py`: Deliberative cognitive engine generating decisions (`Decision`) independent of natural language outputs.
- `planning/planner.py`: Multi-step DAG task plan decomposition engine (`TaskPlan`).

### Execution & Security (`brain/execution/`, `brain/security/`, `brain/simulation/`)
- `security/permission_manager.py`: Policy evaluator enforcing authorization checks.
- `security/audit.py`: Immutable JSON audit logger for sensitive actions.
- `simulation/sandbox.py`: Action dry-run validation simulator.
- `execution/runner.py`: Safe execution engine executing authorized actions.

### Device Abstraction Layer (`brain/devices/`)
- `types.py` & `base.py`: Abstraction contracts for abstract hardware hosts (Robots, Drones, Microcontrollers/ESP32, Wearables, Cameras, Microphones, Displays, IoT, Vehicles).
- `registry.py`: Central registry tracking hardware device metadata and telemetry.

### Networking Subsystem (`brain/networking/`)
- `node.py`: OS node specification representing host instances.
- `bus.py`: Inter-node RPC and event propagation network protocol.

### Plugins Subsystem (`brain/plugins/`)
- `plugin_base.py`: Standard plugin contract (`AbstractPlugin`).
- `registry.py`: Dynamic plugin registration and execution manager.

---

## 4. Developer Plugin Onboarding Guide

To create a new capability plugin without modifying Core:

1. Create a class extending `AbstractPlugin`:
```python
from brain.plugins.plugin_base import AbstractPlugin

class WeatherPlugin(AbstractPlugin):
    name = "weather_plugin"
    version = "1.0.0"
    description = "Provides live weather telemetry."

    async def initialize(self) -> None:
        pass

    async def execute(self, action: str, params: dict) -> dict:
        return {"temperature": 72, "unit": "F"}

    async def shutdown(self) -> None:
        pass
```

2. Register the plugin with `plugin_registry`:
```python
from brain.plugins.registry import plugin_registry

await plugin_registry.register_plugin(WeatherPlugin())
```

---

## 5. Verification & Testing

Run the automated system unit test battery:
```bash
python -m unittest discover -s brain/tests
```

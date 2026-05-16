import { useEffect, useRef, useCallback, useState } from "react";
import { bridge, type BrainStatus, type BrainMessage } from "../lib/bridge";
import { useTStore } from "../store";

// Starts the bridge connection once and keeps it alive for the app lifetime.
export function useBrainConnection(): void {
  const { setVisualizerMode } = useTStore();

  useEffect(() => {
    bridge.connect();

    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type === "visualizer") {
        const mode = msg.mode as "idle" | "listening" | "speaking";
        if (mode === "idle" || mode === "listening" || mode === "speaking") {
          setVisualizerMode(mode);
        }
      }
    });

    return unsub;
  }, [setVisualizerMode]);
}

// Handles push-to-talk voice via brain pipeline.
// Returns { startPTT, stopPTT, playAudio } — all stable references.
export function useBrainVoice() {
  const { setVoiceListening, setVisualizerMode, voiceEnabled } = useTStore();
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Sync voice_enable state to brain when voiceEnabled changes
  useEffect(() => {
    if (bridge.getStatus() !== "online") return;
    bridge.send({ type: "voice_enable", enabled: voiceEnabled });
  }, [voiceEnabled]);

  // Also send voice_enable when brain comes online
  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type === "brain_status" && msg.online === true) {
        bridge.send({ type: "voice_enable", enabled: voiceEnabled });
      }
    });
    return unsub;
  }, [voiceEnabled]);

  // Handle incoming TTS audio from brain
  useEffect(() => {
    const unsub = bridge.onMessage(async (msg: BrainMessage) => {
      if (msg.type !== "tts_audio") return;
      try {
        const b64   = msg.audio as string;
        const sr    = msg.sample_rate as number;
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

        if (!audioCtxRef.current) {
          audioCtxRef.current = new AudioContext({ sampleRate: sr });
        }
        const ctx = audioCtxRef.current;

        // Resume context if suspended (browser autoplay policy)
        if (ctx.state === "suspended") {
          await ctx.resume();
        }

        const buffer = await ctx.decodeAudioData(bytes.buffer);
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(ctx.destination);
        source.onended = () => setVisualizerMode("idle");
        source.start();
        setVisualizerMode("speaking");
      } catch (e) {
        console.error("[voice] tts_audio decode error", e);
      }
    });
    return unsub;
  }, [setVisualizerMode]);

  const startPTT = useCallback(() => {
    if (bridge.getStatus() !== "online") return;
    bridge.send({ type: "voice_start" });
    setVoiceListening(true);
  }, [setVoiceListening]);

  const stopPTT = useCallback(() => {
    if (bridge.getStatus() !== "online") return;
    bridge.send({ type: "voice_stop" });
    setVoiceListening(false);
  }, [setVoiceListening]);

  return { startPTT, stopPTT };
}

// Returns the current brain connection status.
export function useBrainStatus(): BrainStatus {
  const [status, setStatus] = useState<BrainStatus>(bridge.getStatus());

  useEffect(() => {
    const unsub = bridge.onStatus(setStatus);
    setStatus(bridge.getStatus());
    return unsub;
  }, []);

  return status;
}

// Sends a chat message through the brain.
// Returns streaming chunks via onChunk, final done signal via onDone,
// and error via onError.
// Falls back to direct AI if brain is offline.
export function useBrainChat() {
  const pendingRef = useRef<Map<string, {
    onChunk:    (chunk: string) => void;
    onDone:     (provider: string) => void;
    onError:    (err: string) => void;
  }>>(new Map());

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      const id = msg.id as string | undefined;
      if (!id) return;
      const pending = pendingRef.current.get(id);
      if (!pending) return;

      if (msg.type === "chat_chunk") {
        pending.onChunk(msg.chunk as string);
      } else if (msg.type === "chat_done") {
        pending.onDone((msg.provider as string) ?? "groq");
        pendingRef.current.delete(id);
      } else if (msg.type === "chat_error") {
        pending.onError(msg.error as string);
        pendingRef.current.delete(id);
      }
    });
    return unsub;
  }, []);

  const send = useCallback((
    id:      string,
    content: string,
    onChunk: (chunk: string) => void,
    onDone:  (provider: string) => void,
    onError: (err: string) => void,
  ): boolean => {
    const sent = bridge.send({ type: "chat", id, content });
    if (sent) {
      pendingRef.current.set(id, { onChunk, onDone, onError });
    }
    return sent;
  }, []);

  return { send };
}

// Syncs Tauri profile data to the brain whenever the profile changes.
export function useBrainProfileSync(): void {
  const profile = useTStore((s) => s.profile);
  const statusRef = useRef<BrainStatus>(bridge.getStatus());

  useEffect(() => {
    const unsub = bridge.onStatus((s) => { statusRef.current = s; });
    return unsub;
  }, []);

  useEffect(() => {
    if (statusRef.current !== "online") return;
    bridge.send({ type: "profile_sync", data: profile });
  }, [profile]);

  // Also sync immediately when brain first comes online
  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type === "brain_status" && msg.online === true) {
        bridge.send({ type: "profile_sync", data: profile });
      }
    });
    return unsub;
  }, [profile]);
}

// Listens for memory_saved events from the brain and adds them to the store.
export function useBrainMemory(): void {
  const { addBrainMemory } = useTStore();

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type === "memory_saved") {
        addBrainMemory(
          msg.key   as string,
          msg.value as string,
        );
      }
    });
    return unsub;
  }, [addBrainMemory]);
}

// Sends an agent task and streams back step events.
export function useAgent() {
  type AgentEvent = {
    type:    string;
    step?:   number;
    text?:   string;
    tool?:   string;
    params?: Record<string, string>;
    result?: string;
    answer?: string;
    error?:  string;
    message?: string;
  };

  const dispatch = useCallback((
    task:     string,
    onEvent:  (e: AgentEvent) => void,
  ): boolean => {
    const id   = crypto.randomUUID();
    const sent = bridge.send({ type: "agent", id, task });
    if (!sent) return false;

    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.id !== id) return;
      const e: AgentEvent = { type: msg.type };
      if (msg.step)    e.step    = msg.step   as number;
      if (msg.text)    e.text    = msg.text   as string;
      if (msg.tool)    e.tool    = msg.tool   as string;
      if (msg.params)  e.params  = msg.params as Record<string, string>;
      if (msg.result)  e.result  = msg.result as string;
      if (msg.answer)  e.answer  = msg.answer as string;
      if (msg.error)   e.error   = msg.error  as string;
      if (msg.message) e.message = msg.message as string;
      onEvent(e);
      if (msg.type === "agent_done" || msg.type === "agent_error") {
        unsub();
      }
    });

    return true;
  }, []);

  const confirm = useCallback((confirmed: boolean) => {
    bridge.send({ type: "agent_confirm_response", confirmed });
  }, []);

  return { dispatch, confirm };
}

// ─── Proactive Alerts ─────────────────────────────────────────────────────────
// Surfaces alerts pushed by the proactive engine (system health, reminders).

export type ProactiveAlert = {
  severity: "info" | "warn" | "critical";
  message:  string;
  ts:       number;
};

export function useProactiveAlerts() {
  const [alerts, setAlerts] = useState<ProactiveAlert[]>([]);

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type !== "proactive_alert") return;
      setAlerts((prev) => [
        { severity: msg.severity as ProactiveAlert["severity"], message: msg.message as string, ts: Date.now() },
        ...prev.slice(0, 49),   // keep last 50
      ]);
    });
    return unsub;
  }, []);

  const dismiss = useCallback((ts: number) => {
    setAlerts((prev) => prev.filter((a) => a.ts !== ts));
  }, []);

  return { alerts, dismiss };
}

// ─── Local Access ─────────────────────────────────────────────────────────────
// Manages the local credential extraction session lifecycle.

export type LocalAccessProgress = {
  source: string;
  status: "running" | "done" | "fallback" | "failed";
  error?: string;
};

export type LocalAccessState =
  | "idle"
  | "checking"
  | "awaiting_confirm"
  | "elevating"
  | "running"
  | "done"
  | "error";

export function useLocalAccess() {
  const [state,        setState]        = useState<LocalAccessState>("idle");
  const [readyPayload, setReadyPayload] = useState<BrainMessage | null>(null);
  const [progress,     setProgress]     = useState<LocalAccessProgress[]>([]);
  const [fullOutput,   setFullOutput]   = useState<string>("");
  const [hashes,       setHashes]       = useState<string[]>([]);
  const [summary,      setSummary]      = useState<string>("");
  const [error,        setError]        = useState<string>("");
  const [memoryResult, setMemoryResult] = useState<object | null>(null);

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "local_access_ready":
          setState("awaiting_confirm");
          setReadyPayload(msg);
          setProgress([]);
          break;
        case "local_access_progress":
          setProgress((prev) => {
            const idx = prev.findIndex((p) => p.source === msg.source);
            const entry: LocalAccessProgress = {
              source: msg.source as string,
              status: msg.status as LocalAccessProgress["status"],
              error:  msg.error as string | undefined,
            };
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = entry;
              return next;
            }
            return [...prev, entry];
          });
          if (msg.status === "waiting_for_helper") setState("elevating");
          if (msg.status === "running")             setState("running");
          break;
        case "local_access_summary":
          setSummary(msg.chat_summary as string);
          setState("done");
          break;
        case "local_access_full":
          setFullOutput(msg.data as string);
          break;
        case "local_access_hashes":
          setHashes(msg.hashes as string[]);
          break;
        case "local_access_ended":
          setState("idle");
          setProgress([]);
          break;
        case "local_access_cancelled":
          setState("idle");
          break;
        case "local_access_error":
          setError(msg.error as string);
          setState("error");
          break;
        case "memory_inspect_result":
          setMemoryResult(msg.result as object ?? msg.results as object);
          break;
      }
    });
    return unsub;
  }, []);

  const startSession = useCallback(() => {
    setState("checking");
    setError("");
    setFullOutput("");
    setHashes([]);
    setSummary("");
    setProgress([]);
    bridge.send({ type: "local_access_start", id: crypto.randomUUID() });
  }, []);

  const confirm = useCallback(() => {
    bridge.send({ type: "local_access_confirm", confirmed: true });
  }, []);

  const cancel = useCallback(() => {
    bridge.send({ type: "local_access_confirm", confirmed: false });
    setState("idle");
  }, []);

  const endSession = useCallback(() => {
    bridge.send({ type: "local_access_end" });
  }, []);

  const inspectMemory = useCallback((pid: number | null, patterns?: string[]) => {
    bridge.send({ type: "memory_inspect", id: crypto.randomUUID(), pid, patterns });
  }, []);

  return {
    state, readyPayload, progress, fullOutput, hashes,
    summary, error, memoryResult,
    startSession, confirm, cancel, endSession, inspectMemory,
  };
}

// ─── Hardware ─────────────────────────────────────────────────────────────────

export type HardwareDevice = {
  id:           string;
  type:         "serial" | "mqtt" | "gpio";
  description:  string;
  capabilities: string[];
  connected:    boolean;
};

export type HardwareResult = {
  device_id: string;
  action:    string;
  result:    string;
  ts:        number;
};

export type HardwareConfirmRequest = {
  device_id: string;
  action:    string;
  detail:    string;
  message:   string;
};

export function useHardware() {
  const [devices,        setDevices]        = useState<HardwareDevice[]>([]);
  const [results,        setResults]        = useState<HardwareResult[]>([]);
  const [error,          setError]          = useState<string>("");
  const [confirmRequest, setConfirmRequest] = useState<HardwareConfirmRequest | null>(null);
  const [serialPorts,    setSerialPorts]    = useState<{ port: string; description: string }[]>([]);

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "hardware_devices":
          setDevices((msg.devices as HardwareDevice[]) ?? []);
          if (msg.serial_ports) {
            setSerialPorts(msg.serial_ports as { port: string; description: string }[]);
          }
          break;
        case "hardware_result":
          setResults((prev) => [
            {
              device_id: msg.device_id as string,
              action:    msg.action    as string ?? "",
              result:    msg.result   as string,
              ts:        Date.now(),
            },
            ...prev.slice(0, 99),
          ]);
          setError("");
          break;
        case "hardware_error":
          setError(msg.error as string);
          break;
        case "hardware_confirm":
          setConfirmRequest({
            device_id: msg.device_id as string,
            action:    msg.action    as string,
            detail:    msg.detail    as string,
            message:   msg.message   as string,
          });
          break;
        case "hardware_event":
          setResults((prev) => [
            {
              device_id: msg.device_id as string,
              action:    `event:${msg.topic as string ?? ""}`,
              result:    msg.payload   as string,
              ts:        Date.now(),
            },
            ...prev.slice(0, 99),
          ]);
          break;
      }
    });
    return unsub;
  }, []);

  const sendCommand = useCallback((device_id: string, action: string, params: Record<string, string | number> = {}) => {
    bridge.send({ type: "hardware_command", device_id, action, params });
  }, []);

  const listDevices = useCallback(() => {
    bridge.send({ type: "hardware_command", action: "list", device_id: "" });
  }, []);

  const discoverPorts = useCallback(() => {
    bridge.send({ type: "hardware_command", action: "discover", device_id: "" });
  }, []);

  const connectDevice = useCallback((device_id: string, port?: string, baud?: number) => {
    const params: Record<string, string | number> = {};
    if (port) params.port = port;
    if (baud) params.baud = baud;
    bridge.send({ type: "hardware_command", action: "connect", device_id, params });
  }, []);

  const registerDevice = useCallback((config: Record<string, unknown>) => {
    bridge.send({ type: "hardware_command", action: "register", device_id: "", config });
  }, []);

  const unregisterDevice = useCallback((device_id: string) => {
    bridge.send({ type: "hardware_command", action: "unregister", device_id });
  }, []);

  const confirmAction = useCallback((confirmed: boolean) => {
    bridge.send({ type: "hardware_confirm", confirmed });
    setConfirmRequest(null);
  }, []);

  const clearError = useCallback(() => setError(""), []);

  return {
    devices, results, error, confirmRequest, serialPorts,
    sendCommand, listDevices, discoverPorts, connectDevice,
    registerDevice, unregisterDevice, confirmAction, clearError,
  };
}

// ─── Offensive / VM ───────────────────────────────────────────────────────────

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type OffensiveConfirmRequest = {
  id:          string;
  tool:        string;
  command:     string;
  description: string;
  risk:        RiskLevel;
};

export type OffensiveStreamLine = {
  id:    string;
  tool:  string;
  chunk: string;
  ts:    number;
};

export type ToolMissing = {
  id:          string;
  tool:        string;
  install_cmd: string;
};

export type VmStatus = {
  running:  boolean;
  ssh_ok:   boolean;
  vm_ip:    string;
  vm_name:  string;
  message?: string;
};

export type VmToolsStatus = Record<string, boolean>;

export function useOffensive() {
  const [confirmReq,   setConfirmReq]   = useState<OffensiveConfirmRequest | null>(null);
  const [streamLines,  setStreamLines]  = useState<OffensiveStreamLine[]>([]);
  const [toolMissing,  setToolMissing]  = useState<ToolMissing | null>(null);
  const [lastDone,     setLastDone]     = useState<{ id: string; tool: string; cancelled?: boolean } | null>(null);
  const [error,        setError]        = useState<string>("");

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "offensive_confirm_request":
          setConfirmReq({
            id:          msg.id          as string,
            tool:        msg.tool        as string,
            command:     msg.command     as string,
            description: msg.description as string,
            risk:        msg.risk        as RiskLevel,
          });
          break;
        case "offensive_stream":
          setStreamLines(prev => [
            ...prev,
            { id: msg.id as string, tool: msg.tool as string, chunk: msg.chunk as string, ts: Date.now() },
          ].slice(-2000));   // keep last 2000 lines
          break;
        case "offensive_done":
          setConfirmReq(null);
          setLastDone({ id: msg.id as string, tool: msg.tool as string, cancelled: msg.cancelled as boolean | undefined });
          break;
        case "offensive_error":
          setError(msg.error as string);
          setConfirmReq(null);
          break;
        case "tool_missing":
          setToolMissing({ id: msg.id as string, tool: msg.tool as string, install_cmd: msg.install_cmd as string });
          break;
      }
    });
    return unsub;
  }, []);

  const dispatch = useCallback((tool: string, params: Record<string, unknown> = {}, commandOverride?: string) => {
    const id = crypto.randomUUID();
    bridge.send({ type: "offensive_action", id, tool, params, command_override: commandOverride ?? "" });
    return id;
  }, []);

  const confirm = useCallback((id: string, confirmed: boolean) => {
    bridge.send({ type: "offensive_confirm", id, confirmed });
    if (!confirmed) setConfirmReq(null);
  }, []);

  const installTool = useCallback((tool: string) => {
    const id = crypto.randomUUID();
    bridge.send({ type: "tool_install", id, tool });
    setToolMissing(null);
    return id;
  }, []);

  const clearStream = useCallback((id?: string) => {
    setStreamLines(prev => id ? prev.filter(l => l.id !== id) : []);
  }, []);

  const clearError = useCallback(() => setError(""), []);

  return {
    confirmReq, streamLines, toolMissing, lastDone, error,
    dispatch, confirm, installTool, clearStream, clearError,
  };
}

export function useVmStatus() {
  const [status,     setStatus]     = useState<VmStatus | null>(null);
  const [toolStatus, setToolStatus] = useState<VmToolsStatus>({});
  const [loading,    setLoading]    = useState(false);

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type === "vm_status") {
        setStatus({
          running:  (msg.running  as boolean) ?? false,
          ssh_ok:   (msg.ssh_ok   as boolean) ?? false,
          vm_ip:    (msg.vm_ip    as string)  ?? "",
          vm_name:  (msg.vm_name  as string)  ?? "",
          message:  msg.message as string | undefined,
        });
        setLoading(false);
      }
      if (msg.type === "vm_tools_status") {
        setToolStatus(msg.tools as VmToolsStatus);
      }
    });
    return unsub;
  }, []);

  const refresh = useCallback(() => {
    setLoading(true);
    bridge.send({ type: "vm_command", action: "status" });
  }, []);

  const start = useCallback(() => {
    setLoading(true);
    bridge.send({ type: "vm_command", action: "start" });
  }, []);

  const stop = useCallback(() => {
    setLoading(true);
    bridge.send({ type: "vm_command", action: "stop" });
  }, []);

  const snapshot = useCallback((name: string) => {
    bridge.send({ type: "vm_command", action: "snapshot", snapshot_name: name });
  }, []);

  const restore = useCallback((name: string) => {
    bridge.send({ type: "vm_command", action: "restore", snapshot_name: name });
  }, []);

  const checkTools = useCallback((tools: string[]) => {
    bridge.send({ type: "vm_check_tools", tools });
  }, []);

  return { status, toolStatus, loading, refresh, start, stop, snapshot, restore, checkTools };
}

// ─── Devices (Phase 9) ────────────────────────────────────────────────────────

export type DeviceConfirmRequest = {
  id:          string;
  action:      string;
  command:     string;
  description: string;
  risk:        RiskLevel;
};

export type AdbDevice = {
  serial: string;
  state:  string;
  info:   string;
};

export function useDevices() {
  const [confirmReq,  setConfirmReq]  = useState<DeviceConfirmRequest | null>(null);
  const [streamLines, setStreamLines] = useState<{ id: string; action: string; chunk: string; ts: number }[]>([]);
  const [adbDevices,  setAdbDevices]  = useState<AdbDevice[]>([]);
  const [error,       setError]       = useState<string>("");
  const [lastDone,    setLastDone]    = useState<{ id: string; action: string } | null>(null);

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "device_confirm_request":
          setConfirmReq({
            id:          msg.id          as string,
            action:      msg.action      as string,
            command:     msg.command     as string,
            description: msg.description as string,
            risk:        msg.risk        as RiskLevel,
          });
          break;
        case "device_stream":
          setStreamLines(prev => [
            ...prev,
            { id: msg.id as string, action: msg.action as string, chunk: msg.chunk as string, ts: Date.now() },
          ].slice(-2000));
          break;
        case "device_done":
          setConfirmReq(null);
          setLastDone({ id: msg.id as string, action: msg.action as string });
          break;
        case "device_error":
          setError(msg.error as string);
          setConfirmReq(null);
          break;
        case "adb_devices":
          setAdbDevices((msg.devices as AdbDevice[]) ?? []);
          break;
      }
    });
    return unsub;
  }, []);

  const dispatch = useCallback((action: string, params: Record<string, unknown> = {}) => {
    const id = crypto.randomUUID();
    bridge.send({ type: "device_action", id, action, params });
    return id;
  }, []);

  const confirm = useCallback((id: string, confirmed: boolean) => {
    bridge.send({ type: "device_confirm", id, confirmed });
    if (!confirmed) setConfirmReq(null);
  }, []);

  const listAdb = useCallback(() => {
    bridge.send({ type: "adb_list" });
  }, []);

  const clearStream = useCallback((id?: string) => {
    setStreamLines(prev => id ? prev.filter(l => l.id !== id) : []);
  }, []);

  const clearError = useCallback(() => setError(""), []);

  return {
    confirmReq, streamLines, adbDevices, error, lastDone,
    dispatch, confirm, listAdb, clearStream, clearError,
  };
}

// ─── Lab (Phase 10) ───────────────────────────────────────────────────────────

export type LabStepStatus = "pending" | "running" | "done" | "failed" | "skipped";

export type LabStep = {
  id:      string;
  status:  LabStepStatus;
  message: string;
};

export type LabDevice = {
  ip:          string;
  mac:         string;
  hostname:    string;
  os_hint:     string;
  device_type: string;
  open_ports:  number[];
  services:    { port: number; service: string; version: string }[];
  phase:       string;
};

export type LabCred = {
  ts:         string;
  ip:         string;
  username:   string;
  password:   string;
  user_agent: string;
};

export type RatResult = {
  action:     string;
  media_type?: "image" | "audio";
  b64?:       string;
  path?:      string;
  data?:      string;
  lat?:       string;
  lon?:       string;
  error?:     string;
  ts?:        number;
  count?:     number;
  size_kb?:   number;
};

const LAB_STEPS = ["recon","router","pivot","payload","phishing","ducky","post_exploit","report"];

export function useLab() {
  const [active,        setActive]        = useState(false);
  const [steps,         setSteps]         = useState<Record<string, LabStep>>(() =>
    Object.fromEntries(LAB_STEPS.map(id => [id, { id, status: "pending", message: "" }]))
  );
  const [devices,       setDevices]       = useState<LabDevice[]>([]);
  const [creds,         setCreds]         = useState<LabCred[]>([]);
  const [streamLines,   setStreamLines]   = useState<{ step: string; chunk: string; ts: number }[]>([]);
  const [sessionOpen,   setSessionOpen]   = useState(false);
  const [ratResults,    setRatResults]    = useState<RatResult[]>([]);
  const [reportHtml,    setReportHtml]    = useState("");
  const [reportReady,   setReportReady]   = useState(false);
  const [error,         setError]         = useState("");

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "lab_status":
          setActive(msg.active as boolean);
          if (!(msg.active as boolean)) setSessionOpen(false);
          break;
        case "lab_step_update":
          setSteps(prev => ({
            ...prev,
            [msg.step as string]: {
              id:      msg.step as string,
              status:  msg.status as LabStepStatus,
              message: msg.message as string,
            },
          }));
          break;
        case "lab_device_found":
          setDevices(prev => {
            const ip = msg.ip as string;
            const idx = prev.findIndex(d => d.ip === ip);
            const dev: LabDevice = {
              ip,
              mac:         (msg.mac         as string) ?? "",
              hostname:    (msg.hostname    as string) ?? "",
              os_hint:     (msg.os_hint     as string) ?? "",
              device_type: (msg.device_type as string) ?? "unknown",
              open_ports:  (msg.open_ports  as number[]) ?? [],
              services:    (msg.services    as LabDevice["services"]) ?? [],
              phase:       (msg.phase       as string) ?? "",
            };
            if (idx >= 0) { const n = [...prev]; n[idx] = { ...n[idx], ...dev }; return n; }
            return [...prev, dev];
          });
          break;
        case "lab_cred_captured":
          setCreds(prev => [{
            ts:         msg.ts         as string,
            ip:         msg.ip         as string,
            username:   msg.username   as string,
            password:   msg.password   as string,
            user_agent: msg.user_agent as string,
          }, ...prev]);
          break;
        case "lab_stream":
          setStreamLines(prev => [
            ...prev,
            { step: msg.step as string, chunk: msg.chunk as string, ts: Date.now() },
          ].slice(-1000));
          break;
        case "lab_session_opened":
          setSessionOpen(true);
          break;
        case "lab_rat_result":
          setRatResults(prev => [{
            action:     msg.action     as string,
            media_type: msg.media_type as "image" | "audio" | undefined,
            b64:        msg.b64        as string | undefined,
            path:       msg.path       as string | undefined,
            data:       msg.data       as string | undefined,
            lat:        msg.lat        as string | undefined,
            lon:        msg.lon        as string | undefined,
            error:      msg.error      as string | undefined,
            ts:         msg.ts         as number | undefined,
            count:      msg.count      as number | undefined,
            size_kb:    msg.size_kb    as number | undefined,
          }, ...prev].slice(0, 50));
          break;
        case "lab_report_ready":
          setReportHtml(msg.html as string);
          setReportReady(true);
          setActive(false);
          break;
        case "lab_error":
          setError(msg.error as string);
          break;
      }
    });
    return unsub;
  }, []);

  const startLab = useCallback((config: Record<string, unknown>) => {
    setDevices([]); setCreds([]); setStreamLines([]);
    setRatResults([]); setReportHtml(""); setReportReady(false); setError("");
    setSteps(Object.fromEntries(LAB_STEPS.map(id => [id, { id, status: "pending", message: "" }])));
    bridge.send({ type: "lab_start", ...config });
  }, []);

  const stopLab = useCallback(() => {
    bridge.send({ type: "lab_stop" });
  }, []);

  const ratAction = useCallback((action: string, params: Record<string, unknown> = {}, session = "1") => {
    bridge.send({ type: "lab_rat_action", action, session, params });
  }, []);

  const stopPhishing = useCallback(() => {
    bridge.send({ type: "lab_phish_stop" });
  }, []);

  const clearError = useCallback(() => setError(""), []);

  return {
    active, steps, devices, creds, streamLines, sessionOpen,
    ratResults, reportHtml, reportReady, error,
    startLab, stopLab, ratAction, stopPhishing, clearError,
  };
}

// ─── Ops Session (real-world targets) ─────────────────────────────────────────

export type OpsTarget = {
  id:          string;
  type:        "ip" | "domain" | "bugbounty" | "ctf" | "custom";
  value:       string;
  scope_notes: string;
  program_url: string;
};

export type OpsSession = {
  id:            string;
  name:          string;
  active:        boolean;
  notes:         string;
  started:       number;
  targets:       OpsTarget[];
  finding_count: number;
  log_count:     number;
};

export type OpsReconLine = {
  step:   string;
  chunk:  string;
  target: string;
  ts:     number;
};

export function useOps() {
  const [session,    setSession]    = useState<OpsSession | null>(null);
  const [reconLines, setReconLines] = useState<OpsReconLine[]>([]);
  const [reconStep,  setReconStep]  = useState("");
  const [reconDone,  setReconDone]  = useState(false);
  const [error,      setError]      = useState("");

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "ops_session":
          setSession(msg.session as OpsSession);
          break;
        case "ops_recon_start":
          setReconLines([]); setReconDone(false);
          break;
        case "ops_recon_step":
          setReconStep(msg.step as string);
          break;
        case "ops_recon_chunk":
          setReconLines(prev => [
            ...prev,
            { step: msg.step as string, chunk: msg.chunk as string,
              target: msg.target as string, ts: Date.now() },
          ].slice(-1000));
          break;
        case "ops_recon_done":
          setReconDone(true);
          setSession(msg.session as OpsSession);
          break;
        case "ops_recon_error":
          setError(msg.error as string);
          break;
      }
    });
    return unsub;
  }, []);

  const createSession = useCallback((name: string, notes = "") => {
    bridge.send({ type: "ops_session_create", name, notes });
  }, []);

  const addTarget = useCallback((
    target_type: string, value: string,
    scope_notes = "", program_url = ""
  ) => {
    bridge.send({ type: "ops_target_add", target_type, value, scope_notes, program_url });
  }, []);

  const removeTarget = useCallback((target_id: string) => {
    bridge.send({ type: "ops_target_remove", target_id });
  }, []);

  const autoRecon = useCallback((target: string) => {
    setReconLines([]); setReconDone(false);
    bridge.send({ type: "ops_auto_recon", target });
  }, []);

  const clearError = useCallback(() => setError(""), []);

  return {
    session, reconLines, reconStep, reconDone, error,
    createSession, addTarget, removeTarget, autoRecon, clearError,
  };
}

// ─── Intel (Phase 11) ─────────────────────────────────────────────────────────

export type IntelConfirmRequest = {
  id:          string;
  action:      string;
  command:     string;
  description: string;
  risk:        RiskLevel;
};

export type GraphNode = {
  id:     string;
  type:   string;
  label:  string;
  detail: string;
  color:  string;
  risk:   string;
  ts:     number;
};

export type GraphEdge = {
  source: string;
  target: string;
  label:  string;
  weight: number;
};

export type IntelGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export function useIntel() {
  const [confirmReq,  setConfirmReq]  = useState<IntelConfirmRequest | null>(null);
  const [streamLines, setStreamLines] = useState<{ id: string; action: string; chunk: string; ts: number }[]>([]);
  const [graph,       setGraph]       = useState<IntelGraph>({ nodes: [], edges: [] });
  const [lastDone,    setLastDone]    = useState<{ id: string; action: string; duration: number } | null>(null);
  const [error,       setError]       = useState("");

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "intel_confirm_request":
          setConfirmReq({
            id:          msg.id          as string,
            action:      msg.action      as string,
            command:     msg.command     as string,
            description: msg.description as string,
            risk:        msg.risk        as RiskLevel,
          });
          break;
        case "intel_stream":
          setStreamLines(prev => [
            ...prev,
            { id: msg.id as string, action: msg.action as string,
              chunk: msg.chunk as string, ts: Date.now() },
          ].slice(-3000));
          break;
        case "intel_done":
          setConfirmReq(null);
          setLastDone({ id: msg.id as string, action: msg.action as string,
                        duration: msg.duration as number });
          if (msg.graph) setGraph(msg.graph as IntelGraph);
          break;
        case "intel_graph":
          setGraph(msg.graph as IntelGraph);
          break;
        case "intel_error":
          setError(msg.error as string);
          setConfirmReq(null);
          break;
      }
    });
    return unsub;
  }, []);

  const dispatch = useCallback((action: string, params: Record<string, unknown> = {}) => {
    const id = crypto.randomUUID();
    bridge.send({ type: "intel_action", id, action, params });
    return id;
  }, []);

  const confirm = useCallback((id: string, confirmed: boolean) => {
    bridge.send({ type: "intel_confirm", id, confirmed });
    if (!confirmed) setConfirmReq(null);
  }, []);

  const getGraph  = useCallback(() => { bridge.send({ type: "intel_graph_get" }); }, []);
  const resetGraph = useCallback(() => { bridge.send({ type: "intel_graph_reset" }); setGraph({ nodes: [], edges: [] }); }, []);
  const clearStream = useCallback(() => setStreamLines([]), []);
  const clearError  = useCallback(() => setError(""), []);

  return {
    confirmReq, streamLines, graph, lastDone, error,
    dispatch, confirm, getGraph, resetGraph, clearStream, clearError,
  };
}

// ─── Autonomous (Phase 12) ────────────────────────────────────────────────────

export type AutoStepStatus = "pending" | "running" | "done" | "error" | "skipped";

export type AutoStep = {
  step:     string;
  tool:     string;
  status:   AutoStepStatus;
  summary:  string;
  duration: number;
  step_n:   number;
};

export type AutoConfirmRequest = {
  id:     string;
  step:   string;
  tool:   string;
  reason: string;
  risk:   "HIGH" | "CRITICAL";
};

export type AutoMemory = {
  goal:      string;
  target:    string;
  task_type: string;
  elapsed:   number;
  steps:     { name: string; tool: string; status: string; summary: string }[];
  hosts:     string[];
  open_ports: Record<string, number[]>;
  creds:     number;
  flags:     string[];
  vulns:     number;
  subdomains: number;
  emails:    number;
  social:    number;
  breach:    number;
  sessions:  string[];
};

export function useAutonomous() {
  const [running,     setRunning]     = useState(false);
  const [steps,       setSteps]       = useState<AutoStep[]>([]);
  const [confirmReq,  setConfirmReq]  = useState<AutoConfirmRequest | null>(null);
  const [memory,      setMemory]      = useState<AutoMemory | null>(null);
  const [reportPath,  setReportPath]  = useState("");
  const [reportDone,  setReportDone]  = useState(false);
  const [summary,     setSummary]     = useState("");
  const [error,       setError]       = useState("");
  const [taskId,      setTaskId]      = useState("");

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "auto_started":
          setRunning(true); setSteps([]); setReportDone(false);
          setSummary(""); setError(""); setMemory(null);
          break;

        case "auto_step": {
          const s: AutoStep = {
            step:     msg.step     as string,
            tool:     msg.tool     as string,
            status:   msg.status   as AutoStepStatus,
            summary:  msg.summary  as string,
            duration: (msg.duration as number) ?? 0,
            step_n:   (msg.step_n  as number)  ?? 0,
          };
          setSteps(prev => {
            const idx = prev.findIndex(x => x.step === s.step && x.status === "running");
            if (idx >= 0) {
              const n = [...prev]; n[idx] = s; return n;
            }
            // Add running step or update existing
            const existing = prev.findIndex(x => x.step === s.step);
            if (existing >= 0) {
              const n = [...prev]; n[existing] = s; return n;
            }
            return [...prev, s];
          });
          if (msg.memory) setMemory(msg.memory as AutoMemory);
          break;
        }

        case "auto_confirm_request":
          setConfirmReq({
            id:     msg.id     as string,
            step:   msg.step   as string,
            tool:   msg.tool   as string,
            reason: msg.reason as string,
            risk:   msg.risk   as "HIGH" | "CRITICAL",
          });
          break;

        case "auto_status":
          if (msg.memory) setMemory(msg.memory as AutoMemory);
          break;

        case "auto_done":
          setRunning(false);
          setSummary(msg.summary as string);
          setReportPath((msg.report_path as string) ?? "");
          setReportDone(true);
          if (msg.memory) setMemory(msg.memory as AutoMemory);
          break;

        case "auto_stopped":
          setRunning(false);
          break;

        case "auto_error":
          setRunning(false);
          setError(msg.error as string);
          break;
      }
    });
    return unsub;
  }, []);

  const startTask = useCallback((goal: string, target = "") => {
    const id = crypto.randomUUID();
    setTaskId(id);
    bridge.send({ type: "auto_start", id, goal, target });
  }, []);

  const stopTask = useCallback(() => {
    bridge.send({ type: "auto_stop", id: taskId });
    setRunning(false);
  }, [taskId]);

  const confirm = useCallback((confirmed: boolean) => {
    bridge.send({ type: "auto_confirm", id: taskId, confirmed });
    setConfirmReq(null);
  }, [taskId]);

  const reset = useCallback(() => {
    setSteps([]); setMemory(null); setReportDone(false);
    setSummary(""); setError(""); setConfirmReq(null);
  }, []);

  return {
    running, steps, confirmReq, memory, reportPath,
    reportDone, summary, error, taskId,
    startTask, stopTask, confirm, reset,
  };
}

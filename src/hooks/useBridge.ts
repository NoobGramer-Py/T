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
        const ctx    = audioCtxRef.current;
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

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

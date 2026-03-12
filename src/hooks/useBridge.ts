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

import { useEffect, useCallback } from "react";
import { useTStore } from "../store";
import { bridge, type BrainMessage } from "../lib/bridge";

// ─── TTS ─────────────────────────────────────────────────────────────────────
// When brain is online, TTS is handled by Kokoro via useBrainVoice in useBridge.
// This hook is a no-op in that case — kept for the offline fallback path.

export function useSpeak() {
  const { voiceEnabled, voiceSettings, setVisualizerMode } = useTStore();

  const speak = useCallback((text: string) => {
    // Brain handles TTS when online — only use Web Speech as offline fallback
    if (!voiceEnabled || bridge.getStatus() === "online") return;
    try {
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      const utterance  = new SpeechSynthesisUtterance(text);
      utterance.rate   = voiceSettings.rate;
      utterance.pitch  = voiceSettings.pitch;
      if (voiceSettings.voiceName) {
        const match = window.speechSynthesis.getVoices()
          .find((v) => v.name === voiceSettings.voiceName);
        if (match) utterance.voice = match;
      }
      utterance.onstart = () => setVisualizerMode("speaking");
      utterance.onend   = () => setVisualizerMode("idle");
      utterance.onerror = () => setVisualizerMode("idle");
      window.speechSynthesis.speak(utterance);
    } catch {
      // TTS not available
    }
  }, [voiceEnabled, voiceSettings, setVisualizerMode]);

  const cancel = useCallback(() => {
    try { window.speechSynthesis?.cancel(); } catch { /* ignore */ }
    setVisualizerMode("idle");
  }, [setVisualizerMode]);

  return { speak, cancel };
}

// ─── Voice transcript from brain ─────────────────────────────────────────────
// Listens for voice_transcript events sent by the brain after push-to-talk.

export function useVoiceTranscript(onTranscript: (text: string) => void) {
  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      if (msg.type === "voice_transcript" && typeof msg.text === "string") {
        onTranscript(msg.text);
      }
    });
    return unsub;
  }, [onTranscript]);
}

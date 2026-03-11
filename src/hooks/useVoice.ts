import { useEffect, useRef, useCallback } from "react";
import { useTStore } from "../store";

// ─── Web Speech API types (not in all TS stdlib versions) ────────────────────

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous:     boolean;
  interimResults: boolean;
  lang:           string;
  start():        void;
  stop():         void;
  onresult:       ((e: SpeechRecognitionEvent) => void) | null;
  onerror:        ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend:          (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition:       new () => SpeechRecognitionInstance;
    webkitSpeechRecognition: new () => SpeechRecognitionInstance;
  }
}

const WAKE_WORDS = ["hey t", "hey tea", "a t", "ey t"];

function getSpeechRecognition(): SpeechRecognitionInstance | null {
  try {
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor) return null;
    return new Ctor();
  } catch {
    return null;
  }
}

// ─── TTS ─────────────────────────────────────────────────────────────────────

export function useSpeak() {
  const { voiceEnabled, voiceSettings, setVisualizerMode } = useTStore();

  const speak = useCallback((text: string) => {
    if (!voiceEnabled) return;
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
      // TTS not available in this WebView — silently ignore
    }
  }, [voiceEnabled, voiceSettings, setVisualizerMode]);

  const cancel = useCallback(() => {
    try { window.speechSynthesis?.cancel(); } catch { /* ignore */ }
    setVisualizerMode("idle");
  }, [setVisualizerMode]);

  return { speak, cancel };
}

// ─── STT + Wake Word ──────────────────────────────────────────────────────────

export function useVoiceInput(onCommand: (text: string) => void) {
  const voiceEnabled    = useTStore((s) => s.voiceEnabled);
  const setVoiceListening  = useTStore((s) => s.setVoiceListening);
  const setVisualizerMode  = useTStore((s) => s.setVisualizerMode);

  // Use refs so callbacks never go stale without recreating the effect
  const recognitionRef  = useRef<SpeechRecognitionInstance | null>(null);
  const activeRef       = useRef(false);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const voiceEnabledRef = useRef(voiceEnabled);
  const onCommandRef    = useRef(onCommand);

  // Keep refs current on every render — no effect re-run needed
  useEffect(() => { voiceEnabledRef.current = voiceEnabled; }, [voiceEnabled]);
  useEffect(() => { onCommandRef.current = onCommand; },      [onCommand]);

  // Stable stop function — never changes reference
  const stop = useCallback(() => {
    if (restartTimerRef.current) { clearTimeout(restartTimerRef.current); restartTimerRef.current = null; }
    try { recognitionRef.current?.stop(); } catch { /* ignore */ }
    recognitionRef.current = null;
    activeRef.current      = false;
    setVoiceListening(false);
    setVisualizerMode("idle");
  }, [setVoiceListening, setVisualizerMode]);

  // Stable start function — reads live state from refs
  const start = useCallback(() => {
    if (recognitionRef.current) return;
    const rec = getSpeechRecognition();
    if (!rec) return;

    rec.continuous     = true;
    rec.interimResults = false;
    rec.lang           = "en-US";

    rec.onresult = (e: SpeechRecognitionEvent) => {
      const transcript = e.results[e.results.length - 1][0].transcript.trim().toLowerCase();
      if (!activeRef.current) {
        if (WAKE_WORDS.some((w) => transcript.includes(w))) {
          activeRef.current = true;
          setVoiceListening(true);
          setVisualizerMode("listening");
        }
      } else {
        let command = transcript;
        for (const w of WAKE_WORDS) {
          if (command.startsWith(w)) { command = command.slice(w.length).trim(); break; }
        }
        if (command.length > 1) onCommandRef.current(command);
        activeRef.current = false;
        setVoiceListening(false);
        setVisualizerMode("idle");
      }
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error !== "no-speech") stop();
    };

    rec.onend = () => {
      recognitionRef.current = null;
      if (voiceEnabledRef.current) {
        restartTimerRef.current = setTimeout(start, 300);
      }
    };

    try {
      rec.start();
      recognitionRef.current = rec;
    } catch { /* already started or unavailable */ }
  }, [stop, setVoiceListening, setVisualizerMode]);

  // Single stable effect — only re-runs when voiceEnabled actually changes
  useEffect(() => {
    if (voiceEnabled) {
      start();
    } else {
      stop();
    }
    return stop;
  }, [voiceEnabled, start, stop]);
}

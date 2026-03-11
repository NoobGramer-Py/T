import { useEffect, useRef, useCallback } from "react";
import { useTStore } from "../store";

// ─── Type augmentation for Web Speech API (not in all TS libs) ────────────────

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous:        boolean;
  interimResults:    boolean;
  lang:              string;
  start():           void;
  stop():            void;
  onresult:          ((e: SpeechRecognitionEvent) => void) | null;
  onerror:           ((e: SpeechRecognitionErrorEvent) => void) | null;
  onend:             (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition:       new () => SpeechRecognitionInstance;
    webkitSpeechRecognition: new () => SpeechRecognitionInstance;
  }
}

const WAKE_WORDS = ["hey t", "hey tea", "a t", "ey t"];

function getSpeechRecognition(): SpeechRecognitionInstance | null {
  const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
  if (!Ctor) return null;
  return new Ctor();
}

// ─── TTS ─────────────────────────────────────────────────────────────────────

export function useSpeak() {
  const { voiceEnabled, voiceSettings, setVisualizerMode } = useTStore();

  const speak = useCallback((text: string) => {
    if (!voiceEnabled || !window.speechSynthesis) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate  = voiceSettings.rate;
    utterance.pitch = voiceSettings.pitch;

    if (voiceSettings.voiceName) {
      const voices = window.speechSynthesis.getVoices();
      const match  = voices.find((v) => v.name === voiceSettings.voiceName);
      if (match) utterance.voice = match;
    }

    utterance.onstart = () => setVisualizerMode("speaking");
    utterance.onend   = () => setVisualizerMode("idle");
    utterance.onerror = () => setVisualizerMode("idle");

    window.speechSynthesis.speak(utterance);
  }, [voiceEnabled, voiceSettings, setVisualizerMode]);

  const cancel = useCallback(() => {
    window.speechSynthesis?.cancel();
    setVisualizerMode("idle");
  }, [setVisualizerMode]);

  return { speak, cancel };
}

// ─── STT + Wake Word ──────────────────────────────────────────────────────────

export function useVoiceInput(onCommand: (text: string) => void) {
  const {
    voiceEnabled, voiceListening,
    setVoiceListening, setVisualizerMode,
  } = useTStore();

  const recognitionRef  = useRef<SpeechRecognitionInstance | null>(null);
  const activeRef       = useRef(false);   // true while capturing a command
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopRecognition = useCallback(() => {
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setVoiceListening(false);
    setVisualizerMode("idle");
    activeRef.current = false;
  }, [setVoiceListening, setVisualizerMode]);

  const startRecognition = useCallback(() => {
    if (recognitionRef.current) return;  // already running

    const rec = getSpeechRecognition();
    if (!rec) return;

    rec.continuous     = true;
    rec.interimResults = false;
    rec.lang           = "en-US";

    rec.onresult = (e: SpeechRecognitionEvent) => {
      const last       = e.results[e.results.length - 1];
      const transcript = last[0].transcript.trim().toLowerCase();

      if (!activeRef.current) {
        // Waiting for wake word
        const triggered = WAKE_WORDS.some((w) => transcript.includes(w));
        if (triggered) {
          activeRef.current = true;
          setVoiceListening(true);
          setVisualizerMode("listening");
        }
      } else {
        // Wake word already heard — this is the command
        // Strip the wake word from the start if it was caught in same utterance
        let command = transcript;
        for (const w of WAKE_WORDS) {
          if (command.startsWith(w)) {
            command = command.slice(w.length).trim();
            break;
          }
        }
        if (command.length > 1) {
          onCommand(command);
        }
        activeRef.current = false;
        setVoiceListening(false);
        setVisualizerMode("idle");
      }
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      // "no-speech" is normal — just restart. Other errors surface and stop.
      if (e.error !== "no-speech") {
        stopRecognition();
      }
    };

    rec.onend = () => {
      recognitionRef.current = null;
      // Auto-restart so it stays alive continuously
      if (voiceEnabled) {
        restartTimerRef.current = setTimeout(startRecognition, 300);
      }
    };

    try {
      rec.start();
      recognitionRef.current = rec;
    } catch {
      // Browser may throw if already started
    }
  }, [voiceEnabled, onCommand, setVoiceListening, setVisualizerMode, stopRecognition]);

  // Start/stop based on voiceEnabled flag
  useEffect(() => {
    if (voiceEnabled) {
      startRecognition();
    } else {
      stopRecognition();
    }
    return () => stopRecognition();
  }, [voiceEnabled, startRecognition, stopRecognition]);

  return { voiceListening };
}

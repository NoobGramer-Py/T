import { useCallback } from "react";
import { sendMessage, type ChatMessage } from "../lib/ai";
import { useTStore } from "../store";
import { usePersistMessage } from "./useMemory";
import { useSpeak } from "./useVoice";

export function useChat() {
  const { messages, addMessage, setTyping, setVisualizerMode, setProvider } = useTStore();
  const persist    = usePersistMessage();
  const { speak }  = useSpeak();

  const send = useCallback(
    async (userInput: string) => {
      const trimmed = userInput.trim();
      if (!trimmed) return;

      addMessage("user", trimmed);
      await persist("user", trimmed);

      setTyping(true);
      setVisualizerMode("listening");

      const history: ChatMessage[] = messages
        .filter((m) => m.id !== "boot")
        .slice(-20)
        .map((m) => ({ role: m.role, content: m.content }));
      history.push({ role: "user", content: trimmed });

      try {
        const { text, provider } = await sendMessage(history, "");
        setProvider(provider);
        addMessage("assistant", text);
        await persist("assistant", text);
        setVisualizerMode("speaking");
        speak(text);
        // Fallback idle reset if TTS is disabled or fails
        setTimeout(() => setVisualizerMode("idle"), 8000);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        addMessage("assistant", `SYSTEM ERROR: ${msg}`);
        setVisualizerMode("idle");
      } finally {
        setTyping(false);
      }
    },
    [messages, addMessage, setTyping, setVisualizerMode, setProvider, persist, speak]
  );

  return { send };
}

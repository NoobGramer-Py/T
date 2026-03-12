import { useCallback } from "react";
import { sendMessage, type ChatMessage } from "../lib/ai";
import { useTStore } from "../store";
import { usePersistMessage } from "./useMemory";
import { useSpeak } from "./useVoice";
import { useBrainChat } from "./useBridge";
import { bridge } from "../lib/bridge";

export function useChat() {
  const { messages, addMessage, setTyping, setVisualizerMode, setProvider } = useTStore();
  const persist   = usePersistMessage();
  const { speak } = useSpeak();
  const brainChat = useBrainChat();

  const send = useCallback(
    async (userInput: string) => {
      const trimmed = userInput.trim();
      if (!trimmed) return;

      addMessage("user", trimmed);
      await persist("user", trimmed);

      setTyping(true);
      setVisualizerMode("listening");

      const id = crypto.randomUUID();

      // ── Brain path (streaming) ────────────────────────────────────────────
      if (bridge.getStatus() === "online") {
        let accumulated = "";
        let messageAdded = false;

        const sent = brainChat.send(
          id,
          trimmed,
          (chunk) => {
            if (!messageAdded) {
              addMessage("assistant", chunk);
              messageAdded = true;
            } else {
              useTStore.setState((s) => {
                const msgs = [...s.messages];
                const last = msgs[msgs.length - 1];
                if (last?.role === "assistant") {
                  msgs[msgs.length - 1] = { ...last, content: accumulated + chunk };
                }
                return { messages: msgs };
              });
            }
            accumulated += chunk;
          },
          async () => {
            await persist("assistant", accumulated);
            speak(accumulated);
            setTimeout(() => setVisualizerMode("idle"), 8000);
            setTyping(false);
          },
          (err) => {
            addMessage("assistant", `SYSTEM ERROR: ${err}`);
            setVisualizerMode("idle");
            setTyping(false);
          },
        );

        if (sent) return;
      }

      // ── Direct AI fallback (Groq / Ollama) ───────────────────────────────
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
        setTimeout(() => setVisualizerMode("idle"), 8000);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        addMessage("assistant", `SYSTEM ERROR: ${msg}`);
        setVisualizerMode("idle");
      } finally {
        setTyping(false);
      }
    },
    [messages, addMessage, setTyping, setVisualizerMode, setProvider, persist, speak, brainChat]
  );

  return { send };
}

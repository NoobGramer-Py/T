import { useCallback, useRef } from "react";
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

  // Stable ref to always access latest messages without re-creating send
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

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
        // Add a placeholder message that we'll update in-place as chunks arrive
        addMessage("assistant", "");
        let accumulated = "";

        const sent = brainChat.send(
          id,
          trimmed,
          (chunk) => {
            accumulated += chunk;
            // Update the last assistant message in-place
            useTStore.setState((s) => {
              const msgs = [...s.messages];
              for (let i = msgs.length - 1; i >= 0; i--) {
                if (msgs[i].role === "assistant") {
                  msgs[i] = { ...msgs[i], content: accumulated };
                  break;
                }
              }
              return { messages: msgs };
            });
          },
          async (provider) => {
            setProvider(provider as "groq" | "ollama");
            await persist("assistant", accumulated);
            speak(accumulated);
            setTimeout(() => setVisualizerMode("idle"), 8000);
            setTyping(false);
          },
          (err) => {
            // Replace the empty placeholder with the error
            useTStore.setState((s) => {
              const msgs = [...s.messages];
              for (let i = msgs.length - 1; i >= 0; i--) {
                if (msgs[i].role === "assistant") {
                  msgs[i] = { ...msgs[i], content: `SYSTEM ERROR: ${err}` };
                  break;
                }
              }
              return { messages: msgs };
            });
            setVisualizerMode("idle");
            setTyping(false);
          },
        );

        if (sent) return;

        // send() returned false — remove the placeholder and fall through
        useTStore.setState((s) => ({
          messages: s.messages.filter((_, i) => i !== s.messages.length - 1),
        }));
      }

      // ── Direct AI fallback (Groq / Ollama) ───────────────────────────────
      const history: ChatMessage[] = messagesRef.current
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
    [addMessage, setTyping, setVisualizerMode, setProvider, persist, speak, brainChat]
  );

  return { send };
}

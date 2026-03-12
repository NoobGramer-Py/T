import { useState, useRef, useEffect, useCallback } from "react";
import { useTStore } from "../../store";
import { useChat } from "../../hooks/useChat";
import { useVoiceTranscript } from "../../hooks/useVoice";
import { useBrainVoice } from "../../hooks/useBridge";
import { JarvisCoreVisualizer } from "../hud/JarvisCoreVisualizer";

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "8px 0" }}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{
          width: 4, height: 4, borderRadius: "50%",
          background: "#ffb300",
          animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
          boxShadow: "0 0 6px #ffb300",
        }} />
      ))}
      <style>{`
        @keyframes pulse-dot {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
          40%            { transform: scale(1);   opacity: 1;   }
        }
      `}</style>
    </div>
  );
}

function MessageBubble({ role, content, timestamp }: {
  role:      "user" | "assistant";
  content:   string;
  timestamp: number;
}) {
  const isUser = role === "user";
  const time   = new Date(timestamp).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });

  return (
    <div className="fade-in-up" style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", marginBottom: 12 }}>
      <div style={{
        maxWidth: "78%",
        background: isUser ? "rgba(255,179,0,0.07)" : "rgba(255,179,0,0.03)",
        border: `1px solid ${isUser ? "rgba(255,179,0,0.25)" : "rgba(255,179,0,0.1)"}`,
        borderRadius: isUser ? "8px 8px 2px 8px" : "8px 8px 8px 2px",
        padding: "10px 14px", position: "relative",
      }}>
        <div style={{ fontSize: 7, letterSpacing: 4, marginBottom: 6, color: isUser ? "rgba(255,179,0,0.5)" : "rgba(255,179,0,0.35)" }}>
          {isUser ? "YOU" : "T"}
          <span style={{ marginLeft: 10, opacity: 0.5 }}>{time}</span>
        </div>
        <div style={{ fontSize: 12, lineHeight: 1.65, color: isUser ? "rgba(255,230,102,0.9)" : "rgba(255,179,0,0.85)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {content}
        </div>
        {!isUser && (
          <div style={{ position: "absolute", left: 0, top: "20%", bottom: "20%", width: 2, borderRadius: 1, background: "linear-gradient(to bottom, transparent, #ffb300, transparent)", opacity: 0.4 }} />
        )}
      </div>
    </div>
  );
}

export function ChatPanel() {
  const { messages, isTyping, visualizerMode, voiceEnabled, voiceListening } = useTStore();
  const { send }   = useChat();
  const [input, setInput] = useState("");
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);
  const { startPTT, stopPTT } = useBrainVoice();

  // When brain sends a transcript, auto-send it as a message
  const onTranscript = useCallback((text: string) => {
    send(text);
  }, [send]);
  useVoiceTranscript(onTranscript);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    send(input);
    setInput("");
    inputRef.current?.focus();
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const modeLabel = voiceListening
    ? "LISTENING"
    : visualizerMode === "idle"
    ? "STANDBY"
    : visualizerMode === "listening"
    ? "PROCESSING"
    : "RESPONDING";

  return (
    <div style={{ display: "flex", height: "100%", gap: 0 }}>
      {/* ── Visualizer column ── */}
      <div style={{ width: 320, flexShrink: 0, borderRight: "1px solid rgba(255,179,0,0.08)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", position: "relative" }}>
        <JarvisCoreVisualizer mode={voiceListening ? "listening" : visualizerMode} />

        {/* Wake word hint when voice is enabled */}
        {voiceEnabled && !voiceListening && (
          <div style={{ position: "absolute", top: 20, fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.25)", textAlign: "center" }}>
            SAY "HEY T" TO SPEAK
          </div>
        )}

        {/* Listening pulse ring */}
        {voiceListening && (
          <div style={{
            position: "absolute",
            width: 160, height: 160,
            borderRadius: "50%",
            border: "2px solid rgba(255,179,0,0.5)",
            animation: "ping 1s cubic-bezier(0,0,0.2,1) infinite",
            pointerEvents: "none",
          }} />
        )}

        <div style={{ position: "absolute", bottom: 24, fontSize: 8, letterSpacing: 5, color: voiceListening ? "#ffb300" : "rgba(255,179,0,0.35)", textAlign: "center", textShadow: voiceListening ? "0 0 8px #ffb300" : "none", transition: "all 0.3s ease" }}>
          {modeLabel}
        </div>
      </div>

      {/* ── Chat column ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Message list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 20px 8px" }}>
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} timestamp={m.timestamp} />
          ))}
          {isTyping && (
            <div style={{ paddingLeft: 4 }}>
              <TypingIndicator />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input row */}
        <div style={{ padding: "12px 20px 16px", borderTop: "1px solid rgba(255,179,0,0.08)", background: "rgba(0,4,9,0.6)" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
            <div style={{ fontSize: 14, color: "#ffb300", paddingBottom: 9, textShadow: "0 0 8px #ffb300", flexShrink: 0 }}>›</div>

            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={voiceListening ? "Listening..." : "Enter command or query..."}
              rows={1}
              style={{
                flex: 1, resize: "none", overflow: "hidden",
                background: "rgba(255,179,0,0.04)",
                border: `1px solid ${voiceListening ? "rgba(255,179,0,0.4)" : "rgba(255,179,0,0.15)"}`,
                borderRadius: 4, padding: "8px 12px",
                color: "rgba(255,230,102,0.9)",
                fontSize: 12, lineHeight: 1.5,
                fontFamily: "'Courier New', Courier, monospace",
                outline: "none", caretColor: "#ffb300",
                transition: "border-color 0.2s ease",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
              onBlur={(e)  => { e.currentTarget.style.borderColor = voiceListening ? "rgba(255,179,0,0.4)" : "rgba(255,179,0,0.15)"; }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
              }}
            />

            <button
              onClick={handleSend}
              disabled={isTyping || !input.trim()}
              style={{
                width: 36, height: 36, flexShrink: 0,
                background: isTyping || !input.trim() ? "transparent" : "rgba(255,179,0,0.1)",
                border: `1px solid ${isTyping || !input.trim() ? "rgba(255,179,0,0.1)" : "rgba(255,179,0,0.4)"}`,
                borderRadius: 4, cursor: isTyping ? "not-allowed" : "pointer",
                color: isTyping || !input.trim() ? "rgba(255,179,0,0.2)" : "#ffb300",
                fontSize: 14, transition: "all 0.2s ease",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              ▶
            </button>

            {/* Push-to-talk mic button — only shown when voice is enabled and brain is online */}
            {voiceEnabled && (
              <button
                onMouseDown={startPTT}
                onMouseUp={stopPTT}
                onTouchStart={startPTT}
                onTouchEnd={stopPTT}
                disabled={isTyping}
                style={{
                  width: 36, height: 36, flexShrink: 0,
                  background: voiceListening ? "rgba(255,179,0,0.2)" : "rgba(255,179,0,0.05)",
                  border: `1px solid ${voiceListening ? "#ffb300" : "rgba(255,179,0,0.2)"}`,
                  borderRadius: 4, cursor: isTyping ? "not-allowed" : "pointer",
                  color: voiceListening ? "#ffb300" : "rgba(255,179,0,0.4)",
                  fontSize: 14, transition: "all 0.15s ease",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: voiceListening ? "0 0 10px rgba(255,179,0,0.3)" : "none",
                }}
              >
                🎙
              </button>
            )}
          </div>

          <div style={{ marginTop: 6, paddingLeft: 24, fontSize: 8, color: "rgba(255,179,0,0.2)", letterSpacing: 2 }}>
            ENTER TO SEND · SHIFT+ENTER FOR NEWLINE{voiceEnabled ? " · SAY \"HEY T\" TO SPEAK" : ""}
          </div>
        </div>
      </div>
    </div>
  );
}

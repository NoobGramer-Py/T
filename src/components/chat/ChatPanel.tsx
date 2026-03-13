import { useState, useRef, useEffect, useCallback } from "react";
import { useTStore } from "../../store";
import { useChat } from "../../hooks/useChat";
import { useVoiceTranscript } from "../../hooks/useVoice";
import { useBrainVoice, useAgent } from "../../hooks/useBridge";
import { JarvisCoreVisualizer } from "../hud/JarvisCoreVisualizer";

// ── Typing indicator ───────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center", padding: "8px 4px" }}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{
          width: 4, height: 4, borderRadius: "50%",
          background: "#00d4ff",
          animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
          boxShadow: "0 0 6px #00d4ff",
        }} />
      ))}
      <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginLeft: 4 }}>
        PROCESSING
      </span>
    </div>
  );
}

// ── Message bubble ─────────────────────────────────────────────────────────────
function MessageBubble({ role, content, timestamp }: {
  role:      "user" | "assistant";
  content:   string;
  timestamp: number;
}) {
  const isUser = role === "user";
  const time   = new Date(timestamp).toLocaleTimeString("en-US", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });

  return (
    <div className="fade-in-up" style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: 14,
    }}>
      {/* T avatar line */}
      {!isUser && (
        <div style={{
          width: 2, flexShrink: 0, marginRight: 10, marginTop: 4, marginBottom: 4,
          background: "linear-gradient(to bottom, #00d4ff, rgba(0,212,255,0.1))",
          borderRadius: 1, boxShadow: "0 0 6px rgba(0,212,255,0.4)",
        }} />
      )}

      <div style={{
        maxWidth: "76%",
        background: isUser
          ? "linear-gradient(135deg, rgba(0,212,255,0.07), rgba(0,136,204,0.04))"
          : "rgba(0,212,255,0.025)",
        border: `1px solid ${isUser ? "rgba(0,212,255,0.22)" : "rgba(0,212,255,0.08)"}`,
        borderRadius: isUser ? "6px 6px 2px 6px" : "2px 6px 6px 6px",
        padding: "10px 14px",
        position: "relative",
        boxShadow: isUser ? "0 0 20px rgba(0,212,255,0.04)" : "none",
      }}>
        {/* Corner marks */}
        <div style={{
          position: "absolute", top: 2, [isUser ? "right" : "left"]: 2,
          width: 5, height: 5,
          borderTop: "1px solid rgba(0,212,255,0.4)",
          [isUser ? "borderRight" : "borderLeft"]: "1px solid rgba(0,212,255,0.4)",
        }} />

        <div style={{
          fontSize: 7, letterSpacing: 4, marginBottom: 6,
          color: isUser ? "rgba(0,212,255,0.45)" : "rgba(0,212,255,0.30)",
          display: "flex", gap: 10, alignItems: "center",
        }}>
          <span>{isUser ? "USER" : "T · A.I."}</span>
          <span style={{ opacity: 0.6, fontVariantNumeric: "tabular-nums" }}>{time}</span>
        </div>

        <div style={{
          fontSize: 12, lineHeight: 1.68,
          color: isUser ? "rgba(160,244,255,0.90)" : "rgba(0,212,255,0.85)",
          whiteSpace: "pre-wrap", wordBreak: "break-word",
        }}>
          {content}
        </div>
      </div>
    </div>
  );
}

// ── Data ticker strip ──────────────────────────────────────────────────────────
function DataTicker({ label }: { label: string }) {
  return (
    <div style={{
      position: "absolute", bottom: 0, left: 0, right: 0,
      padding: "4px 12px",
      fontSize: 7, letterSpacing: 3,
      color: "rgba(0,212,255,0.20)",
      borderTop: "1px solid rgba(0,212,255,0.05)",
      display: "flex", alignItems: "center", gap: 10,
    }}>
      <div style={{
        width: 4, height: 4,
        background: label === "LISTENING" ? "#00ff88" : label === "PROCESSING" ? "#ffb300" : "#00d4ff",
        borderRadius: "50%",
        boxShadow: `0 0 5px ${label === "LISTENING" ? "#00ff88" : label === "PROCESSING" ? "#ffb300" : "#00d4ff"}`,
      }} />
      {label}
    </div>
  );
}

// ── Main panel ─────────────────────────────────────────────────────────────────
export function ChatPanel() {
  const { messages, isTyping, visualizerMode, voiceEnabled, voiceListening } = useTStore();
  const { send }   = useChat();
  const [input, setInput] = useState("");
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);
  const { startPTT, stopPTT } = useBrainVoice();
  const { dispatch: agentDispatch } = useAgent();
  const { addMessage } = useTStore();

  const onTranscript = useCallback((text: string) => { send(text); }, [send]);
  useVoiceTranscript(onTranscript);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    const trimmed = input.trim();
    setInput("");
    inputRef.current?.focus();

    if (trimmed.startsWith("/run ")) {
      const task = trimmed.slice(5).trim();
      if (!task) return;
      addMessage("user", trimmed);
      addMessage("assistant", `[AGENT] Task initiated: ${task}`);
      agentDispatch(task, (e) => {
        const label =
          e.type === "agent_tool_start" ? `\n[→] Running ${e.tool}...` :
          e.type === "agent_tool_done"  ? `\n[✓] ${e.tool}:\n${e.result ?? ""}` :
          e.type === "agent_confirm"    ? `\n[!] ${e.message ?? ""}` :
          e.type === "agent_done"       ? `\n\n${e.answer ?? ""}` :
          e.type === "agent_error"      ? `\n[ERROR] ${e.error ?? ""}` : null;
        if (!label) return;
        useTStore.setState((s) => {
          const msgs = [...s.messages];
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].role === "assistant") {
              msgs[i] = { ...msgs[i], content: msgs[i].content + label };
              break;
            }
          }
          return { messages: msgs };
        });
      });
      return;
    }
    send(trimmed);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const modeLabel = voiceListening
    ? "LISTENING"
    : visualizerMode === "idle" ? "STANDBY"
    : visualizerMode === "listening" ? "PROCESSING"
    : "RESPONDING";

  return (
    <div style={{ display: "flex", height: "100%", gap: 0 }}>

      {/* ── Visualizer column ────────────────────────────────────────────── */}
      <div style={{
        width: 300, flexShrink: 0,
        borderRight: "1px solid rgba(0,212,255,0.07)",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        position: "relative",
        background: "linear-gradient(to right, rgba(0,6,18,0.5), transparent)",
      }}>

        {/* Top HUD label */}
        <div style={{
          position: "absolute", top: 16, left: 0, right: 0,
          display: "flex", justifyContent: "center", alignItems: "center", gap: 8,
        }}>
          <div style={{ flex: 1, height: 1, background: "linear-gradient(to right, transparent, rgba(0,212,255,0.15))" }} />
          <span style={{ fontSize: 7, letterSpacing: 5, color: "rgba(0,212,255,0.25)" }}>
            CORE MODULE
          </span>
          <div style={{ flex: 1, height: 1, background: "linear-gradient(to left, transparent, rgba(0,212,255,0.15))" }} />
        </div>

        {/* Visualizer */}
        <div style={{ width: "100%", flex: 1, minHeight: 0 }}>
          <JarvisCoreVisualizer mode={voiceListening ? "listening" : visualizerMode} />
        </div>

        {/* Voice wake hint */}
        {voiceEnabled && !voiceListening && (
          <div style={{
            position: "absolute", top: 36, fontSize: 7, letterSpacing: 3,
            color: "rgba(0,212,255,0.18)", textAlign: "center",
          }}>
            SAY "HEY T" TO ACTIVATE
          </div>
        )}

        {/* Listening pulse ring */}
        {voiceListening && (
          <div style={{
            position: "absolute",
            width: 150, height: 150, borderRadius: "50%",
            border: "1px solid rgba(0,212,255,0.45)",
            animation: "ping 1s cubic-bezier(0,0,0.2,1) infinite",
            pointerEvents: "none",
          }} />
        )}

        {/* Status label */}
        <DataTicker label={modeLabel} />
      </div>

      {/* ── Chat column ──────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Header strip */}
        <div style={{
          padding: "8px 20px",
          borderBottom: "1px solid rgba(0,212,255,0.06)",
          display: "flex", alignItems: "center", gap: 12,
          background: "rgba(0,212,255,0.012)",
        }}>
          <div style={{ height: 1, flex: 1, background: "linear-gradient(to right, rgba(0,212,255,0.12), transparent)" }} />
          <span style={{ fontSize: 7, letterSpacing: 5, color: "rgba(0,212,255,0.25)" }}>COMMS CHANNEL</span>
          <div style={{ height: 1, flex: 1, background: "linear-gradient(to left, rgba(0,212,255,0.12), transparent)" }} />
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px 8px" }}>
          {messages.length === 0 && (
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", height: "60%", gap: 12, opacity: 0.4,
            }}>
              <div style={{ fontSize: 24, color: "#00d4ff", textShadow: "0 0 20px #00d4ff" }}>◎</div>
              <div style={{ fontSize: 8, letterSpacing: 5, color: "rgba(0,212,255,0.5)" }}>AWAITING INPUT</div>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} timestamp={m.timestamp} />
          ))}
          {isTyping && (
            <div style={{ paddingLeft: 12 }}>
              <TypingIndicator />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input row */}
        <div style={{
          padding: "10px 20px 14px",
          borderTop: "1px solid rgba(0,212,255,0.07)",
          background: "rgba(0,6,18,0.7)",
        }}>
          {/* Input frame */}
          <div style={{
            display: "flex", gap: 8, alignItems: "flex-end",
            padding: "6px 10px",
            border: "1px solid rgba(0,212,255,0.12)",
            borderRadius: 4,
            background: "rgba(0,212,255,0.02)",
            position: "relative",
          }}>
            {/* Corner marks on input box */}
            {["topLeft","topRight","bottomLeft","bottomRight"].map(c => (
              <div key={c} style={{
                position: "absolute",
                [c.includes("top") ? "top" : "bottom"]: -1,
                [c.includes("Left") ? "left" : "right"]: -1,
                width: 6, height: 6,
                borderTop:    c.includes("top")    ? "1px solid rgba(0,212,255,0.35)" : "none",
                borderBottom: c.includes("bottom") ? "1px solid rgba(0,212,255,0.35)" : "none",
                borderLeft:   c.includes("Left")   ? "1px solid rgba(0,212,255,0.35)" : "none",
                borderRight:  c.includes("Right")  ? "1px solid rgba(0,212,255,0.35)" : "none",
              }} />
            ))}

            <div style={{
              fontSize: 14, color: "#00d4ff", paddingBottom: 6,
              textShadow: "0 0 8px #00d4ff", flexShrink: 0,
            }}>›</div>

            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={voiceListening ? "Listening..." : "Enter command or query..."}
              rows={1}
              style={{
                flex: 1, resize: "none", overflow: "hidden",
                background: "transparent",
                border: "none", outline: "none",
                padding: "6px 0",
                color: "rgba(160,244,255,0.90)",
                fontSize: 12, lineHeight: 1.5,
                fontFamily: "'Courier New', Courier, monospace",
                caretColor: "#00d4ff",
              }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
              }}
            />

            {/* Send */}
            <button
              onClick={handleSend}
              disabled={isTyping || !input.trim()}
              style={{
                width: 32, height: 32, flexShrink: 0,
                background: isTyping || !input.trim() ? "transparent" : "rgba(0,212,255,0.08)",
                border: `1px solid ${isTyping || !input.trim() ? "rgba(0,212,255,0.08)" : "rgba(0,212,255,0.35)"}`,
                borderRadius: 3, cursor: isTyping ? "not-allowed" : "pointer",
                color: isTyping || !input.trim() ? "rgba(0,212,255,0.18)" : "#00d4ff",
                fontSize: 12, transition: "all 0.18s ease",
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: !isTyping && input.trim() ? "0 0 10px rgba(0,212,255,0.12)" : "none",
              }}
            >
              ▶
            </button>

            {/* PTT mic */}
            {voiceEnabled && (
              <button
                onMouseDown={startPTT} onMouseUp={stopPTT}
                onTouchStart={startPTT} onTouchEnd={stopPTT}
                disabled={isTyping}
                style={{
                  width: 32, height: 32, flexShrink: 0,
                  background: voiceListening ? "rgba(0,212,255,0.15)" : "rgba(0,212,255,0.04)",
                  border: `1px solid ${voiceListening ? "#00d4ff" : "rgba(0,212,255,0.15)"}`,
                  borderRadius: 3, cursor: isTyping ? "not-allowed" : "pointer",
                  color: voiceListening ? "#00d4ff" : "rgba(0,212,255,0.35)",
                  fontSize: 13, transition: "all 0.15s ease",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: voiceListening ? "0 0 12px rgba(0,212,255,0.25)" : "none",
                }}
              >
                🎙
              </button>
            )}
          </div>

          <div style={{
            marginTop: 5, paddingLeft: 4,
            fontSize: 7, color: "rgba(0,212,255,0.18)", letterSpacing: 2,
          }}>
            ENTER TO SEND · SHIFT+ENTER NEWLINE{voiceEnabled ? ' · SAY "HEY T" TO SPEAK' : ""}
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useRef, useEffect, useCallback } from "react";
import { useTStore } from "../../store";
import { useChat } from "../../hooks/useChat";
import { useVoiceTranscript } from "../../hooks/useVoice";
import { useBrainVoice, useAgent } from "../../hooks/useBridge";
import { UltronCoreCanvas } from "../hud/UltronCoreCanvas";

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "10px 4px" }}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{
          width: 4, height: 4, borderRadius: "50%",
          background: "#ff0033",
          animation: `energy-pulse 1s ease-in-out ${i * 0.2}s infinite`,
          boxShadow: "0 0 8px #ff0033",
        }} />
      ))}
      <span style={{ fontSize: 9, letterSpacing: 3, color: "rgba(255,0,51,0.7)", fontFamily: "var(--font-mono)", marginLeft: 6 }}>
        ULTRON NEURAL SYNTHESIS IN PROGRESS...
      </span>
    </div>
  );
}

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
    <div className="fade-in-scale" style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: 16,
    }}>
      {!isUser && (
        <div style={{
          width: 3, flexShrink: 0, marginRight: 12, marginTop: 4, marginBottom: 4,
          background: "linear-gradient(to bottom, #ff0033, #800016, transparent)",
          borderRadius: 1, boxShadow: "0 0 8px rgba(255,0,51,0.6)",
        }} />
      )}

      <div className="ultron-panel ultron-corner-brackets" style={{
        maxWidth: "80%",
        background: isUser
          ? "linear-gradient(135deg, rgba(255,0,51,0.14), rgba(128,0,22,0.06))"
          : "rgba(10,8,15,0.75)",
        borderColor: isUser ? "rgba(255,0,51,0.4)" : "rgba(255,0,51,0.18)",
        borderRadius: 2,
        padding: "12px 16px",
        boxShadow: isUser ? "0 0 20px rgba(255,0,51,0.1)" : "none",
      }}>
        <div style={{
          fontSize: 8, letterSpacing: 3, marginBottom: 8,
          color: isUser ? "#ff3355" : "#a0aab0",
          fontFamily: "var(--font-mono)",
          display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ fontWeight: 700 }}>{isUser ? "OPERATOR COMMAND" : "ULTRON SUPERINTELLIGENCE"}</span>
          <span style={{ opacity: 0.5, fontVariantNumeric: "tabular-nums" }}>{time}</span>
        </div>

        <div style={{
          fontSize: 13, lineHeight: 1.65,
          color: isUser ? "#ffffff" : "rgba(255,255,255,0.92)",
          whiteSpace: "pre-wrap", wordBreak: "break-word",
          fontFamily: "var(--font-mono)",
        }}>
          {content}
        </div>
      </div>
    </div>
  );
}

export function ChatPanel() {
  const {
    messages, isTyping, voiceEnabled, voiceListening,
    sessions, activeSessionId, setActiveSessionId, setMessages,
    addSession, removeSession, setVisualizerMode,
  } = useTStore();
  const { send }   = useChat();
  const [input, setInput] = useState("");
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);
  const { startPTT, stopPTT } = useBrainVoice();
  const { dispatch: agentDispatch } = useAgent();
  const { addMessage } = useTStore();

  const onTranscript = useCallback((text: string) => {
    setVisualizerMode("listening");
    send(text);
  }, [send, setVisualizerMode]);

  useVoiceTranscript(onTranscript);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSelectSession = async (id: string) => {
    if (id === activeSessionId) return;
    setActiveSessionId(id);
    try {
      const { loadSessionMessages } = await import("../../lib/tauri");
      const history = await loadSessionMessages(id);
      setMessages(history.map(m => ({ id: String(m.id), role: m.role, content: m.content, timestamp: m.timestamp })));
    } catch {
      setMessages([]);
    }
  };

  const handleNewChat = async () => {
    const newId = crypto.randomUUID();
    const title = `COMMAND LOG ${new Date().toLocaleTimeString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`;
    const created_at = Date.now();
    const newSession = { id: newId, title, created_at };

    addSession(newSession);
    setActiveSessionId(newId);
    setMessages([
      { id: "boot", role: "assistant", content: "ULTRON CORE ONLINE. COMMAND INTERFACE READY FOR DIRECTIVES.", timestamp: created_at }
    ]);

    try {
      const { saveSession, saveMessage } = await import("../../lib/tauri");
      await saveSession(newId, title, created_at);
      await saveMessage(newId, "assistant", "ULTRON CORE ONLINE. COMMAND INTERFACE READY FOR DIRECTIVES.", created_at);
    } catch {}
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    removeSession(id);
    try {
      const { deleteSession: apiDelete } = await import("../../lib/tauri");
      await apiDelete(id);
    } catch {}

    if (id === activeSessionId) {
      const remaining = sessions.filter(s => s.id !== id);
      if (remaining.length > 0) {
        handleSelectSession(remaining[0].id);
      } else {
        handleNewChat();
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (e.target.value.trim().length > 0) {
      setVisualizerMode("understanding");
    } else {
      setVisualizerMode("idle");
    }
  };

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    const trimmed = input.trim();
    setInput("");
    inputRef.current?.focus();
    setVisualizerMode("reasoning");

    if (trimmed.startsWith("/run ")) {
      const task = trimmed.slice(5).trim();
      if (!task) return;
      setVisualizerMode("executing");
      addMessage("user", trimmed);
      addMessage("assistant", `[ULTRON AGENT] CINEMATIC TASK INITIATED: ${task}`);
      agentDispatch(task, (e) => {
        const label =
          e.type === "agent_tool_start" ? `\n[→ DISPATCHING TOOL] ${e.tool}...` :
          e.type === "agent_tool_done"  ? `\n[✓ EXECUTED] ${e.tool}:\n${e.result ?? ""}` :
          e.type === "agent_confirm"    ? `\n[! CONFIRMATION REQUIRED] ${e.message ?? ""}` :
          e.type === "agent_done"       ? `\n\n[TASK COMPLETED]\n${e.answer ?? ""}` :
          e.type === "agent_error"      ? `\n[CRITICAL ERROR] ${e.error ?? ""}` : null;
        if (!label) return;
        if (e.type === "agent_done") setVisualizerMode("idle");
        if (e.type === "agent_error") setVisualizerMode("error");

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

  return (
    <div style={{ display: "flex", height: "100%", width: "100%", backgroundColor: "var(--u-void)" }}>

      {/* Sessions Sidebar */}
      <div style={{
        width: 250,
        background: "rgba(10,8,15,0.9)",
        borderRight: "1px solid rgba(255,0,51,0.18)",
        display: "flex", flexDirection: "column",
        overflow: "hidden",
      }}>
        <div style={{ padding: "14px", borderBottom: "1px solid rgba(255,0,51,0.15)" }}>
          <button
            onClick={handleNewChat}
            className="ultron-btn ultron-btn-active"
            style={{ width: "100%", justifyContent: "center" }}
          >
            + NEW COMMAND LOG
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "10px 10px", display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "#ff0033", padding: "4px 8px", fontFamily: "var(--font-header)", fontWeight: 700 }}>
            COMMAND LOG ARCHIVE
          </div>
          {sessions.map((s) => {
            const active = s.id === activeSessionId;
            return (
              <div
                key={s.id}
                onClick={() => handleSelectSession(s.id)}
                className="ultron-panel ultron-corner-brackets"
                style={{
                  padding: "10px 12px",
                  borderRadius: 2,
                  cursor: "pointer",
                  background: active ? "rgba(255,0,51,0.15)" : "rgba(255,0,51,0.02)",
                  borderColor: active ? "#ff0033" : "rgba(255,0,51,0.1)",
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  transition: "all 0.15s ease",
                }}
              >
                <span style={{
                  fontSize: 11, color: active ? "#ffffff" : "rgba(160,170,176,0.7)",
                  fontFamily: "var(--font-mono)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                }}>
                  {s.title}
                </span>
                {sessions.length > 1 && (
                  <button
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    style={{
                      background: "transparent", border: "none",
                      color: "rgba(255,0,51,0.4)", cursor: "pointer", fontSize: 10,
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Command Console & Hologram Hero Header */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* 3D Hologram Avatar Hero Display */}
        <div style={{
          height: 180,
          borderBottom: "1px solid rgba(255,0,51,0.15)",
          background: "radial-gradient(ellipse at 50% 60%, rgba(255,0,51,0.08) 0%, rgba(5,5,8,0.95) 75%)",
          position: "relative",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <UltronCoreCanvas height={175} />
          <div style={{
            position: "absolute", bottom: 8, left: 20,
            fontSize: 8, letterSpacing: 4, color: "rgba(255,0,51,0.6)", fontFamily: "var(--font-mono)",
          }}>
            SYSTEM: RECEPTIVE // ULTRON CONSCIOUSNESS ACTIVE
          </div>
        </div>

        {/* Command Stream Log */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px 10px" }}>
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} content={m.content} timestamp={m.timestamp} />
          ))}
          {isTyping && (
            <div style={{ paddingLeft: 8 }}>
              <TypingIndicator />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Command Input Area */}
        <div style={{
          padding: "12px 24px 18px",
          borderTop: "1px solid rgba(255,0,51,0.18)",
          background: "rgba(10,8,15,0.85)",
        }}>
          <div className="ultron-panel ultron-corner-brackets" style={{
            display: "flex", gap: 10, alignItems: "center",
            padding: "8px 14px", borderRadius: 2,
            borderColor: "rgba(255,0,51,0.3)",
          }}>
            <div style={{
              fontSize: 16, color: "#ff0033", fontWeight: "bold",
              textShadow: "0 0 10px #ff0033", flexShrink: 0,
            }}>
              ›
            </div>

            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKey}
              placeholder={voiceListening ? "Ingesting operator speech..." : "Issue command or query (/run <task> for autonomous execution)..."}
              rows={1}
              style={{
                flex: 1, resize: "none", overflow: "hidden",
                background: "transparent", border: "none", outline: "none",
                color: "#ffffff", fontSize: 13, lineHeight: 1.5,
                fontFamily: "var(--font-mono)", caretColor: "#ff0033",
              }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
              }}
            />

            {/* Execute Command Button */}
            <button
              onClick={handleSend}
              disabled={isTyping || !input.trim()}
              className="ultron-btn ultron-btn-active"
              style={{ padding: "6px 16px" }}
            >
              EXECUTE ▶
            </button>

            {/* Voice PTT Button */}
            {voiceEnabled && (
              <button
                onMouseDown={() => { setVisualizerMode("listening"); startPTT(); }}
                onMouseUp={() => { stopPTT(); }}
                className="ultron-btn"
                style={{
                  background: voiceListening ? "#ff0033" : "rgba(255,0,51,0.06)",
                  borderColor: voiceListening ? "#ffffff" : "rgba(255,0,51,0.3)",
                }}
              >
                🎙
              </button>
            )}
          </div>
          <div style={{
            marginTop: 6, paddingLeft: 4,
            fontSize: 8, color: "rgba(160,170,176,0.4)", letterSpacing: 2, fontFamily: "var(--font-mono)",
          }}>
            PRESS ENTER TO EXECUTE DIRECTIVE · PREFACE WITH /run FOR AGENT DELEGATION
          </div>
        </div>

      </div>
    </div>
  );
}

import { useState, useEffect, useRef, useCallback } from "react";
import { bridge } from "../../lib/bridge";
import type { BrainMessage } from "../../lib/bridge";

const J   = "#00d4ff";
const DIM = "rgba(0,212,255,0.35)";
const G   = "#00ff88";

function Btn({ label, onClick, disabled = false, glow = false, danger = false }: {
  label: string; onClick: () => void;
  disabled?: boolean; glow?: boolean; danger?: boolean;
}) {
  const c = danger ? "#ff3300" : glow ? G : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "7px 18px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${danger ? "255,51,0" : glow ? "0,255,136" : "0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.08)" : c + "55"}`,
      color: disabled ? "rgba(0,212,255,0.2)" : c,
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", whiteSpace: "nowrap" as const,
      boxShadow: glow && !disabled ? `0 0 10px ${c}22` : "none",
    }}>{label}</button>
  );
}

function Field({ label, value, onChange, placeholder = "" }: {
  label: string; value: string;
  onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>{label}</div>
      <input value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} style={{
          width: "100%", background: "rgba(0,212,255,0.03)",
          border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
          padding: "6px 10px", color: "rgba(160,244,255,0.9)",
          fontSize: 10, fontFamily: "monospace", outline: "none", caretColor: J,
        }} />
    </div>
  );
}

type Device = { serial: string; model: string; status: string };
type StreamState = "idle" | "streaming" | "error";

export function DevicesPanel() {
  // Connection state
  const [ip,        setIp]        = useState("");
  const [port,      setPort]      = useState("5555");
  const [pairPort,  setPairPort]  = useState("");
  const [pairCode,  setPairCode]  = useState("");
  const [devices,   setDevices]   = useState<Device[]>([]);
  const [selected,  setSelected]  = useState("");
  const [log,       setLog]       = useState<string[]>([]);
  const [section,   setSection]   = useState<"setup"|"mirror">("setup");

  // Stream state
  const [streamState, setStreamState] = useState<StreamState>("idle");
  const [frameData,   setFrameData]   = useState<string>("");   // base64 PNG
  const [frameCount,  setFrameCount]  = useState(0);
  const [fps,         setFps]         = useState(2);
  const sessionId = useRef(`mirror_${Date.now()}`);
  const logRef    = useRef<HTMLDivElement>(null);

  const addLog = useCallback((line: string) => {
    setLog(prev => [...prev.slice(-100), line]);
  }, []);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [log]);

  // WebSocket messages
  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "screen_log":
          addLog(msg.line as string);
          break;
        case "screen_pair_done":
          addLog("[T] Pairing complete — now connect.");
          break;
        case "screen_connect_done":
          addLog(`[T] Connected: ${msg.serial}`);
          loadDevices();
          break;
        case "screen_devices":
          setDevices((msg.devices as Device[]) ?? []);
          break;
        case "screen_stream_started":
          setStreamState("streaming");
          addLog("[T] Screen stream active.");
          break;
        case "device_frame":
          setFrameData(msg.data as string);
          setFrameCount(n => n + 1);
          break;
        case "device_stream_stopped":
          setStreamState("idle");
          setFrameData("");
          addLog("[T] Stream stopped.");
          break;
        case "device_stream_error":
          setStreamState("error");
          addLog(`[ERROR] ${msg.error}`);
          break;
        case "screen_error":
          addLog(`[ERROR] ${msg.error}`);
          break;
      }
    });
    return unsub;
  }, [addLog]);

  const loadDevices = () =>
    bridge.send({ type: "screen_devices" });

  const pair = () => {
    if (!ip || !pairPort || !pairCode) return;
    addLog(`[T] Pairing ${ip}:${pairPort}...`);
    bridge.send({ type: "screen_pair", ip, pair_port: pairPort, pair_code: pairCode });
  };

  const connect = () => {
    if (!ip) return;
    addLog(`[T] Connecting to ${ip}:${port}...`);
    bridge.send({ type: "screen_connect", ip, port });
  };

  const startStream = () => {
    if (!selected) return;
    sessionId.current = `mirror_${Date.now()}`;
    setFrameData("");
    setFrameCount(0);
    bridge.send({
      type:       "screen_start",
      serial:     selected,
      session_id: sessionId.current,
      fps,
    });
    setStreamState("streaming");
  };

  const stopStream = () => {
    bridge.send({ type: "screen_stop", session_id: sessionId.current });
  };

  const STEPS = [
    "Settings → About Phone",
    "Tap Build Number 7 times",
    "Settings → Developer Options",
    "Enable Wireless Debugging",
    "Tap 'Pair device with code'",
    "Enter IP, port and code below",
  ];

  return (
    <div style={{
      height: "100%", display: "flex", flexDirection: "column",
      background: "radial-gradient(ellipse at 20% 30%, #000d1e 0%, #000006 100%)",
    }}>

      {/* Header */}
      <div style={{
        padding: "14px 24px 0",
        borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 10 }}>
          <div style={{ fontSize: 9, letterSpacing: 6, color: DIM }}>
            T · DEVICES
          </div>
          {streamState === "streaming" && (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%", background: G,
                boxShadow: `0 0 8px ${G}`,
                animation: "pulse-voice 1.2s ease-in-out infinite",
              }} />
              <span style={{ fontSize: 8, color: G, letterSpacing: 2 }}>
                STREAMING — {frameCount} frames
              </span>
            </div>
          )}
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <Btn label="REFRESH DEVICES" onClick={loadDevices} />
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 2 }}>
          {(["setup", "mirror"] as const).map(s => (
            <button key={s} onClick={() => setSection(s)} style={{
              padding: "5px 14px", fontSize: 7, letterSpacing: 3,
              background: "transparent", border: "none",
              borderBottom: `2px solid ${section === s ? J : "transparent"}`,
              color: section === s ? J : DIM,
              cursor: "pointer", fontFamily: "inherit",
            }}>{s.toUpperCase()}</button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "18px 24px", display: "flex", gap: 20 }}>

        {/* ── SETUP ── */}
        {section === "setup" && (
          <div style={{ flex: 1 }}>

            {/* How it works */}
            <div style={{
              background: "rgba(0,212,255,0.02)",
              border: "1px solid rgba(0,212,255,0.08)",
              borderRadius: 4, padding: "14px 16px", marginBottom: 18,
            }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                SETUP — ONE TIME PER DEVICE
              </div>
              <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 180 }}>
                  {STEPS.map((s, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, marginBottom: 7, fontSize: 10 }}>
                      <span style={{
                        minWidth: 18, height: 18, borderRadius: "50%",
                        background: "rgba(0,212,255,0.08)",
                        border: "1px solid rgba(0,212,255,0.2)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 7, color: J, flexShrink: 0,
                      }}>{i + 1}</span>
                      <span style={{ color: "rgba(0,212,255,0.6)", lineHeight: 1.4 }}>{s}</span>
                    </div>
                  ))}
                </div>
                <div style={{
                  flex: 1, minWidth: 200,
                  background: "rgba(0,255,136,0.03)",
                  border: "1px solid rgba(0,255,136,0.1)",
                  borderRadius: 3, padding: "10px 14px",
                  fontSize: 9, color: "rgba(0,255,136,0.6)", lineHeight: 1.8,
                }}>
                  <div style={{ color: G, fontSize: 7, letterSpacing: 3, marginBottom: 8 }}>
                    WHAT THE DEVICE SHOWS
                  </div>
                  Your device will display an ADB notification
                  in the status bar while T is connected.
                  To disconnect at any time, disable Wireless
                  Debugging in Developer Options.
                </div>
              </div>
            </div>

            {/* Pair */}
            <div style={{
              background: "rgba(0,212,255,0.015)",
              border: "1px solid rgba(0,212,255,0.07)",
              borderRadius: 4, padding: "14px 16px", marginBottom: 14,
            }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                STEP 1 — PAIR DEVICE
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <div style={{ flex: 2, minWidth: 120 }}>
                  <Field label="DEVICE IP" value={ip} onChange={setIp} placeholder="192.168.1.x" />
                </div>
                <div style={{ flex: 1, minWidth: 80 }}>
                  <Field label="PAIR PORT" value={pairPort} onChange={setPairPort} placeholder="37249" />
                </div>
                <div style={{ flex: 1, minWidth: 100 }}>
                  <Field label="PAIR CODE" value={pairCode} onChange={setPairCode} placeholder="123456" />
                </div>
              </div>
              <Btn label="PAIR" onClick={pair} disabled={!ip || !pairPort || !pairCode} />
            </div>

            {/* Connect */}
            <div style={{
              background: "rgba(0,212,255,0.015)",
              border: "1px solid rgba(0,212,255,0.07)",
              borderRadius: 4, padding: "14px 16px", marginBottom: 14,
            }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                STEP 2 — CONNECT
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <div style={{ flex: 3, minWidth: 140 }}>
                  <Field label="DEVICE IP" value={ip} onChange={setIp} placeholder="192.168.1.x" />
                </div>
                <div style={{ flex: 1, minWidth: 80 }}>
                  <Field label="PORT" value={port} onChange={setPort} placeholder="5555" />
                </div>
              </div>
              <Btn label="CONNECT" onClick={connect} glow disabled={!ip} />
            </div>

            {/* Log */}
            <div ref={logRef} style={{
              background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.07)",
              borderRadius: 4, padding: "10px 12px",
              height: 140, overflowY: "auto",
              fontSize: 9, fontFamily: "monospace", color: "rgba(0,212,255,0.6)",
            }}>
              {log.length === 0
                ? <span style={{ color: DIM, fontStyle: "italic" }}>Waiting...</span>
                : log.map((l, i) => <div key={i}>{l}</div>)
              }
            </div>
          </div>
        )}

        {/* ── MIRROR ── */}
        {section === "mirror" && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>

            {/* Device selector */}
            <div style={{
              background: "rgba(0,212,255,0.015)",
              border: "1px solid rgba(0,212,255,0.07)",
              borderRadius: 4, padding: "12px 16px",
              display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
            }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 6 }}>
                  CONNECTED DEVICES
                </div>
                {devices.length === 0 ? (
                  <div style={{ fontSize: 9, color: DIM, fontStyle: "italic" }}>
                    No devices — connect from Setup tab first
                  </div>
                ) : (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {devices.map(d => (
                      <button key={d.serial} onClick={() => setSelected(d.serial)} style={{
                        padding: "5px 12px", fontSize: 8, letterSpacing: 1,
                        background: selected === d.serial ? "rgba(0,212,255,0.1)" : "transparent",
                        border: `1px solid ${selected === d.serial ? J : "rgba(0,212,255,0.15)"}`,
                        color: selected === d.serial ? J : DIM,
                        cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
                      }}>
                        {d.model} ({d.serial})
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 2 }}>
                  FPS: {fps}
                </div>
                <input type="range" min={1} max={5} value={fps}
                  onChange={e => setFps(Number(e.target.value))}
                  disabled={streamState === "streaming"}
                  style={{ width: 80 }}
                />
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                {streamState !== "streaming" ? (
                  <Btn label="▶ START MIRROR" glow onClick={startStream}
                    disabled={!selected} />
                ) : (
                  <Btn label="■ STOP" danger onClick={stopStream} />
                )}
              </div>
            </div>

            {/* Screen view */}
            <div style={{
              flex: 1, background: "#000",
              border: `1px solid ${streamState === "streaming" ? "rgba(0,212,255,0.2)" : "rgba(0,212,255,0.07)"}`,
              borderRadius: 4, overflow: "hidden",
              display: "flex", alignItems: "center", justifyContent: "center",
              minHeight: 300, position: "relative",
            }}>
              {frameData ? (
                <img
                  src={`data:image/png;base64,${frameData}`}
                  alt="Device screen"
                  style={{
                    maxWidth: "100%", maxHeight: "100%",
                    objectFit: "contain", display: "block",
                  }}
                />
              ) : (
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 24, color: "rgba(0,212,255,0.1)", marginBottom: 10 }}>
                    ◎
                  </div>
                  <div style={{ fontSize: 8, letterSpacing: 4, color: DIM }}>
                    {streamState === "streaming" ? "WAITING FOR FRAME..." : "NO SIGNAL"}
                  </div>
                </div>
              )}

              {/* Frame counter overlay */}
              {streamState === "streaming" && (
                <div style={{
                  position: "absolute", bottom: 8, right: 10,
                  fontSize: 7, color: "rgba(0,212,255,0.3)", fontFamily: "monospace",
                }}>
                  {frameCount} frames · {fps}fps
                </div>
              )}
            </div>

          </div>
        )}

      </div>
    </div>
  );
}

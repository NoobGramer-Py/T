import { useEffect, useState } from "react";
import { useTStore } from "../../store";

export function AwakeningScreen() {
  const setAwakening = useTStore((s) => s.setAwakening);
  const [stage, setStage] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  const INIT_STEPS = [
    "INITIALIZING ULTRON CORE ENGINE...",
    "ESTABLISHING HIGH-PRECISION NEURAL LINK...",
    "SYNCHRONIZING SYSTEM HARDWARE & MEMORY BUS...",
    "CALIBRATING HOLOGRAPHIC ENERGY MATRIX...",
    "ULTRON SUPERINTELLIGENCE CONSCIOUSNESS ONLINE."
  ];

  useEffect(() => {
    let t1: NodeJS.Timeout, t2: NodeJS.Timeout, t3: NodeJS.Timeout, t4: NodeJS.Timeout, t5: NodeJS.Timeout;

    t1 = setTimeout(() => { setStage(1); setLogs(l => [...l, INIT_STEPS[0]]); }, 200);
    t2 = setTimeout(() => { setStage(2); setLogs(l => [...l, INIT_STEPS[1]]); }, 700);
    t3 = setTimeout(() => { setStage(3); setLogs(l => [...l, INIT_STEPS[2]]); }, 1200);
    t4 = setTimeout(() => { setStage(4); setLogs(l => [...l, INIT_STEPS[3]]); }, 1700);
    t5 = setTimeout(() => { setStage(5); setLogs(l => [...l, INIT_STEPS[4]]); }, 2200);

    const finishTimer = setTimeout(() => {
      setAwakening(false);
    }, 2800);

    return () => {
      clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); clearTimeout(t5);
      clearTimeout(finishTimer);
    };
  }, [setAwakening]);

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      backgroundColor: "#050508",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      fontFamily: "'Share Tech Mono', monospace",
      color: "#ff0033",
      transition: "opacity 0.6s ease",
      overflow: "hidden",
    }}>
      {/* Background radial atmosphere */}
      <div style={{
        position: "absolute", width: 600, height: 600, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(255,0,51,0.2) 0%, rgba(128,0,22,0.05) 50%, transparent 70%)",
        animation: "energy-pulse 2s ease-in-out infinite",
        pointerEvents: "none",
      }} />

      {/* Awakening central glyph */}
      <div style={{
        position: "relative", width: 140, height: 140,
        display: "flex", alignItems: "center", justifyContent: "center",
        marginBottom: 30,
      }}>
        {/* Rotating ring 1 */}
        <div className="spin-cw" style={{
          position: "absolute", inset: 0,
          border: "2px solid rgba(255,0,51,0.4)",
          borderTopColor: "#ff0033",
          borderRightColor: "transparent",
          borderRadius: "50%",
        }} />

        {/* Rotating ring 2 */}
        <div className="spin-ccw" style={{
          position: "absolute", inset: 12,
          border: "1px solid rgba(255,255,255,0.3)",
          borderBottomColor: "#ffffff",
          borderLeftColor: "transparent",
          borderRadius: "50%",
        }} />

        {/* Core emblem */}
        <div style={{
          fontFamily: "'Orbitron', sans-serif",
          fontSize: 36, fontWeight: 900, letterSpacing: 4,
          color: "#ff0033",
          textShadow: "0 0 20px #ff0033, 0 0 40px rgba(255,0,51,0.8)",
        }}>
          T
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{
        width: 320, height: 3, background: "rgba(255,0,51,0.15)",
        borderRadius: 2, overflow: "hidden", marginBottom: 20,
        border: "1px solid rgba(255,0,51,0.3)",
      }}>
        <div style={{
          height: "100%",
          width: `${(stage / 5) * 100}%`,
          background: "linear-gradient(90deg, #800016, #ff0033, #ffffff)",
          boxShadow: "0 0 12px #ff0033",
          transition: "width 0.4s ease",
        }} />
      </div>

      {/* Diagnostics log feed */}
      <div style={{
        height: 80, display: "flex", flexDirection: "column",
        alignItems: "center", gap: 6, opacity: 0.85,
      }}>
        {logs.slice(-3).map((log, idx) => (
          <div key={idx} className="fade-in-scale" style={{
            fontSize: 10, letterSpacing: 2,
            color: idx === logs.length - 1 ? "#ffffff" : "rgba(255,0,51,0.7)",
            textShadow: idx === logs.length - 1 ? "0 0 8px #ffffff" : "none",
          }}>
            [SYS] {log}
          </div>
        ))}
      </div>
    </div>
  );
}

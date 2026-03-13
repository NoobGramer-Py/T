import { useTStore } from "../../store";
import { useBrainStatus } from "../../hooks/useBridge";

// ── Segmented arc stat bar ─────────────────────────────────────────────────────
function ArcBar({ value, color }: { value: number; color: string }) {
  const segs   = 12;
  const filled = Math.round((Math.min(value, 100) / 100) * segs);
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: segs }, (_, i) => (
        <div key={i} style={{
          width: 3, height: 10,
          background: i < filled ? color : "rgba(0,212,255,0.08)",
          boxShadow: i < filled ? `0 0 4px ${color}` : "none",
          borderRadius: 1,
          transition: "background 0.6s ease",
        }} />
      ))}
    </div>
  );
}

function Stat({ label, value, bar, color }: { label: string; value: string; bar: number; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "center" }}>
      <div style={{ color: "rgba(0,212,255,0.38)", fontSize: 7, letterSpacing: 4 }}>{label}</div>
      <div style={{ color, fontSize: 10, letterSpacing: 2, fontWeight: "bold", textShadow: `0 0 8px ${color}` }}>
        {value}
      </div>
      <ArcBar value={bar} color={color} />
    </div>
  );
}

function formatUptime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return `${String(h).padStart(2, "0")}h${String(m).padStart(2, "0")}m`;
}

// ── Spinning arc corner decoration ────────────────────────────────────────────
function ArcCorner({ side }: { side: "left" | "right" }) {
  const r = side === "left";
  return (
    <div style={{
      position: "absolute",
      [r ? "left" : "right"]: 0,
      top: 0, bottom: 0,
      width: 48,
      overflow: "hidden",
      display: "flex", alignItems: "center",
      justifyContent: r ? "flex-start" : "flex-end",
      pointerEvents: "none",
    }}>
      <svg width="48" height="52" style={{ opacity: 0.22 }}>
        <circle cx={r ? 0 : 48} cy="26" r="22"
          fill="none" stroke="#00d4ff" strokeWidth="1"
          strokeDasharray="14 6"
          style={{ animation: `${r ? "arc-spin" : "arc-spin-rev"} 12s linear infinite`,
            transformOrigin: `${r ? 0 : 48}px 26px` }} />
        <circle cx={r ? 0 : 48} cy="26" r="14"
          fill="none" stroke="#00d4ff" strokeWidth="0.5"
          strokeDasharray="8 10"
          style={{ animation: `${r ? "arc-spin-rev" : "arc-spin"} 8s linear infinite`,
            transformOrigin: `${r ? 0 : 48}px 26px` }} />
      </svg>
    </div>
  );
}

export function TopBar() {
  const { stats, provider, voiceEnabled, setVoiceEnabled, voiceListening } = useTStore();
  const brainStatus = useBrainStatus();

  const cpuColor  = stats.cpuPercent  > 80 ? "#ff3300" : stats.cpuPercent  > 60 ? "#ffb300" : "#00d4ff";
  const ramColor  = stats.ramPercent  > 80 ? "#ff3300" : stats.ramPercent  > 60 ? "#ffb300" : "#00d4ff";
  const diskColor = stats.diskPercent > 85 ? "#ff3300" : "#00d4ff";

  const brainOnline = brainStatus === "online";
  const brainConnecting = brainStatus === "connecting";
  const brainColor = brainOnline ? "#00ff88" : brainConnecting ? "#ffb300" : "rgba(0,212,255,0.2)";
  const brainLabel = brainOnline ? "ONLINE" : brainConnecting ? "CONNECTING" : "OFFLINE";

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0,
      height: 52, zIndex: 50,
      background: "linear-gradient(to bottom, rgba(0,6,18,0.98) 0%, rgba(0,10,21,0.85) 100%)",
      borderBottom: "1px solid rgba(0,212,255,0.12)",
      display: "flex", alignItems: "center",
      padding: "0 20px 0 72px", gap: 28,
      boxShadow: "0 1px 20px rgba(0,212,255,0.06)",
    }}>
      <ArcCorner side="left" />
      <ArcCorner side="right" />

      {/* System identifier */}
      <div style={{ display: "flex", flexDirection: "column", minWidth: 80, gap: 2 }}>
        <div style={{
          fontSize: 15, fontWeight: "bold", letterSpacing: 10,
          color: "#00d4ff",
          textShadow: "0 0 14px #00d4ff, 0 0 40px rgba(0,212,255,0.35)",
        }}>
          T
        </div>
        <div style={{ fontSize: 6, letterSpacing: 4, color: "rgba(0,212,255,0.3)" }}>
          A.I. CORE
        </div>
      </div>

      {/* Separator */}
      <div style={{ width: 1, height: 32, background: "rgba(0,212,255,0.12)" }} />

      {/* Stats */}
      <div style={{ display: "flex", gap: 24, flex: 1, alignItems: "center" }}>
        <Stat label="CPU"    value={`${stats.cpuPercent.toFixed(1)}%`}        bar={stats.cpuPercent}  color={cpuColor} />
        <Stat label="RAM"    value={`${stats.ramPercent.toFixed(1)}%`}        bar={stats.ramPercent}  color={ramColor} />
        <Stat label="DISK"   value={`${stats.diskPercent.toFixed(1)}%`}       bar={stats.diskPercent} color={diskColor} />
        <Stat label="RX"     value={`${stats.networkRxKbps.toFixed(0)} KB/s`} bar={Math.min(stats.networkRxKbps / 1000 * 100, 100)} color="#00d4ff" />
        <Stat label="TX"     value={`${stats.networkTxKbps.toFixed(0)} KB/s`} bar={Math.min(stats.networkTxKbps / 500 * 100, 100)}  color="#0088cc" />
        <Stat label="UPTIME" value={formatUptime(stats.uptime)}               bar={100} color="rgba(0,212,255,0.45)" />
      </div>

      {/* Voice toggle */}
      <button
        onClick={() => setVoiceEnabled(!voiceEnabled)}
        title={voiceEnabled ? "Disable voice" : "Enable voice"}
        style={{
          display: "flex", alignItems: "center", gap: 7,
          padding: "5px 12px", borderRadius: 2,
          background: voiceEnabled ? "rgba(0,212,255,0.08)" : "transparent",
          border: `1px solid ${voiceEnabled ? "rgba(0,212,255,0.35)" : "rgba(0,212,255,0.12)"}`,
          cursor: "pointer", transition: "all 0.2s ease",
        }}
      >
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: voiceListening ? "#00ff88" : voiceEnabled ? "#00d4ff" : "rgba(0,212,255,0.18)",
          boxShadow: voiceListening ? "0 0 8px #00ff88" : voiceEnabled ? "0 0 8px #00d4ff" : "none",
          animation: voiceListening ? "pulse-voice 1s ease-in-out infinite" : "none",
        }} />
        <span style={{ fontSize: 7, letterSpacing: 3, color: voiceEnabled ? "#00d4ff" : "rgba(0,212,255,0.32)" }}>
          {voiceListening ? "LISTENING" : voiceEnabled ? "VOICE ON" : "VOICE"}
        </span>
      </button>

      <div style={{ width: 1, height: 32, background: "rgba(0,212,255,0.12)" }} />

      {/* Provider badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <div style={{
          width: 5, height: 5, borderRadius: "50%",
          background: provider === "groq" ? "#a0f4ff" : "#00ff88",
          boxShadow: provider === "groq" ? "0 0 7px #a0f4ff" : "0 0 7px #00ff88",
        }} />
        <span style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.45)" }}>
          {provider === "groq" ? "GROQ" : "OLLAMA"}
        </span>
      </div>

      <div style={{ width: 1, height: 32, background: "rgba(0,212,255,0.12)" }} />

      {/* Brain status */}
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <div style={{
          width: 5, height: 5, borderRadius: "50%",
          background: brainColor,
          boxShadow: brainOnline ? `0 0 7px ${brainColor}` : "none",
          animation: brainConnecting ? "pulse-voice 1.2s ease-in-out infinite" : "none",
        }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <span style={{ fontSize: 6, letterSpacing: 3, color: "rgba(0,212,255,0.3)" }}>BRAIN</span>
          <span style={{ fontSize: 7, letterSpacing: 2, color: brainColor, textShadow: brainOnline ? `0 0 6px ${brainColor}` : "none" }}>
            {brainLabel}
          </span>
        </div>
      </div>
    </div>
  );
}

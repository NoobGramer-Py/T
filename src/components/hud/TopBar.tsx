import { useTStore } from "../../store";
import { useBrainStatus } from "../../hooks/useBridge";

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ width: 60, height: 3, background: "rgba(255,179,0,0.1)", borderRadius: 2, overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${Math.min(value, 100)}%`, background: color, boxShadow: `0 0 6px ${color}`, transition: "width 1s ease", borderRadius: 2 }} />
    </div>
  );
}

function Stat({ label, value, bar, color }: { label: string; value: string; bar: number; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, alignItems: "center" }}>
      <div style={{ color: "rgba(255,179,0,0.4)", fontSize: 7, letterSpacing: 4 }}>{label}</div>
      <div style={{ color, fontSize: 11, letterSpacing: 2, fontWeight: "bold", textShadow: `0 0 8px ${color}` }}>{value}</div>
      <Bar value={bar} color={color} />
    </div>
  );
}

function formatUptime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function TopBar() {
  const { stats, provider, voiceEnabled, setVoiceEnabled, voiceListening } = useTStore();
  const brainStatus = useBrainStatus();

  const cpuColor  = stats.cpuPercent  > 80 ? "#ff4400" : stats.cpuPercent  > 60 ? "#ffb300" : "#ffe566";
  const ramColor  = stats.ramPercent  > 80 ? "#ff4400" : stats.ramPercent  > 60 ? "#ffb300" : "#ffe566";
  const diskColor = stats.diskPercent > 85 ? "#ff4400" : "#ffb300";

  const brainColor = brainStatus === "online" ? "#00ff88" : brainStatus === "connecting" ? "#ffb300" : "rgba(255,179,0,0.2)";
  const brainLabel = brainStatus === "online" ? "BRAIN ONLINE" : brainStatus === "connecting" ? "BRAIN CONNECTING" : "BRAIN OFFLINE";

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0,
      height: 52, zIndex: 50,
      background: "linear-gradient(to bottom, rgba(0,4,9,0.98), rgba(0,4,9,0.6))",
      borderBottom: "1px solid rgba(255,179,0,0.1)",
      display: "flex", alignItems: "center",
      padding: "0 24px", gap: 32,
    }}>
      {/* T logo */}
      <div style={{ fontSize: 18, fontWeight: "bold", letterSpacing: 8, color: "#ffb300", textShadow: "0 0 16px #ffb300, 0 0 40px rgba(255,179,0,0.4)", minWidth: 32 }}>T</div>

      <div style={{ width: 1, height: 28, background: "rgba(255,179,0,0.12)" }} />

      {/* Stats row */}
      <div style={{ display: "flex", gap: 28, flex: 1 }}>
        <Stat label="CPU"    value={`${stats.cpuPercent.toFixed(1)}%`}         bar={stats.cpuPercent}  color={cpuColor} />
        <Stat label="RAM"    value={`${stats.ramPercent.toFixed(1)}%`}         bar={stats.ramPercent}  color={ramColor} />
        <Stat label="DISK"   value={`${stats.diskPercent.toFixed(1)}%`}        bar={stats.diskPercent} color={diskColor} />
        <Stat label="RX"     value={`${stats.networkRxKbps.toFixed(0)} KB/s`}  bar={Math.min(stats.networkRxKbps / 1000 * 100, 100)} color="#ffb300" />
        <Stat label="TX"     value={`${stats.networkTxKbps.toFixed(0)} KB/s`}  bar={Math.min(stats.networkTxKbps / 500  * 100, 100)} color="#ff6e00" />
        <Stat label="UPTIME" value={formatUptime(stats.uptime)}               bar={100}               color="rgba(255,179,0,0.5)" />
      </div>

      {/* Voice toggle */}
      <button
        onClick={() => setVoiceEnabled(!voiceEnabled)}
        title={voiceEnabled ? "Disable voice" : "Enable voice"}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "4px 10px", borderRadius: 3,
          background: voiceEnabled ? "rgba(255,179,0,0.1)" : "transparent",
          border: `1px solid ${voiceEnabled ? "rgba(255,179,0,0.4)" : "rgba(255,179,0,0.15)"}`,
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        {/* Animated mic dot */}
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: voiceListening ? "#00ff88" : voiceEnabled ? "#ffb300" : "rgba(255,179,0,0.2)",
          boxShadow: voiceListening ? "0 0 8px #00ff88" : voiceEnabled ? "0 0 8px #ffb300" : "none",
          animation: voiceListening ? "pulse-voice 1s ease-in-out infinite" : "none",
        }} />
        <span style={{ fontSize: 7, letterSpacing: 3, color: voiceEnabled ? "#ffb300" : "rgba(255,179,0,0.35)" }}>
          {voiceListening ? "LISTENING" : voiceEnabled ? "VOICE ON" : "VOICE"}
        </span>
        <style>{`
          @keyframes pulse-voice {
            0%, 100% { opacity: 1; transform: scale(1); }
            50%       { opacity: 0.5; transform: scale(1.4); }
          }
        `}</style>
      </button>

      <div style={{ width: 1, height: 28, background: "rgba(255,179,0,0.12)" }} />

      {/* Provider badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: provider === "groq" ? "#ffe566" : "#00ff88", boxShadow: provider === "groq" ? "0 0 8px #ffe566" : "0 0 8px #00ff88" }} />
        <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.5)" }}>
          {provider === "groq" ? "GROQ ONLINE" : "OLLAMA LOCAL"}
        </span>
      </div>

      <div style={{ width: 1, height: 28, background: "rgba(255,179,0,0.12)" }} />

      {/* Brain status badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: brainColor, boxShadow: brainStatus === "online" ? `0 0 8px ${brainColor}` : "none" }} />
        <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.5)" }}>{brainLabel}</span>
      </div>
    </div>
  );
}

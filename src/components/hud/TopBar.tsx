import { useTStore } from "../../store";
import { useBrainStatus } from "../../hooks/useBridge";

function ArcBar({ value, color }: { value: number; color: string }) {
  const segs   = 12;
  const filled = Math.round((Math.min(value, 100) / 100) * segs);
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: segs }, (_, i) => (
        <div key={i} style={{
          width: 3, height: 9,
          background: i < filled ? color : "rgba(255,0,51,0.08)",
          boxShadow: i < filled ? `0 0 5px ${color}` : "none",
          borderRadius: 1,
          transition: "background 0.5s ease",
        }} />
      ))}
    </div>
  );
}

function Stat({ label, value, bar, color }: { label: string; value: string; bar: number; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, alignItems: "center" }}>
      <div style={{ color: "rgba(160,170,176,0.6)", fontSize: 8, letterSpacing: 3, fontFamily: "var(--font-mono)" }}>{label}</div>
      <div style={{ color, fontSize: 11, letterSpacing: 1, fontWeight: "bold", fontFamily: "var(--font-mono)", textShadow: `0 0 8px ${color}` }}>
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

export function TopBar() {
  const { stats, provider, voiceEnabled, setVoiceEnabled, voiceListening, visualizerMode } = useTStore();
  const brainStatus = useBrainStatus();

  const cpuColor  = stats.cpuPercent  > 80 ? "#ff0033" : stats.cpuPercent  > 60 ? "#ff8800" : "#ff3355";
  const ramColor  = stats.ramPercent  > 80 ? "#ff0033" : stats.ramPercent  > 60 ? "#ff8800" : "#ff3355";
  const diskColor = stats.diskPercent > 85 ? "#ff0033" : "#ff3355";

  const brainOnline = brainStatus === "online";
  const brainConnecting = brainStatus === "connecting";
  const brainColor = brainOnline ? "#00ff66" : brainConnecting ? "#ff8800" : "rgba(255,0,51,0.3)";
  const brainLabel = brainOnline ? "ONLINE" : brainConnecting ? "CONNECTING" : "OFFLINE";

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0,
      height: 54, zIndex: 50,
      background: "linear-gradient(to bottom, rgba(5,5,8,0.98) 0%, rgba(15,10,18,0.85) 100%)",
      borderBottom: "1px solid rgba(255,0,51,0.22)",
      display: "flex", alignItems: "center",
      padding: "0 24px 0 72px", gap: 24,
      boxShadow: "0 2px 20px rgba(255,0,51,0.08)",
      backdropFilter: "blur(10px)",
    }}>

      {/* System Emblem */}
      <div style={{ display: "flex", flexDirection: "column", minWidth: 90, gap: 1 }}>
        <div style={{
          fontSize: 16, fontWeight: 900, letterSpacing: 8,
          color: "#ff0033", fontFamily: "var(--font-header)",
          textShadow: "0 0 14px #ff0033, 0 0 35px rgba(255,0,51,0.5)",
        }}>
          ULTRON
        </div>
        <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(160,170,176,0.5)", fontFamily: "var(--font-mono)" }}>
          AI OS v1.0
        </div>
      </div>

      <div style={{ width: 1, height: 32, background: "rgba(255,0,51,0.18)" }} />

      {/* Stats Cluster */}
      <div style={{ display: "flex", gap: 20, flex: 1, alignItems: "center" }}>
        <Stat label="CPU"    value={`${stats.cpuPercent.toFixed(1)}%`}        bar={stats.cpuPercent}  color={cpuColor} />
        <Stat label="RAM"    value={`${stats.ramPercent.toFixed(1)}%`}        bar={stats.ramPercent}  color={ramColor} />
        <Stat label="DISK"   value={`${stats.diskPercent.toFixed(1)}%`}       bar={stats.diskPercent} color={diskColor} />
        <Stat label="NET RX" value={`${stats.networkRxKbps.toFixed(0)} KB/s`} bar={Math.min(stats.networkRxKbps / 1000 * 100, 100)} color="#ff3355" />
        <Stat label="NET TX" value={`${stats.networkTxKbps.toFixed(0)} KB/s`} bar={Math.min(stats.networkTxKbps / 500 * 100, 100)}  color="#800016" />
        <Stat label="UPTIME" value={formatUptime(stats.uptime)}               bar={100} color="rgba(160,170,176,0.6)" />
      </div>

      {/* Interaction State Badge */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "4px 10px", borderRadius: 2,
        background: "rgba(255,0,51,0.06)",
        border: "1px solid rgba(255,0,51,0.2)",
      }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: "#ff0033", boxShadow: "0 0 8px #ff0033",
          animation: "energy-pulse 1.5s ease-in-out infinite",
        }} />
        <span style={{ fontSize: 9, letterSpacing: 2, color: "#ffffff", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>
          STATE: {visualizerMode}
        </span>
      </div>

      <div style={{ width: 1, height: 32, background: "rgba(255,0,51,0.18)" }} />

      {/* Voice Toggle */}
      <button
        onClick={() => setVoiceEnabled(!voiceEnabled)}
        title={voiceEnabled ? "Disable voice interface" : "Enable voice interface"}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "6px 14px", borderRadius: 2,
          background: voiceEnabled ? "rgba(255,0,51,0.15)" : "transparent",
          border: `1px solid ${voiceEnabled ? "#ff0033" : "rgba(255,0,51,0.2)"}`,
          cursor: "pointer", transition: "all 0.2s ease",
        }}
      >
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: voiceListening ? "#ffffff" : voiceEnabled ? "#ff0033" : "rgba(255,0,51,0.3)",
          boxShadow: voiceListening ? "0 0 10px #ffffff" : voiceEnabled ? "0 0 8px #ff0033" : "none",
        }} />
        <span style={{ fontSize: 9, letterSpacing: 2, color: voiceEnabled ? "#ffffff" : "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
          {voiceListening ? "LISTENING" : voiceEnabled ? "VOICE ON" : "VOICE"}
        </span>
      </button>

      <div style={{ width: 1, height: 32, background: "rgba(255,0,51,0.18)" }} />

      {/* Provider Badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <div style={{
          width: 5, height: 5, borderRadius: "50%",
          background: "#ff0033", boxShadow: "0 0 6px #ff0033",
        }} />
        <span style={{ fontSize: 9, letterSpacing: 2, color: "rgba(160,170,176,0.7)", fontFamily: "var(--font-mono)" }}>
          PROV: {provider.toUpperCase()}
        </span>
      </div>

      <div style={{ width: 1, height: 32, background: "rgba(255,0,51,0.18)" }} />

      {/* Brain Status */}
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: brainColor,
          boxShadow: brainOnline ? `0 0 8px ${brainColor}` : "none",
        }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <span style={{ fontSize: 6, letterSpacing: 3, color: "rgba(160,170,176,0.5)", fontFamily: "var(--font-mono)" }}>BRAIN</span>
          <span style={{ fontSize: 8, letterSpacing: 2, color: brainColor, fontFamily: "var(--font-mono)" }}>
            {brainLabel}
          </span>
        </div>
      </div>
    </div>
  );
}

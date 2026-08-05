import { useTStore } from "../../store";

export function HardwarePanel() {
  const stats = useTStore((s) => s.stats);

  const statsList = [
    { label: "CPU UTILIZATION", val: `${stats.cpuPercent.toFixed(1)}%`, pct: stats.cpuPercent, color: "#ff0033" },
    { label: "MEMORY CONSUMPTION", val: `${stats.ramPercent.toFixed(1)}%`, pct: stats.ramPercent, color: "#ff3355" },
    { label: "STORAGE ALLOCATION", val: `${stats.diskPercent.toFixed(1)}%`, pct: stats.diskPercent, color: "#800016" },
    { label: "NETWORK INBOUND (RX)", val: `${stats.networkRxKbps.toFixed(0)} KB/s`, pct: Math.min(stats.networkRxKbps / 1000 * 100, 100), color: "#ffffff" },
    { label: "NETWORK OUTBOUND (TX)", val: `${stats.networkTxKbps.toFixed(0)} KB/s`, pct: Math.min(stats.networkTxKbps / 500 * 100, 100), color: "#a0aab0" },
  ];

  return (
    <div style={{
      display: "flex", flexDirection: "column", width: "100%", height: "100%",
      backgroundColor: "var(--u-void)", padding: 32, gap: 24,
      overflowY: "auto", fontFamily: "var(--font-tech)", color: "var(--text-primary)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
            SYSTEM HARDWARE TELEMETRY
          </div>
          <div style={{ fontSize: 24, fontWeight: 900, letterSpacing: 3, color: "#ffffff", fontFamily: "var(--font-header)" }}>
            HARDWARE CONTROL MATRIX
          </div>
        </div>

        <div className="ultron-panel ultron-corner-brackets" style={{ padding: "8px 16px", borderRadius: 2 }}>
          <span style={{ fontSize: 9, letterSpacing: 3, color: "#ff0033", fontFamily: "var(--font-mono)" }}>
            UPTIME: {Math.floor(stats.uptime / 3600)}h {Math.floor((stats.uptime % 3600) / 60)}m
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}>
        {statsList.map((item, idx) => (
          <div key={idx} className="ultron-panel ultron-corner-brackets" style={{ padding: 20, borderRadius: 2 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 11, letterSpacing: 2, color: "rgba(160,170,176,0.8)", fontFamily: "var(--font-mono)" }}>
                {item.label}
              </span>
              <span style={{ fontSize: 14, fontWeight: "bold", color: item.color, fontFamily: "var(--font-mono)", textShadow: `0 0 8px ${item.color}` }}>
                {item.val}
              </span>
            </div>

            <div style={{
              width: "100%", height: 6, background: "rgba(255,0,51,0.1)",
              border: "1px solid rgba(255,0,51,0.2)", borderRadius: 1, overflow: "hidden",
            }}>
              <div style={{
                height: "100%", width: `${item.pct}%`,
                background: `linear-gradient(90deg, #800016, ${item.color})`,
                boxShadow: `0 0 10px ${item.color}`, transition: "width 0.6s ease",
              }} />
            </div>
          </div>
        ))}
      </div>

      {/* Thermals & Power Grid */}
      <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
        <div style={{ fontSize: 12, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 14 }}>
          THERMAL & VOLTAGE REGULATION
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {[
            { name: "CPU PACKAGE", val: "42°C", stat: "OPTIMAL" },
            { name: "GPU CORE", val: "39°C", stat: "NOMINAL" },
            { name: "SYSTEM RAIL", val: "12.04 V", stat: "STABLE" },
            { name: "FAN VELOCITY", val: "1850 RPM", stat: "REGULATED" },
          ].map((m, i) => (
            <div key={i} style={{ padding: 14, background: "rgba(5,5,8,0.7)", border: "1px solid rgba(255,0,51,0.15)" }}>
              <div style={{ fontSize: 8, color: "rgba(160,170,176,0.6)", letterSpacing: 2, fontFamily: "var(--font-mono)" }}>{m.name}</div>
              <div style={{ fontSize: 18, fontWeight: "bold", color: "#ffffff", fontFamily: "var(--font-mono)", margin: "4px 0" }}>{m.val}</div>
              <div style={{ fontSize: 8, color: "#00ff66", letterSpacing: 2, fontFamily: "var(--font-mono)" }}>{m.stat}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

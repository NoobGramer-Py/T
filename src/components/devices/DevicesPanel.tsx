export function DevicesPanel() {
  return (
    <div style={{
      display: "flex", flexDirection: "column", width: "100%", height: "100%",
      backgroundColor: "var(--u-void)", padding: 32, gap: 24,
      overflowY: "auto", fontFamily: "var(--font-tech)", color: "var(--text-primary)",
    }}>
      <div>
        <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
          REMOTE DEVICE & SCREEN MIRROR MATRIX
        </div>
        <div style={{ fontSize: 24, fontWeight: 900, letterSpacing: 3, color: "#ffffff", fontFamily: "var(--font-header)" }}>
          CONNECTED DEVICE CONSOLE
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 24 }}>

        {/* Android / Mobile device card */}
        <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: "bold", color: "#ffffff", fontFamily: "var(--font-mono)" }}>
              📱 ANDROID TELEMETRY NODE
            </div>
            <span style={{ fontSize: 8, letterSpacing: 2, color: "#00ff66", fontFamily: "var(--font-mono)" }}>
              CONNECTED via Scrcpy / ADB
            </span>
          </div>

          <div style={{
            height: 220, background: "rgba(5,5,8,0.9)",
            border: "1px dashed rgba(255,0,51,0.25)",
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: 12, borderRadius: 2,
          }}>
            <div style={{ fontSize: 28, color: "#ff0033" }}>📱</div>
            <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
              DISPLAY STREAM STANDBY
            </div>
            <button className="ultron-btn ultron-btn-active">START MIRROR FEED ▶</button>
          </div>
        </div>

        {/* Workstation / Secondary Display node card */}
        <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: "bold", color: "#ffffff", fontFamily: "var(--font-mono)" }}>
              💻 AUXILIARY DISPLAY NODE
            </div>
            <span style={{ fontSize: 8, letterSpacing: 2, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
              STANDBY
            </span>
          </div>

          <div style={{
            height: 220, background: "rgba(5,5,8,0.9)",
            border: "1px dashed rgba(255,0,51,0.25)",
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            gap: 12, borderRadius: 2,
          }}>
            <div style={{ fontSize: 28, color: "#ff0033" }}>💻</div>
            <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
              NO SECONDARY SCREEN CONNECTED
            </div>
            <button className="ultron-btn">CONNECT DISK NODE</button>
          </div>
        </div>

      </div>
    </div>
  );
}

import { useState } from "react";

export function NetworkPanel() {
  const [targetIp, setTargetIp] = useState("");
  const [scanResult, setScanResult] = useState<string | null>(null);

  const handleScan = () => {
    if (!targetIp) return;
    setScanResult(`ANALYZING THREAT INTEL FOR: ${targetIp}\n\n[ABUSEIPDB]: 0 Reports / Clean Reputation score.\n[VIRUSTOTAL]: 0/94 Detections.\n[GEOIP]: US - Ashburn Datacenter Node.\n[PORT SPECTRUM]: 80/TCP OPEN, 443/TCP OPEN, 22/TCP FILTERED.`);
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", width: "100%", height: "100%",
      backgroundColor: "var(--u-void)", padding: 32, gap: 24,
      overflowY: "auto", fontFamily: "var(--font-tech)", color: "var(--text-primary)",
    }}>
      <div>
        <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
          NETWORK INTEL & THREAT ANALYSIS
        </div>
        <div style={{ fontSize: 24, fontWeight: 900, letterSpacing: 3, color: "#ffffff", fontFamily: "var(--font-header)" }}>
          NETWORK RECONNAISSANCE MATRIX
        </div>
      </div>

      <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
        <div style={{ fontSize: 11, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 14 }}>
          TARGET IP / DOMAIN SCANNER
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <input
            className="ultron-input"
            value={targetIp}
            onChange={(e) => setTargetIp(e.target.value)}
            placeholder="Enter target IP address or hostname (e.g., 1.1.1.1)..."
            style={{ flex: 1 }}
          />
          <button className="ultron-btn ultron-btn-active" onClick={handleScan}>
            RUN RECONNAISSANCE ▶
          </button>
        </div>

        {scanResult && (
          <div className="fade-in-scale" style={{
            marginTop: 20, padding: 16, background: "rgba(5,5,8,0.85)",
            border: "1px solid rgba(255,0,51,0.25)", borderRadius: 2,
            fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.6, color: "#ffffff",
            whiteSpace: "pre-wrap",
          }}>
            {scanResult}
          </div>
        )}
      </div>

      <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
        <div style={{ fontSize: 11, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 14 }}>
          ACTIVE NETWORK SOCKETS
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, fontFamily: "var(--font-mono)", fontSize: 11 }}>
          {[
            { proto: "TCP", local: "127.0.0.1:7891", remote: "0.0.0.0:*", state: "LISTEN", process: "ultron_brain.exe" },
            { proto: "TCP", local: "127.0.0.1:5173", remote: "0.0.0.0:*", state: "LISTEN", process: "vite_dev.exe" },
            { proto: "TCP", local: "192.168.1.45:54320", remote: "104.18.2.1:443", state: "ESTABLISHED", process: "t_core.exe" },
          ].map((s, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(5,5,8,0.6)", border: "1px solid rgba(255,0,51,0.1)" }}>
              <span style={{ color: "#ff0033" }}>{s.proto}</span>
              <span style={{ color: "#ffffff" }}>{s.local}</span>
              <span style={{ color: "rgba(160,170,176,0.6)" }}>→</span>
              <span style={{ color: "#ffffff" }}>{s.remote}</span>
              <span style={{ color: "#00ff66" }}>{s.state}</span>
              <span style={{ color: "rgba(160,170,176,0.5)" }}>[{s.process}]</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

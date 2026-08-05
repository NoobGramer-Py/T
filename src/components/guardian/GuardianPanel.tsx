import { useState } from "react";

export function GuardianPanel() {
  const [activeTool, setActiveTool] = useState<string>("ports");
  const [output, setOutput] = useState<string>("");

  const runTool = (name: string) => {
    setActiveTool(name);
    setOutput(`[GUARDIAN MATRIX] INITIATING DEFENSIVE DIAGNOSTIC: ${name.toUpperCase()}\n\n✓ FIREWALL POLICY: ACTIVE (DEFAULT DENY INBOUND)\n✓ PROCESS INTEGRITY: VERIFIED\n✓ ANOMALY DETECTOR: 0 HOST INTRUSIONS DETECTED\n✓ ENCRYPTION MATRIX: AES-256 GCM ENFORCED`);
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", width: "100%", height: "100%",
      backgroundColor: "var(--u-void)", padding: 32, gap: 24,
      overflowY: "auto", fontFamily: "var(--font-tech)", color: "var(--text-primary)",
    }}>
      <div>
        <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
          CYBER DEFENSE & SECURITY MATRIX
        </div>
        <div style={{ fontSize: 24, fontWeight: 900, letterSpacing: 3, color: "#ffffff", fontFamily: "var(--font-header)" }}>
          GUARDIAN SYSTEM SHIELD
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 24 }}>

        {/* Tools Selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { id: "ports", name: "PORT & SERVICE AUDIT" },
            { id: "hashes", name: "MALWARE HASH SCAN" },
            { id: "headers", name: "HTTP SECURITY HEADERS" },
            { id: "passwords", name: "CREDENTIAL LEAK CHECK" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => runTool(t.id)}
              className={`ultron-btn ${activeTool === t.id ? "ultron-btn-active" : ""}`}
              style={{ justifyContent: "flex-start" }}
            >
              🛡 {t.name}
            </button>
          ))}
        </div>

        {/* Execution Output */}
        <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2, minHeight: 300 }}>
          <div style={{ fontSize: 11, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 14 }}>
            GUARDIAN DEFENSIVE CONSOLE OUTPUT
          </div>

          <div style={{
            background: "rgba(5,5,8,0.9)", border: "1px solid rgba(255,0,51,0.2)",
            padding: 16, borderRadius: 2, minHeight: 220,
            fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.6, color: "#ffffff",
            whiteSpace: "pre-wrap",
          }}>
            {output || "Select a defensive security module to execute system audit."}
          </div>
        </div>

      </div>
    </div>
  );
}

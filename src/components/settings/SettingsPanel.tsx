import { useTStore } from "../../store";

export function SettingsPanel() {
  const { profile, setProfile, provider, setProvider } = useTStore();

  return (
    <div style={{
      display: "flex", flexDirection: "column", width: "100%", height: "100%",
      backgroundColor: "var(--u-void)", padding: 32, gap: 24,
      overflowY: "auto", fontFamily: "var(--font-tech)", color: "var(--text-primary)",
    }}>
      <div>
        <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
          SYSTEM CONFIGURATION & API KEYS
        </div>
        <div style={{ fontSize: 24, fontWeight: 900, letterSpacing: 3, color: "#ffffff", fontFamily: "var(--font-header)" }}>
          ULTRON CONFIGURATION STORE
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>

        {/* AI Provider & API Keys */}
        <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
          <div style={{ fontSize: 12, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 16 }}>
            NEURAL ENGINE PROVIDER
          </div>

          <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
            <button
              onClick={() => setProvider("groq")}
              className={`ultron-btn ${provider === "groq" ? "ultron-btn-active" : ""}`}
              style={{ flex: 1, justifyContent: "center" }}
            >
              GROQ CLOUD (FAST)
            </button>
            <button
              onClick={() => setProvider("ollama")}
              className={`ultron-btn ${provider === "ollama" ? "ultron-btn-active" : ""}`}
              style={{ flex: 1, justifyContent: "center" }}
            >
              OLLAMA LOCAL (OFFLINE)
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <div style={{ fontSize: 9, color: "rgba(160,170,176,0.7)", letterSpacing: 2, fontFamily: "var(--font-mono)", marginBottom: 4 }}>
                GROQ API KEY
              </div>
              <input
                type="password"
                className="ultron-input"
                style={{ width: "100%" }}
                value={profile.groqKey || ""}
                onChange={(e) => setProfile({ groqKey: e.target.value })}
                placeholder="gsk_..."
              />
            </div>

            <div>
              <div style={{ fontSize: 9, color: "rgba(160,170,176,0.7)", letterSpacing: 2, fontFamily: "var(--font-mono)", marginBottom: 4 }}>
                VIRUSTOTAL API KEY
              </div>
              <input
                type="password"
                className="ultron-input"
                style={{ width: "100%" }}
                value={profile.virusTotalKey || ""}
                onChange={(e) => setProfile({ virusTotalKey: e.target.value })}
                placeholder="vt_key..."
              />
            </div>
          </div>
        </div>

        {/* User Identity & VM Configuration */}
        <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
          <div style={{ fontSize: 12, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 16 }}>
            OPERATOR IDENTITY & LAB VM
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <div style={{ fontSize: 9, color: "rgba(160,170,176,0.7)", letterSpacing: 2, fontFamily: "var(--font-mono)", marginBottom: 4 }}>
                OPERATOR DESIGNATION / NAME
              </div>
              <input
                type="text"
                className="ultron-input"
                style={{ width: "100%" }}
                value={profile.name || ""}
                onChange={(e) => setProfile({ name: e.target.value })}
                placeholder="Operator"
              />
            </div>

            <div>
              <div style={{ fontSize: 9, color: "rgba(160,170,176,0.7)", letterSpacing: 2, fontFamily: "var(--font-mono)", marginBottom: 4 }}>
                LAB VM IP ADDRESS
              </div>
              <input
                type="text"
                className="ultron-input"
                style={{ width: "100%" }}
                value={profile.vmIp || ""}
                onChange={(e) => setProfile({ vmIp: e.target.value })}
                placeholder="192.168.1.100"
              />
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

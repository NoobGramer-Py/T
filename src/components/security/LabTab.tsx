import { useState } from "react";
import { useLab, type LabDevice, type LabCred, type RatResult, type LabStep } from "../../hooks/useBridge";

const J   = "#00d4ff";
const DIM = "rgba(0,212,255,0.35)";
const CARD: React.CSSProperties = {
  background: "rgba(0,212,255,0.02)",
  border: "1px solid rgba(0,212,255,0.09)",
  borderRadius: 4, padding: "14px 16px",
};

const STEP_LABELS: Record<string, string> = {
  recon:        "1 · NETWORK RECON",
  router:       "2 · ROUTER EXPLOIT",
  pivot:        "3 · PIVOT",
  payload:      "4 · ANDROID RAT",
  phishing:     "5 · PHISHING",
  ducky:        "6 · RUBBER DUCKY",
  post_exploit: "7 · POST-EXPLOIT",
  report:       "8 · REPORT",
};

const STEP_COLOR: Record<string, string> = {
  pending: "rgba(0,212,255,0.2)",
  running: "#ffb300",
  done:    "#00ff88",
  failed:  "#ff3300",
  skipped: "rgba(0,212,255,0.25)",
};

const PHISH_TEMPLATES = [
  { id: "google",    label: "Google"    },
  { id: "facebook",  label: "Facebook"  },
  { id: "instagram", label: "Instagram" },
  { id: "whatsapp",  label: "WhatsApp"  },
  { id: "gmail",     label: "Gmail"     },
  { id: "microsoft", label: "Microsoft" },
];

function Btn({ label, onClick, danger = false, disabled = false, glow = false }: {
  label: string; onClick: () => void;
  danger?: boolean; disabled?: boolean; glow?: boolean;
}) {
  const c = danger ? "#ff3300" : glow ? "#00ff88" : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 14px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${danger?"255,51,0":glow?"0,255,136":"0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.1)" : `rgba(${danger?"255,51,0":glow?"0,255,136":"0,212,255"},0.3)`}`,
      color: disabled ? "rgba(0,212,255,0.2)" : c,
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", whiteSpace: "nowrap" as const,
      boxShadow: glow && !disabled ? `0 0 10px rgba(0,255,136,0.2)` : "none",
    }}>{label}</button>
  );
}

function Input({ label, value, onChange, placeholder = "", type = "text" }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>{label}</div>
      <input type={type} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: "100%", background: "rgba(0,212,255,0.03)",
          border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
          padding: "6px 10px", color: "rgba(160,244,255,0.9)",
          fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: J,
        }}
        onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
        onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
      />
    </div>
  );
}

// ── Step tracker ──────────────────────────────────────────────────────────────

function StepTracker({ steps }: { steps: Record<string, LabStep> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {Object.entries(STEP_LABELS).map(([id, label]) => {
        const step = steps[id] || { status: "pending", message: "" };
        const color = STEP_COLOR[step.status] || DIM;
        const isRunning = step.status === "running";
        return (
          <div key={id} style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "6px 10px",
            background: isRunning ? "rgba(255,179,0,0.04)" : "rgba(0,212,255,0.01)",
            border: `1px solid ${isRunning ? "rgba(255,179,0,0.15)" : "rgba(0,212,255,0.06)"}`,
            borderRadius: 3,
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
              background: color,
              boxShadow: step.status === "done" ? `0 0 6px ${color}` : "none",
              animation: isRunning ? "pulse-voice 1s ease-in-out infinite" : "none",
            }} />
            <span style={{ fontSize: 8, letterSpacing: 2, color, minWidth: 160 }}>{label}</span>
            <span style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", flex: 1 }}>
              {step.message}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Network map ───────────────────────────────────────────────────────────────

function NetworkMap({ devices }: { devices: LabDevice[] }) {
  const TYPE_ICON: Record<string, string> = {
    router: "🛡", android: "📱", windows: "🖥", linux: "🐧",
    ios: "📱", camera: "📷", iot_mqtt: "🏠", unknown: "❓",
  };
  const TYPE_COLOR: Record<string, string> = {
    router: "#ff6600", android: "#00ff88", windows: "#00d4ff",
    linux: "#a0f4ff", ios: "#a0a0ff", camera: "#ff00ff",
    iot_mqtt: "#ffb300", unknown: "rgba(0,212,255,0.3)",
  };

  if (devices.length === 0) {
    return (
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic", padding: "10px 0" }}>
        No devices found yet. Start a lab session to scan the network.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {devices.map(d => {
        const color = TYPE_COLOR[d.device_type] || DIM;
        const icon  = TYPE_ICON[d.device_type] || "❓";
        return (
          <div key={d.ip} style={{
            ...CARD, minWidth: 160, flex: "1 1 160px",
            borderColor: `rgba(${color === "#00ff88" ? "0,255,136" : "0,212,255"},0.15)`,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
              <span style={{ fontSize: 14 }}>{icon}</span>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, boxShadow: `0 0 5px ${color}` }} />
              <span style={{ fontSize: 10, color, fontWeight: 600 }}>{d.ip}</span>
            </div>
            <div style={{ fontSize: 8, color: "rgba(0,212,255,0.5)", letterSpacing: 2, marginBottom: 3 }}>
              {d.device_type.toUpperCase()}
            </div>
            {d.hostname && <div style={{ fontSize: 9, color: "rgba(0,212,255,0.6)" }}>{d.hostname}</div>}
            {d.os_hint  && <div style={{ fontSize: 8, color: "rgba(0,212,255,0.4)" }}>{d.os_hint.slice(0, 40)}</div>}
            {d.open_ports.length > 0 && (
              <div style={{ fontSize: 8, color: "rgba(0,212,255,0.35)", marginTop: 4 }}>
                {d.open_ports.slice(0, 8).join(", ")}{d.open_ports.length > 8 ? "…" : ""}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Credential feed ───────────────────────────────────────────────────────────

function CredFeed({ creds }: { creds: LabCred[] }) {
  if (creds.length === 0) return (
    <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic" }}>
      Phishing server active. Waiting for credentials...
    </div>
  );
  return (
    <div style={{ maxHeight: 200, overflowY: "auto" }}>
      {creds.map((c, i) => (
        <div key={i} style={{
          display: "flex", gap: 10, padding: "6px 10px", marginBottom: 3,
          background: "rgba(0,255,136,0.03)", border: "1px solid rgba(0,255,136,0.12)",
          borderRadius: 3, fontSize: 10, fontFamily: "monospace", alignItems: "center",
        }}>
          <span style={{ color: "rgba(0,212,255,0.4)", minWidth: 60 }}>{c.ts}</span>
          <span style={{ color: "rgba(0,212,255,0.5)", minWidth: 100 }}>{c.ip}</span>
          <span style={{ color: "#a0f4ff", minWidth: 140 }}>{c.username}</span>
          <span style={{ color: "#ff6600", fontWeight: 600 }}>{c.password}</span>
        </div>
      ))}
    </div>
  );
}

// ── RAT control ───────────────────────────────────────────────────────────────

function RatControl({ onAction, sessionOpen }: {
  onAction: (action: string, params?: Record<string, unknown>) => void;
  sessionOpen: boolean;
}) {
  const [filePath,    setFilePath]    = useState("/sdcard/DCIM");
  const [shellCmd,    setShellCmd]    = useState("id");
  const [micDuration, setMicDuration] = useState("10");
  const [pid,         setPid]         = useState("");

  if (!sessionOpen) return (
    <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic" }}>
      No active Meterpreter session. Install the payload APK on the target device and wait for callback.
    </div>
  );

  return (
    <div>
      {/* Surveillance */}
      <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 10 }}>SURVEILLANCE</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
        <Btn label="📷 PHOTO (front)"  onClick={() => onAction("webcam_snap", { camera: 2 })} />
        <Btn label="📷 PHOTO (back)"   onClick={() => onAction("webcam_snap", { camera: 1 })} />
        <Btn label="📍 GPS LOCATION"   onClick={() => onAction("geolocate")} />
        <Btn label={`🎤 RECORD ${micDuration}s`} onClick={() => onAction("record_mic", { duration: parseInt(micDuration) })} />
        <input value={micDuration} onChange={e => setMicDuration(e.target.value)}
          style={{ width: 40, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "4px 6px", color: J, fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: J }}
          onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
      </div>

      {/* Data extraction */}
      <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 10 }}>DATA EXTRACTION</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
        <Btn label="💬 DUMP SMS"       onClick={() => onAction("dump_sms")} danger />
        <Btn label="👥 DUMP CONTACTS"  onClick={() => onAction("dump_contacts")} danger />
        <Btn label="📞 CALL LOG"       onClick={() => onAction("dump_call_log")} danger />
        <Btn label="⌨️ KEYLOG DUMP"    onClick={() => onAction("keylogger_dump")} danger />
        <Btn label="📦 EXFIL ALL"      onClick={() => onAction("exfil_all")} danger />
      </div>

      {/* File system */}
      <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 8 }}>FILE SYSTEM</div>
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        <input value={filePath} onChange={e => setFilePath(e.target.value)}
          style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: J }}
          onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
        <Btn label="LIST"     onClick={() => onAction("browse_files", { path: filePath })} />
        <Btn label="DOWNLOAD" onClick={() => onAction("download_file", { path: filePath })} />
      </div>

      {/* Shell */}
      <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 8 }}>SHELL</div>
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        <input value={shellCmd} onChange={e => setShellCmd(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") onAction("shell", { command: shellCmd }); }}
          style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: J }}
          onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
        <Btn label="RUN" onClick={() => onAction("shell", { command: shellCmd })} />
      </div>

      {/* Windows post-exploit */}
      <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 8 }}>WINDOWS POST-EXPLOIT</div>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <Btn label="HASHDUMP" onClick={() => onAction("hashdump")} danger />
        <input value={pid} onChange={e => setPid(e.target.value)}
          placeholder="PID" style={{ width: 70, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: J, fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: J }}
          onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
        <Btn label="MIGRATE" onClick={() => onAction("migrate", { pid: parseInt(pid) })} />
      </div>
    </div>
  );
}

// ── RAT results (media + data) ────────────────────────────────────────────────

function RatResults({ results }: { results: RatResult[] }) {
  if (results.length === 0) return null;
  return (
    <div>
      <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 10 }}>SESSION OUTPUT</div>
      {results.map((r, i) => (
        <div key={i} style={{ ...CARD, marginBottom: 8 }}>
          <div style={{ fontSize: 8, letterSpacing: 3, color: J, marginBottom: 6 }}>
            {r.action.toUpperCase().replace("_", " ")}
            {r.error && <span style={{ color: "#ff3300", marginLeft: 10 }}>FAILED</span>}
          </div>
          {r.error && <div style={{ fontSize: 10, color: "#ff4400" }}>{r.error}</div>}
          {r.media_type === "image" && r.b64 && (
            <img src={`data:image/jpeg;base64,${r.b64}`}
              alt="device camera"
              style={{ maxWidth: "100%", borderRadius: 3, border: "1px solid rgba(0,212,255,0.15)" }}
            />
          )}
          {r.media_type === "audio" && r.b64 && (
            <audio controls style={{ width: "100%", marginTop: 4 }}>
              <source src={`data:audio/wav;base64,${r.b64}`} type="audio/wav" />
            </audio>
          )}
          {r.lat && r.lon && (
            <div style={{ fontSize: 10, color: "#00ff88" }}>
              📍 Lat: {r.lat} · Lon: {r.lon}
              <a href={`https://maps.google.com/?q=${r.lat},${r.lon}`}
                target="_blank" rel="noreferrer"
                style={{ color: J, marginLeft: 10, fontSize: 9 }}>
                Open Maps
              </a>
            </div>
          )}
          {r.data && (
            <pre style={{
              fontSize: 9, color: "rgba(0,212,255,0.7)", whiteSpace: "pre-wrap",
              wordBreak: "break-all", maxHeight: 200, overflowY: "auto",
              background: "rgba(0,212,255,0.02)", padding: "8px", borderRadius: 2, marginTop: 4,
            }}>{r.data.slice(0, 2000)}{r.data.length > 2000 ? "\n…" : ""}</pre>
          )}
          {r.path && <div style={{ fontSize: 8, color: DIM, marginTop: 4 }}>Saved: {r.path}</div>}
          {r.size_kb && <div style={{ fontSize: 8, color: DIM, marginTop: 4 }}>Size: {r.size_kb} KB</div>}
        </div>
      ))}
    </div>
  );
}

// ── Stream log ────────────────────────────────────────────────────────────────

function StreamLog({ lines, filterStep }: {
  lines: { step: string; chunk: string; ts: number }[];
  filterStep?: string;
}) {
  const filtered = filterStep ? lines.filter(l => l.step === filterStep) : lines;
  if (filtered.length === 0) return null;
  return (
    <div style={{
      background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
      borderRadius: 3, padding: "10px 12px", maxHeight: 220, overflowY: "auto",
      fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.7)", lineHeight: 1.55,
    }}>
      {filtered.map((l, i) => (
        <div key={i} style={{
          color: l.chunk.startsWith("[ERROR]") ? "#ff4400" :
                 l.chunk.includes("ACCESS GRANTED") || l.chunk.includes("Meterpreter session") ? "#00ff88" : undefined,
        }}>{l.chunk}</div>
      ))}
    </div>
  );
}

// ── Main LabTab ───────────────────────────────────────────────────────────────

export function LabTab() {
  const lab = useLab();

  const [subnet,    setSubnet]    = useState("192.168.1.0/24");
  const [lhost,     setLhost]     = useState("");
  const [lport,     setLport]     = useState("4444");
  const [phishTmpl, setPhishTmpl] = useState("google");
  const [phishUrl,  setPhishUrl]  = useState("");
  const [stepsSelected, setStepsSelected] = useState<string[]>(
    ["recon","router","payload","phishing","ducky"]
  );
  const [section, setSection] = useState<"config"|"status"|"rat"|"phish"|"report">("config");

  const toggleStep = (id: string) =>
    setStepsSelected(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );

  const launch = () => {
    lab.startLab({
      subnet, lhost, lport,
      phish_template: phishTmpl,
      phish_url:      phishUrl,
      steps:          stepsSelected,
    });
    setSection("status");
  };

  const SECTIONS = [
    { id: "config", label: "CONFIG"  },
    { id: "status", label: "STATUS"  },
    { id: "rat",    label: "RAT"     },
    { id: "phish",  label: "PHISHING"},
    { id: "report", label: "REPORT"  },
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{
        padding: "12px 20px 0",
        borderBottom: "1px solid rgba(0,212,255,0.08)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 10 }}>
          <div style={{ fontSize: 9, letterSpacing: 6, color: lab.active ? "#00ff88" : DIM }}>
            T · RED TEAM LAB
          </div>
          {lab.active && (
            <div style={{
              width: 7, height: 7, borderRadius: "50%", background: "#00ff88",
              boxShadow: "0 0 8px #00ff88", animation: "pulse-voice 1.2s ease-in-out infinite",
            }} />
          )}
          {lab.sessionOpen && (
            <div style={{
              padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
              background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.3)",
              color: "#00ff88",
            }}>SESSION ACTIVE</div>
          )}
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            {!lab.active
              ? <Btn label="▶ LAUNCH" onClick={launch} glow />
              : <Btn label="■ STOP + REPORT" onClick={lab.stopLab} danger />
            }
          </div>
        </div>

        {/* Section tabs */}
        <div style={{ display: "flex", gap: 2 }}>
          {SECTIONS.map(s => (
            <button key={s.id} onClick={() => setSection(s.id as typeof section)} style={{
              padding: "5px 12px", fontSize: 7, letterSpacing: 3, background: "transparent",
              border: "none",
              borderBottom: `2px solid ${section === s.id ? J : "transparent"}`,
              color: section === s.id ? J : "rgba(0,212,255,0.3)",
              cursor: "pointer", fontFamily: "inherit",
            }}>{s.label}</button>
          ))}
        </div>
      </div>

      {/* Error bar */}
      {lab.error && (
        <div style={{
          flexShrink: 0, margin: "8px 20px 0",
          background: "rgba(255,51,0,0.07)", border: "1px solid rgba(255,51,0,0.2)",
          borderRadius: 3, padding: "8px 12px", fontSize: 10, color: "#ff4400",
          display: "flex", justifyContent: "space-between",
        }}>
          <span>{lab.error}</span>
          <button onClick={lab.clearError} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

        {/* ── CONFIG ── */}
        {section === "config" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
              <div>
                <Input label="TARGET SUBNET"   value={subnet} onChange={setSubnet} placeholder="192.168.1.0/24" />
                <Input label="LHOST (your IP)" value={lhost}  onChange={setLhost}  placeholder="192.168.1.100" />
                <Input label="LPORT"           value={lport}  onChange={setLport}  placeholder="4444" />
              </div>
              <div>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 8 }}>ATTACK STEPS</div>
                {Object.entries(STEP_LABELS).filter(([id]) => id !== "report" && id !== "pivot" && id !== "post_exploit").map(([id, label]) => (
                  <label key={id} style={{
                    display: "flex", alignItems: "center", gap: 8,
                    marginBottom: 6, cursor: "pointer", fontSize: 9, color: "rgba(0,212,255,0.7)",
                  }}>
                    <input type="checkbox"
                      checked={stepsSelected.includes(id)}
                      onChange={() => toggleStep(id)}
                      style={{ accentColor: J }}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            {/* Phishing config */}
            {stepsSelected.includes("phishing") && (
              <div style={{ ...CARD, marginBottom: 16 }}>
                <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>PHISHING PAGE</div>
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 6 }}>TEMPLATE</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {PHISH_TEMPLATES.map(t => (
                      <button key={t.id} onClick={() => setPhishTmpl(t.id)} style={{
                        padding: "4px 10px", fontSize: 8, borderRadius: 2,
                        background: phishTmpl === t.id ? "rgba(0,212,255,0.1)" : "transparent",
                        border: `1px solid ${phishTmpl === t.id ? "rgba(0,212,255,0.4)" : "rgba(0,212,255,0.1)"}`,
                        color: phishTmpl === t.id ? J : DIM,
                        cursor: "pointer", fontFamily: "inherit",
                      }}>{t.label}</button>
                    ))}
                  </div>
                </div>
                <Input label="OR CLONE THIS URL (leave blank to use template)"
                  value={phishUrl} onChange={setPhishUrl}
                  placeholder="https://target-site.com" />
              </div>
            )}

            <div style={{
              background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)",
              borderRadius: 3, padding: "10px 14px", fontSize: 9,
              color: "rgba(255,179,0,0.65)", lineHeight: 1.7,
            }}>
              ⚠ This lab runs against your own devices only. T requires LHOST to be your PC's
              local IP so the VM can reach it. Make sure your attack VM is running and SSH is
              configured before launching.
            </div>
          </div>
        )}

        {/* ── STATUS ── */}
        {section === "status" && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 12 }}>ATTACK CHAIN</div>
              <StepTracker steps={lab.steps} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                NETWORK MAP — {lab.devices.length} DEVICE{lab.devices.length !== 1 ? "S" : ""} FOUND
              </div>
              <NetworkMap devices={lab.devices} />
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 8 }}>LIVE LOG</div>
              <StreamLog lines={lab.streamLines} />
            </div>
          </div>
        )}

        {/* ── RAT ── */}
        {section === "rat" && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                METERPRETER SESSION CONTROL
              </div>
              <RatControl
                onAction={(action, params) => lab.ratAction(action, params)}
                sessionOpen={lab.sessionOpen}
              />
            </div>
            <div style={{ marginTop: 20 }}>
              <RatResults results={lab.ratResults} />
            </div>
          </div>
        )}

        {/* ── PHISHING ── */}
        {section === "phish" && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <div style={{ fontSize: 7, letterSpacing: 4, color: DIM }}>CREDENTIAL FEED</div>
              <div style={{
                width: 6, height: 6, borderRadius: "50%",
                background: lab.active ? "#00ff88" : "rgba(0,212,255,0.2)",
                boxShadow: lab.active ? "0 0 6px #00ff88" : "none",
                animation: lab.active ? "pulse-voice 1.2s ease-in-out infinite" : "none",
              }} />
              <span style={{ fontSize: 8, color: DIM }}>
                {lab.active ? "SERVER ACTIVE" : "SERVER STOPPED"}
              </span>
              {lab.active && <Btn label="STOP SERVER" onClick={lab.stopPhishing} danger />}
            </div>
            <CredFeed creds={lab.creds} />

            {lab.creds.length > 0 && (
              <div style={{
                marginTop: 12, padding: "8px 12px",
                background: "rgba(0,255,136,0.04)", border: "1px solid rgba(0,255,136,0.15)",
                borderRadius: 3, fontSize: 9, color: "#00ff88",
              }}>
                {lab.creds.length} credential{lab.creds.length !== 1 ? "s" : ""} captured
              </div>
            )}
          </div>
        )}

        {/* ── REPORT ── */}
        {section === "report" && (
          <div>
            {!lab.reportReady ? (
              <div style={{ fontSize: 9, color: DIM, fontStyle: "italic" }}>
                Stop the lab session to generate the penetration test report.
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                  PENETRATION TEST REPORT
                </div>
                <iframe
                  srcDoc={lab.reportHtml}
                  style={{
                    width: "100%", height: 600, border: "1px solid rgba(0,212,255,0.12)",
                    borderRadius: 4, background: "#000a15",
                  }}
                  title="Pentest Report"
                />
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

import { useState } from "react";
import { useOffensive } from "../../hooks/useBridge";

const J    = "#00d4ff";
const DIM  = "rgba(0,212,255,0.35)";
const WARN = "#ff6600";
const CRIT = "#ff2200";

const RISK_COLOR: Record<string, string> = {
  LOW:      "#00cc66",
  MEDIUM:   J,
  HIGH:     WARN,
  CRITICAL: CRIT,
};

function Btn({ label, onClick, risk = "MEDIUM", disabled = false }: {
  label: string; onClick: () => void; risk?: string; disabled?: boolean;
}) {
  const c = RISK_COLOR[risk] || J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "6px 14px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${risk === "CRITICAL" ? "255,34,0" : risk === "HIGH" ? "255,102,0" : "0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.08)" : c + "55"}`,
      color: disabled ? "rgba(0,212,255,0.2)" : c,
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", whiteSpace: "nowrap" as const,
    }}>{label}</button>
  );
}

function Input({ label, value, onChange, placeholder = "" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>{label}</div>
      <input value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} style={{
          width: "100%", background: "rgba(0,212,255,0.03)",
          border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
          padding: "6px 10px", color: "rgba(160,244,255,0.9)",
          fontSize: 10, fontFamily: "monospace", outline: "none", caretColor: J,
        }} />
    </div>
  );
}

function Section({ title, risk, children }: {
  title: string; risk: string; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div style={{
      background: "rgba(0,212,255,0.015)", border: "1px solid rgba(0,212,255,0.07)",
      borderRadius: 4, marginBottom: 12, overflow: "hidden",
    }}>
      <div onClick={() => setOpen(o => !o)} style={{
        display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
        cursor: "pointer", borderBottom: open ? "1px solid rgba(0,212,255,0.06)" : "none",
      }}>
        <div style={{
          padding: "2px 8px", fontSize: 6, letterSpacing: 3,
          border: `1px solid ${RISK_COLOR[risk]}`, color: RISK_COLOR[risk], borderRadius: 2,
        }}>{risk}</div>
        <span style={{ fontSize: 9, letterSpacing: 3, color: "rgba(160,244,255,0.8)" }}>{title}</span>
        <span style={{ marginLeft: "auto", fontSize: 8, color: DIM }}>{open ? "▲" : "▼"}</span>
      </div>
      {open && <div style={{ padding: "14px 16px" }}>{children}</div>}
    </div>
  );
}

export function StealthTab() {
  const off = useOffensive();

  const [session,    setSession]    = useState("1");
  const [osType,     setOsType]     = useState<"windows"|"linux">("windows");
  const [payloadPath,setPayloadPath]= useState("/tmp/payload.exe");
  const [encTech,    setEncTech]    = useState<"xor"|"base64"|"shikata">("xor");
  const [lhost,      setLhost]      = useState("");
  const [lport,      setLport]      = useState("443");
  const [platform,   setPlatform]   = useState<"windows"|"linux"|"android">("windows");
  const [targetProc, setTargetProc] = useState("explorer.exe");
  const [tsPath,     setTsPath]     = useState("C:\\Windows\\Temp\\*.exe");
  const [psCommand,  setPsCommand]  = useState("whoami; ipconfig");
  const [dlUrl,      setDlUrl]      = useState("");
  const [dlOut,      setDlOut]      = useState("C:\\Windows\\Temp\\file.exe");
  const [dnsDomain,  setDnsDomain]  = useState("");
  const [dnsLhost,   setDnsLhost]   = useState("");

  const dispatch = (tool: string, params: Record<string, unknown>) => off.dispatch(tool, params);

  // Collect output lines for this session
  const outputText = off.streamLines.map(l => l.chunk).join("\n");

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>

      {/* Header */}
      <div style={{
        padding: "12px 20px 10px", borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0,
      }}>
        <div style={{ fontSize: 9, letterSpacing: 6, color: DIM, marginBottom: 4 }}>
          T · PHASE 13 — STEALTH & EVASION
        </div>
        <div style={{ fontSize: 8, color: "rgba(255,102,0,0.6)", letterSpacing: 1 }}>
          ⚠ Authorized penetration testing only
        </div>
      </div>

      {/* Shared controls bar */}
      <div style={{
        padding: "10px 20px", flexShrink: 0,
        borderBottom: "1px solid rgba(0,212,255,0.06)",
        display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap",
      }}>
        <div>
          <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>SESSION</div>
          <input value={session} onChange={e => setSession(e.target.value)} style={{
            width: 60, background: "rgba(0,212,255,0.03)",
            border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
            padding: "5px 8px", color: "#a0f4ff", fontSize: 10,
            fontFamily: "monospace", outline: "none",
          }} />
        </div>
        <div>
          <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>TARGET OS</div>
          <div style={{ display: "flex", gap: 6 }}>
            {(["windows","linux"] as const).map(o => (
              <button key={o} onClick={() => setOsType(o)} style={{
                padding: "4px 12px", fontSize: 7, letterSpacing: 2,
                background: osType === o ? "rgba(0,212,255,0.1)" : "transparent",
                border: `1px solid ${osType === o ? J : "rgba(0,212,255,0.12)"}`,
                color: osType === o ? J : DIM,
                cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
              }}>{o.toUpperCase()}</button>
            ))}
          </div>
        </div>
        <Btn label="⚡ FULL STEALTH SWEEP" risk="CRITICAL"
          onClick={() => dispatch("full_stealth_sweep", { session, os: osType })} />
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "14px 20px" }}>

        {/* AV Evasion */}
        <Section title="AV / PAYLOAD EVASION" risk="HIGH">
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <Input label="PAYLOAD PATH" value={payloadPath} onChange={setPayloadPath}
                placeholder="/tmp/payload.exe" />
              <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 6 }}>
                ENCODING TECHNIQUE
              </div>
              <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
                {(["xor","base64","shikata"] as const).map(t => (
                  <button key={t} onClick={() => setEncTech(t)} style={{
                    padding: "4px 10px", fontSize: 7, letterSpacing: 1,
                    background: encTech === t ? "rgba(0,212,255,0.1)" : "transparent",
                    border: `1px solid ${encTech === t ? J : "rgba(0,212,255,0.12)"}`,
                    color: encTech === t ? J : DIM,
                    cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
                  }}>{t.toUpperCase()}</button>
                ))}
              </div>
              <Btn label="ENCODE PAYLOAD" risk="HIGH"
                onClick={() => dispatch("encode_payload", { path: payloadPath, technique: encTech })}
                disabled={!payloadPath} />
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <Input label="LHOST" value={lhost} onChange={setLhost} placeholder="192.168.56.104" />
              <Input label="LPORT" value={lport} onChange={setLport} placeholder="443" />
              <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 6 }}>PLATFORM</div>
              <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
                {(["windows","linux","android"] as const).map(p => (
                  <button key={p} onClick={() => setPlatform(p)} style={{
                    padding: "4px 10px", fontSize: 7, letterSpacing: 1,
                    background: platform === p ? "rgba(0,212,255,0.1)" : "transparent",
                    border: `1px solid ${platform === p ? J : "rgba(0,212,255,0.12)"}`,
                    color: platform === p ? J : DIM,
                    cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
                  }}>{p.toUpperCase()}</button>
                ))}
              </div>
              <Btn label="GENERATE EVASIVE PAYLOAD" risk="CRITICAL"
                onClick={() => dispatch("generate_evasive_payload", { lhost, lport, platform })}
                disabled={!lhost} />
            </div>
          </div>
        </Section>

        {/* Log clearing */}
        <Section title="LOG CLEARING & ANTI-FORENSICS" risk="CRITICAL">
          <div style={{ fontSize: 9, color: "rgba(255,34,0,0.6)", marginBottom: 10 }}>
            Wipes all activity evidence from the target. Requires active session.
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            <Btn label="CLEAR LINUX LOGS" risk="CRITICAL"
              onClick={() => dispatch("clear_logs_linux", { session })} />
            <Btn label="CLEAR WINDOWS EVENT LOGS" risk="CRITICAL"
              onClick={() => dispatch("clear_logs_windows", { session })} />
          </div>
          <Input label="FILE PATH TO TIMESTOMP" value={tsPath} onChange={setTsPath}
            placeholder="C:\\Windows\\Temp\\*.exe" />
          <Btn label="TIMESTOMP" risk="HIGH"
            onClick={() => dispatch("timestomp", { session, path: tsPath })} />
        </Section>

        {/* Process hiding */}
        <Section title="PROCESS MIGRATION & HIDING" risk="HIGH">
          <Input label="MIGRATE INTO PROCESS" value={targetProc} onChange={setTargetProc}
            placeholder="explorer.exe" />
          <div style={{ fontSize: 9, color: DIM, marginBottom: 10 }}>
            Recommended: explorer.exe · svchost.exe · winlogon.exe · notepad.exe
          </div>
          <Btn label="MIGRATE PROCESS" risk="HIGH"
            onClick={() => dispatch("migrate_process", { session, process: targetProc })} />
        </Section>

        {/* LOLBins */}
        <Section title="LIVING-OFF-THE-LAND / LOLBINS" risk="MEDIUM">
          <div style={{ marginBottom: 12 }}>
            <Btn label="ENUMERATE LOLBINS" risk="MEDIUM"
              onClick={() => dispatch("lolbins_enum", { session, os: osType })} />
          </div>
          <Input label="POWERSHELL COMMAND (AMSI + EXEC POLICY BYPASS)"
            value={psCommand} onChange={setPsCommand}
            placeholder="whoami; Get-LocalUser; ipconfig /all" />
          <div style={{ marginBottom: 12 }}>
            <Btn label="PS AMSI BYPASS + EXECUTE" risk="HIGH"
              onClick={() => dispatch("ps_amsi_bypass", { session, command: psCommand })}
              disabled={!psCommand} />
          </div>
          <Input label="CERTUTIL DOWNLOAD URL" value={dlUrl} onChange={setDlUrl}
            placeholder="http://192.168.56.104/file.exe" />
          <Input label="OUTPUT PATH" value={dlOut} onChange={setDlOut}
            placeholder="C:\\Windows\\Temp\\file.exe" />
          <Btn label="CERTUTIL DOWNLOAD (LOLBin)" risk="HIGH"
            onClick={() => dispatch("certutil_download", { url: dlUrl, output: dlOut, session })}
            disabled={!dlUrl} />
        </Section>

        {/* Traffic obfuscation */}
        <Section title="TRAFFIC OBFUSCATION & TUNNELING" risk="HIGH">
          <div style={{ marginBottom: 14 }}>
            <Btn label="START HTTPS C2 LISTENER (port 443)" risk="HIGH"
              onClick={() => dispatch("traffic_obfuscation", { target: lhost || "0.0.0.0", port: "443" })} />
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 160 }}>
              <Input label="DNS TUNNEL DOMAIN" value={dnsDomain} onChange={setDnsDomain}
                placeholder="t.yourdomain.com" />
            </div>
            <div style={{ flex: 1, minWidth: 160 }}>
              <Input label="VPS IP (NS record target)" value={dnsLhost} onChange={setDnsLhost}
                placeholder="1.2.3.4" />
            </div>
          </div>
          <Btn label="SETUP DNS TUNNEL (iodine)" risk="HIGH"
            onClick={() => dispatch("dns_tunnel", { domain: dnsDomain, lhost: dnsLhost })}
            disabled={!dnsDomain || !dnsLhost} />
        </Section>

        {/* Output */}
        {outputText && (
          <div style={{
            background: "rgba(0,0,0,0.4)", border: "1px solid rgba(0,212,255,0.1)",
            borderRadius: 4, padding: "12px 14px", marginTop: 8,
          }}>
            <div style={{
              fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 8,
              display: "flex", justifyContent: "space-between",
            }}>
              <span>OUTPUT</span>
              {!off.lastDone && (
                <span style={{ color: "#ffb300", animation: "data-flicker 1.5s ease infinite" }}>
                  RUNNING...
                </span>
              )}
            </div>
            <pre style={{
              fontSize: 9, color: "rgba(0,212,255,0.75)", fontFamily: "monospace",
              whiteSpace: "pre-wrap", wordBreak: "break-all", margin: 0,
              maxHeight: 320, overflowY: "auto",
            }}>{outputText}</pre>
          </div>
        )}

      </div>
    </div>
  );
}

import { useState, useEffect, useRef, useCallback } from "react";
import { bridge } from "../../lib/bridge";
import type { BrainMessage } from "../../lib/bridge";

const J   = "#00d4ff";
const DIM = "rgba(0,212,255,0.35)";
const G   = "#00ff88";
const W   = "#ff6600";
const R   = "#ff2200";

const SEV_COLOR: Record<string, string> = {
  HIGH:   R,
  MEDIUM: W,
  LOW:    J,
};

function Btn({ label, onClick, disabled = false, glow = false, danger = false }: {
  label: string; onClick: () => void;
  disabled?: boolean; glow?: boolean; danger?: boolean;
}) {
  const c = danger ? R : glow ? G : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "7px 16px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${danger ? "255,34,0" : glow ? "0,255,136" : "0,212,255"},0.07)`,
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
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{
          width: "100%", background: "rgba(0,212,255,0.03)",
          border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
          padding: "6px 10px", color: "rgba(160,244,255,0.9)",
          fontSize: 10, fontFamily: "monospace", outline: "none", caretColor: J,
        }} />
    </div>
  );
}

type Alert = {
  id:          number;
  attack_type: string;
  severity:    string;
  attacker_ip: string;
  log_line:    string;
  timestamp:   number;
};

type Tab = "network" | "breach" | "link" | "harden" | "monitor" | "investigate";

export function GuardianPanel() {
  const [tab,       setTab]       = useState<Tab>("network");
  const [output,    setOutput]    = useState<string[]>([]);
  const [running,   setRunning]   = useState(false);
  const [alerts,    setAlerts]    = useState<Alert[]>([]);
  const [monitoring,setMonitoring]= useState(false);
  const alertId = useRef(0);
  const outRef  = useRef<HTMLDivElement>(null);
  const sessionId = "guardian_main";

  // Inputs
  const [network,   setNetwork]   = useState("");
  const [routerIp,  setRouterIp]  = useState("192.168.1.1");
  const [email,     setEmail]     = useState("");
  const [phone,     setPhone]     = useState("");
  const [domain,    setDomain]    = useState("");
  const [url,       setUrl]       = useState("");
  const [osType,    setOsType]    = useState<"windows"|"android"|"router">("windows");
  const [attackerIp,setAttackerIp]= useState("");
  const [blockIp,   setBlockIp]   = useState("");

  const addOutput = useCallback((line: string) => {
    setOutput(prev => [...prev.slice(-500), line]);
  }, []);

  useEffect(() => {
    if (outRef.current) outRef.current.scrollTop = outRef.current.scrollHeight;
  }, [output]);

  useEffect(() => {
    const unsub = bridge.onMessage((msg: BrainMessage) => {
      switch (msg.type) {
        case "guardian_output":
          addOutput(msg.line as string);
          break;
        case "guardian_done":
          setRunning(false);
          break;
        case "guardian_alert":
          setAlerts(prev => [{
            id:          ++alertId.current,
            attack_type: msg.attack_type as string,
            severity:    msg.severity    as string,
            attacker_ip: msg.attacker_ip as string,
            log_line:    msg.log_line    as string,
            timestamp:   msg.timestamp   as number,
          }, ...prev].slice(0, 100));
          break;
        case "guardian_started":
          setMonitoring(true);
          addOutput(msg.message as string);
          break;
        case "guardian_stopped":
          setMonitoring(false);
          addOutput("[T] Monitor stopped.");
          break;
        case "guardian_error":
          setRunning(false);
          addOutput(`[ERROR] ${msg.message}`);
          break;
      }
    });
    return unsub;
  }, [addOutput]);

  const dispatch = (action: string, params: Record<string, unknown> = {}) => {
    setOutput([]);
    setRunning(true);
    bridge.send({ type: "guardian_action", action, params });
  };

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: "network",     label: "NETWORK SCAN",  icon: "🔍" },
    { id: "breach",      label: "BREACH CHECK",  icon: "🔓" },
    { id: "link",        label: "LINK SAFETY",   icon: "🔗" },
    { id: "harden",      label: "HARDEN",        icon: "🛡" },
    { id: "monitor",     label: "MONITOR",       icon: "👁" },
    { id: "investigate", label: "INVESTIGATE",   icon: "🕵" },
  ];

  return (
    <div style={{
      height: "100%", display: "flex", flexDirection: "column",
      background: "radial-gradient(ellipse at 20% 30%, #000d1e 0%, #000006 100%)",
    }}>

      {/* Header */}
      <div style={{
        padding: "14px 24px 0",
        borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 8 }}>
          <div style={{ fontSize: 9, letterSpacing: 6, color: DIM }}>T · GUARDIAN</div>
          {monitoring && (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%", background: G,
                boxShadow: `0 0 8px ${G}`,
                animation: "pulse-voice 1.2s ease-in-out infinite",
              }} />
              <span style={{ fontSize: 8, color: G, letterSpacing: 2 }}>MONITORING</span>
            </div>
          )}
          {alerts.length > 0 && (
            <div style={{
              padding: "2px 10px", fontSize: 7, letterSpacing: 2,
              background: "rgba(255,34,0,0.08)", border: "1px solid rgba(255,34,0,0.3)",
              color: R, borderRadius: 2,
            }}>
              {alerts.length} ALERT{alerts.length > 1 ? "S" : ""}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 2, overflowX: "auto" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "5px 12px", fontSize: 7, letterSpacing: 2,
              background: "transparent", border: "none", whiteSpace: "nowrap",
              borderBottom: `2px solid ${tab === t.id ? J : "transparent"}`,
              color: tab === t.id ? J : DIM,
              cursor: "pointer", fontFamily: "inherit",
            }}>{t.icon} {t.label}</button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* Left — controls */}
        <div style={{
          width: 300, flexShrink: 0, padding: "16px 20px",
          borderRight: "1px solid rgba(0,212,255,0.07)",
          overflowY: "auto",
        }}>

          {/* NETWORK SCAN */}
          {tab === "network" && (
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                HOME NETWORK SCANNER
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 14, lineHeight: 1.7 }}>
                Scans every device on your network, shows open ports and explains the risk in plain language.
              </div>
              <Input label="NETWORK (leave blank to auto-detect)" value={network}
                onChange={setNetwork} placeholder="192.168.1.0/24" />
              <Input label="ROUTER IP" value={routerIp}
                onChange={setRouterIp} placeholder="192.168.1.1" />
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Btn label="SCAN NETWORK" glow onClick={() => dispatch("scan_network", { network })} disabled={running} />
                <Btn label="CHECK ROUTER" onClick={() => dispatch("check_router", { router_ip: routerIp })} disabled={running} />
              </div>
            </div>
          )}

          {/* BREACH CHECK */}
          {tab === "breach" && (
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                BREACH DATABASE CHECK
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 14, lineHeight: 1.7 }}>
                Check if an email, phone or domain has appeared in known data breaches or paste sites.
              </div>
              <Input label="EMAIL ADDRESS" value={email} onChange={setEmail} placeholder="user@example.com" />
              <Btn label="CHECK EMAIL" onClick={() => dispatch("breach_email", { email })} disabled={running || !email} />
              <div style={{ margin: "14px 0 10px", borderTop: "1px solid rgba(0,212,255,0.06)" }} />
              <Input label="PHONE NUMBER" value={phone} onChange={setPhone} placeholder="+923001234567" />
              <Btn label="CHECK PHONE" onClick={() => dispatch("breach_phone", { phone })} disabled={running || !phone} />
              <div style={{ margin: "14px 0 10px", borderTop: "1px solid rgba(0,212,255,0.06)" }} />
              <Input label="DOMAIN" value={domain} onChange={setDomain} placeholder="example.com" />
              <Btn label="CHECK DOMAIN" onClick={() => dispatch("breach_domain", { domain })} disabled={running || !domain} />
            </div>
          )}

          {/* LINK SAFETY */}
          {tab === "link" && (
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                PHISHING LINK CHECKER
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 14, lineHeight: 1.7 }}>
                Paste a suspicious link before anyone clicks it. T checks it against phishing and malware databases.
              </div>
              <Input label="SUSPICIOUS URL" value={url} onChange={setUrl} placeholder="https://suspicious-link.com" />
              <Btn label="CHECK LINK" glow onClick={() => dispatch("check_link", { url })} disabled={running || !url} />
            </div>
          )}

          {/* HARDEN */}
          {tab === "harden" && (
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                DEVICE HARDENING ADVISOR
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 14, lineHeight: 1.7 }}>
                Plain-language steps to secure a device. Share this with anyone who needs help.
              </div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 8 }}>DEVICE TYPE</div>
              <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
                {(["windows","android","router"] as const).map(o => (
                  <button key={o} onClick={() => setOsType(o)} style={{
                    padding: "5px 12px", fontSize: 7, letterSpacing: 2,
                    background: osType === o ? "rgba(0,212,255,0.1)" : "transparent",
                    border: `1px solid ${osType === o ? J : "rgba(0,212,255,0.12)"}`,
                    color: osType === o ? J : DIM,
                    cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
                  }}>{o.toUpperCase()}</button>
                ))}
              </div>
              <Btn label="GET HARDENING GUIDE" glow
                onClick={() => dispatch("harden_advice", { os: osType })} disabled={running} />
            </div>
          )}

          {/* MONITOR */}
          {tab === "monitor" && (
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                ATTACK MONITOR
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 14, lineHeight: 1.7 }}>
                Watches your network connections in real time. Alerts you when suspicious activity is detected.
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                {!monitoring ? (
                  <Btn label="▶ START MONITORING" glow
                    onClick={() => bridge.send({ type: "guardian_action", action: "monitor_start",
                      params: { session_id: sessionId } })} />
                ) : (
                  <Btn label="■ STOP" danger
                    onClick={() => bridge.send({ type: "guardian_action", action: "monitor_stop",
                      params: { session_id: sessionId } })} />
                )}
              </div>

              {/* Alerts */}
              {alerts.length > 0 && (
                <div>
                  <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 8 }}>
                    ALERTS ({alerts.length})
                  </div>
                  <div style={{ maxHeight: 300, overflowY: "auto" }}>
                    {alerts.map(a => (
                      <div key={a.id} style={{
                        background: "rgba(0,0,0,0.3)",
                        border: `1px solid ${SEV_COLOR[a.severity]}33`,
                        borderLeft: `3px solid ${SEV_COLOR[a.severity]}`,
                        borderRadius: 3, padding: "8px 10px", marginBottom: 6,
                      }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                          <span style={{
                            fontSize: 6, letterSpacing: 2, padding: "1px 6px",
                            background: SEV_COLOR[a.severity] + "22",
                            border: `1px solid ${SEV_COLOR[a.severity]}`,
                            color: SEV_COLOR[a.severity], borderRadius: 2,
                          }}>{a.severity}</span>
                          <span style={{ fontSize: 8, color: "#a0f4ff" }}>{a.attack_type}</span>
                          <span style={{ fontSize: 7, color: DIM, marginLeft: "auto" }}>
                            {new Date(a.timestamp * 1000).toLocaleTimeString()}
                          </span>
                        </div>
                        <div style={{ fontSize: 9, color: W }}>
                          {a.attacker_ip}
                        </div>
                        <div style={{ fontSize: 8, color: DIM, fontFamily: "monospace", marginTop: 2 }}>
                          {a.log_line.slice(0, 100)}
                        </div>
                        <button onClick={() => {
                          setTab("investigate");
                          setAttackerIp(a.attacker_ip);
                        }} style={{
                          marginTop: 6, padding: "3px 8px", fontSize: 7, letterSpacing: 1,
                          background: "rgba(0,212,255,0.05)",
                          border: "1px solid rgba(0,212,255,0.15)",
                          color: J, cursor: "pointer",
                          fontFamily: "inherit", borderRadius: 2,
                        }}>INVESTIGATE →</button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* INVESTIGATE */}
          {tab === "investigate" && (
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                IP INVESTIGATION
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 14, lineHeight: 1.7 }}>
                Collects intelligence on any IP address. Geolocation, ISP, abuse history, WHOIS.
              </div>
              <Input label="TARGET IP" value={attackerIp} onChange={setAttackerIp} placeholder="8.8.8.8" />
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
                <Btn label="INVESTIGATE" glow
                  onClick={() => dispatch("investigate_attacker", { ip: attackerIp })}
                  disabled={running || !attackerIp} />
              </div>
              <div style={{ borderTop: "1px solid rgba(0,212,255,0.06)", paddingTop: 14 }}>
                <Input label="BLOCK IP (defensive firewall rule)" value={blockIp}
                  onChange={setBlockIp} placeholder="1.2.3.4" />
                <Btn label="BLOCK TARGET" danger
                  onClick={() => dispatch("block_ip", { ip: blockIp })}
                  disabled={running || !blockIp} />
                <div style={{ fontSize: 8, color: DIM, marginTop: 8, lineHeight: 1.6 }}>
                  Adds a Windows Firewall rule to drop all inbound traffic from this IP.
                  Run T as Administrator for this to work.
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Right — output */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{
            padding: "8px 16px",
            borderBottom: "1px solid rgba(0,212,255,0.06)",
            display: "flex", justifyContent: "space-between", alignItems: "center",
            flexShrink: 0,
          }}>
            <span style={{ fontSize: 7, letterSpacing: 4, color: DIM }}>OUTPUT</span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {running && (
                <span style={{ fontSize: 8, color: W, animation: "data-flicker 1.5s ease infinite" }}>
                  RUNNING...
                </span>
              )}
              <button onClick={() => setOutput([])} style={{
                fontSize: 7, letterSpacing: 2, padding: "3px 8px",
                background: "transparent", border: "1px solid rgba(0,212,255,0.1)",
                color: DIM, cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
              }}>CLEAR</button>
            </div>
          </div>

          <div ref={outRef} style={{
            flex: 1, overflowY: "auto", padding: "12px 16px",
            fontFamily: "monospace", fontSize: 10,
            color: "rgba(0,212,255,0.75)", lineHeight: 1.7,
          }}>
            {output.length === 0 ? (
              <div style={{ color: DIM, fontStyle: "italic", padding: "20px 0" }}>
                Select a tool and run a check — output appears here.
              </div>
            ) : (
              output.map((line, i) => {
                const color =
                  line.startsWith("[ERROR]")  ? R :
                  line.startsWith("[T]")       ? "#a0f4ff" :
                  line.includes("⚠")          ? W :
                  line.includes("✓")          ? G :
                  line.startsWith("═") || line.startsWith("─") ? "rgba(0,212,255,0.2)" :
                  "rgba(0,212,255,0.7)";
                return (
                  <div key={i} style={{ color, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                    {line}
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

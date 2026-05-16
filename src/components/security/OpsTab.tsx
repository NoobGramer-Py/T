import { useState } from "react";
import { useOps, useOffensive, type OpsTarget } from "../../hooks/useBridge";

const J   = "#00d4ff";
const DIM = "rgba(0,212,255,0.35)";
const CARD: React.CSSProperties = {
  background: "rgba(0,212,255,0.02)",
  border: "1px solid rgba(0,212,255,0.09)",
  borderRadius: 4, padding: "14px 16px",
};

const RISK_COLOR: Record<string, string> = {
  LOW: "#00ff88", MEDIUM: "#ffb300", HIGH: "#ff6600", CRITICAL: "#ff2200",
};

function Btn({ label, onClick, danger = false, disabled = false, active = false }: {
  label: string; onClick: () => void;
  danger?: boolean; disabled?: boolean; active?: boolean;
}) {
  const c = danger ? "#ff3300" : active ? "#00ff88" : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 14px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${danger ? "255,51,0" : active ? "0,255,136" : "0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.1)" : `rgba(${danger ? "255,51,0" : active ? "0,255,136" : "0,212,255"},0.3)`}`,
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
          fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: J,
        }}
        onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
        onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
      />
    </div>
  );
}

// ── Target type badge ──────────────────────────────────────────────────────────

const TYPE_COLOR: Record<string, string> = {
  ip:         "#00d4ff",
  domain:     "#a0f4ff",
  bugbounty:  "#00ff88",
  ctf:        "#ffb300",
  custom:     "#cc88ff",
};

function TypeBadge({ type }: { type: string }) {
  return (
    <span style={{
      padding: "1px 7px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
      border: `1px solid ${TYPE_COLOR[type] || J}40`,
      color: TYPE_COLOR[type] || J,
    }}>{type.toUpperCase()}</span>
  );
}

// ── Confirm modal (reused pattern) ────────────────────────────────────────────

function ConfirmModal({ tool, command, description, risk, onConfirm }: {
  tool: string; command: string; description: string; risk: string;
  onConfirm: (c: boolean) => void;
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.82)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "#000a15", border: "1px solid rgba(0,212,255,0.25)",
        borderRadius: 6, padding: "28px 32px", maxWidth: 520, width: "90%",
      }}>
        <div style={{ fontSize: 8, letterSpacing: 5, color: DIM, marginBottom: 14 }}>
          REAL-WORLD OPERATION · CONFIRMATION REQUIRED
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{
            padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
            border: `1px solid ${RISK_COLOR[risk] || J}`,
            color: RISK_COLOR[risk] || J,
          }}>{risk}</div>
          <span style={{ color: "#a0f4ff", fontSize: 12, fontWeight: 600 }}>{tool}</span>
        </div>
        <div style={{
          fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.7)",
          background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.08)",
          borderRadius: 3, padding: "8px 12px", marginBottom: 14, wordBreak: "break-all",
        }}>{command}</div>
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.55)", marginBottom: 22, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
          {description}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn label="CANCEL"  onClick={() => onConfirm(false)} danger />
          <Btn label="CONFIRM" onClick={() => onConfirm(true)} active />
        </div>
      </div>
    </div>
  );
}

// ── Recon output ──────────────────────────────────────────────────────────────

function ReconOutput({ lines, currentStep, done }: {
  lines: { step: string; chunk: string; ts: number }[];
  currentStep: string;
  done: boolean;
}) {
  if (lines.length === 0 && !currentStep) return null;
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <span style={{ fontSize: 7, letterSpacing: 4, color: DIM }}>RECON OUTPUT</span>
        {currentStep && !done && (
          <span style={{ fontSize: 8, color: "#ffb300", animation: "data-flicker 2s ease infinite" }}>
            {currentStep}...
          </span>
        )}
        {done && <span style={{ fontSize: 8, color: "#00ff88" }}>COMPLETE</span>}
      </div>
      <div style={{
        background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.07)",
        borderRadius: 3, padding: "10px 12px", maxHeight: 360, overflowY: "auto",
        fontFamily: "monospace", fontSize: 10, lineHeight: 1.55,
      }}>
        {lines.map((l, i) => {
          const isHeader = l.chunk.startsWith("[") && l.chunk.includes("]");
          const isHit    = /open|found|200|success|vulnerable/i.test(l.chunk);
          return (
            <div key={i} style={{
              color: isHit ? "#00ff88" :
                     l.chunk.startsWith("[ERROR]") ? "#ff4400" :
                     isHeader ? "#a0f4ff" : "rgba(0,212,255,0.65)",
              marginBottom: isHeader ? 4 : 0,
              fontWeight: isHit ? 600 : undefined,
            }}>{l.chunk}</div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main OpsTab ───────────────────────────────────────────────────────────────

export function OpsTab() {
  const ops = useOps();
  const off = useOffensive();

  const [sessName,   setSessName]   = useState("Operation Alpha");
  const [sessNotes,  setSessNotes]  = useState("");
  const [targetType, setTargetType] = useState("domain");
  const [targetVal,  setTargetVal]  = useState("");
  const [scopeNotes, setScopeNotes] = useState("");
  const [programUrl, setProgramUrl] = useState("");
  const [reconTarget,setReconTarget]= useState("");
  const [offTarget,  setOffTarget]  = useState("");
  const [offTool,    setOffTool]    = useState("nmap");
  const [offFlags,   setOffFlags]   = useState("-sV -T4 --open");
  const [section,    setSection]    = useState<"session"|"recon"|"attack"|"ctf">("session");

  const TARGET_TYPES = [
    { id: "ip",        label: "IP / Range"      },
    { id: "domain",    label: "Domain"          },
    { id: "bugbounty", label: "Bug Bounty"      },
    { id: "ctf",       label: "CTF / HTB / THM" },
    { id: "custom",    label: "Custom"          },
  ];

  // Common offensive tools for direct dispatch
  const QUICK_TOOLS = [
    { tool: "nmap",        label: "NMAP SCAN",      flags: { target: offTarget, flags: "-sV -T4 --open" } },
    { tool: "nikto",       label: "NIKTO",          flags: { target: offTarget } },
    { tool: "sqlmap",      label: "SQLMAP",         flags: { url: offTarget, extra: "--batch --level=2 --risk=2" } },
    { tool: "ffuf",        label: "FFUF FUZZ",      flags: { url: offTarget + "/FUZZ", wordlist: "/usr/share/seclists/Discovery/Web-Content/common.txt" } },
    { tool: "nuclei",      label: "NUCLEI",         flags: { target: offTarget, tags: "cve,rce,sqli,xss" } },
    { tool: "searchsploit",label: "SEARCHSPLOIT",   flags: { query: offTarget } },
    { tool: "wpscan",      label: "WPSCAN",         flags: { url: offTarget } },
    { tool: "hydra",       label: "HYDRA SSH",      flags: { target: offTarget, service: "ssh", user: "admin", wordlist: "/usr/share/wordlists/rockyou.txt" } },
    { tool: "gobuster",    label: "GOBUSTER",       flags: { url: offTarget, wordlist: "/usr/share/seclists/Discovery/Web-Content/common.txt" } },
    { tool: "theharvester",label: "THEHARVESTER",   flags: { domain: offTarget, source: "all" } },
    { tool: "amass",       label: "AMASS",          flags: { domain: offTarget } },
    { tool: "subfinder",   label: "SUBFINDER",      flags: { domain: offTarget } },
    { tool: "masscan",     label: "MASSCAN",        flags: { target: offTarget, ports: "1-65535", rate: "5000" } },
    { tool: "wafw00f",     label: "WAF DETECT",     flags: { url: offTarget } },
  ];

  const SECTIONS = [
    { id: "session", label: "SESSION & SCOPE" },
    { id: "recon",   label: "AUTO RECON"      },
    { id: "attack",  label: "TOOLS"           },
    { id: "ctf",     label: "CTF"             },
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Confirm modals */}
      {off.confirmReq && (
        <ConfirmModal
          tool={off.confirmReq.tool}
          command={off.confirmReq.command}
          description={off.confirmReq.description}
          risk={off.confirmReq.risk}
          onConfirm={c => off.confirm(off.confirmReq!.id, c)}
        />
      )}

      {/* Header */}
      <div style={{
        padding: "12px 20px 0",
        borderBottom: "1px solid rgba(0,212,255,0.08)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 10 }}>
          <div style={{ fontSize: 9, letterSpacing: 6, color: DIM }}>T · REAL-WORLD OPERATIONS</div>
          {ops.session && (
            <div style={{
              padding: "2px 10px", fontSize: 7, letterSpacing: 3, borderRadius: 2,
              background: "rgba(0,255,136,0.06)", border: "1px solid rgba(0,255,136,0.2)",
              color: "#00ff88",
            }}>
              {ops.session.name} — {ops.session.targets.length} target{ops.session.targets.length !== 1 ? "s" : ""}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 2 }}>
          {SECTIONS.map(s => (
            <button key={s.id} onClick={() => setSection(s.id as typeof section)} style={{
              padding: "5px 12px", fontSize: 7, letterSpacing: 3,
              background: "transparent", border: "none",
              borderBottom: `2px solid ${section === s.id ? J : "transparent"}`,
              color: section === s.id ? J : DIM,
              cursor: "pointer", fontFamily: "inherit",
            }}>{s.label}</button>
          ))}
        </div>
      </div>

      {/* Error */}
      {(ops.error || off.error) && (
        <div style={{
          flexShrink: 0, margin: "8px 20px 0",
          background: "rgba(255,51,0,0.07)", border: "1px solid rgba(255,51,0,0.2)",
          borderRadius: 3, padding: "8px 12px", fontSize: 10, color: "#ff4400",
          display: "flex", justifyContent: "space-between",
        }}>
          <span>{ops.error || off.error}</span>
          <button onClick={() => { ops.clearError(); off.clearError(); }} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

        {/* ── SESSION & SCOPE ── */}
        {section === "session" && (
          <div>
            {/* Create session */}
            {!ops.session && (
              <div style={{ ...CARD, marginBottom: 20 }}>
                <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                  CREATE OPERATION SESSION
                </div>
                <Input label="SESSION NAME" value={sessName} onChange={setSessName} placeholder="Operation Alpha" />
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>NOTES</div>
                  <textarea value={sessNotes} onChange={e => setSessNotes(e.target.value)}
                    placeholder="Scope limits, program rules, notes..."
                    rows={2} style={{
                      width: "100%", resize: "vertical",
                      background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
                      borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
                      fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: J,
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
                    onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
                  />
                </div>
                <Btn label="CREATE SESSION" onClick={() => ops.createSession(sessName, sessNotes)} active />
              </div>
            )}

            {/* Session status */}
            {ops.session && (
              <div style={{ ...CARD, marginBottom: 20, borderColor: "rgba(0,255,136,0.15)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <div style={{ fontSize: 10, color: "#00ff88", fontWeight: 600 }}>{ops.session.name}</div>
                  <div style={{ fontSize: 8, color: DIM }}>{new Date(ops.session.started * 1000).toLocaleString()}</div>
                </div>
                {ops.session.notes && (
                  <div style={{ fontSize: 9, color: "rgba(0,212,255,0.5)", marginBottom: 10, lineHeight: 1.6 }}>
                    {ops.session.notes}
                  </div>
                )}
                <div style={{ display: "flex", gap: 14 }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 18, color: J, fontWeight: 700 }}>{ops.session.targets.length}</div>
                    <div style={{ fontSize: 7, letterSpacing: 3, color: DIM }}>TARGETS</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 18, color: "#00ff88", fontWeight: 700 }}>{ops.session.finding_count}</div>
                    <div style={{ fontSize: 7, letterSpacing: 3, color: DIM }}>FINDINGS</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 18, color: "#ffb300", fontWeight: 700 }}>{ops.session.log_count}</div>
                    <div style={{ fontSize: 7, letterSpacing: 3, color: DIM }}>ACTIONS</div>
                  </div>
                </div>
              </div>
            )}

            {/* Add target */}
            <div style={{ ...CARD, marginBottom: 20 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>ADD TARGET</div>

              {/* Type selector */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
                {TARGET_TYPES.map(t => (
                  <button key={t.id} onClick={() => setTargetType(t.id)} style={{
                    padding: "4px 10px", fontSize: 8, cursor: "pointer", fontFamily: "inherit",
                    background: targetType === t.id ? `rgba(${TYPE_COLOR[t.id] === "#00ff88" ? "0,255,136" : "0,212,255"},0.08)` : "transparent",
                    border: `1px solid ${targetType === t.id ? TYPE_COLOR[t.id] : "rgba(0,212,255,0.1)"}`,
                    color: targetType === t.id ? TYPE_COLOR[t.id] : DIM,
                    borderRadius: 2,
                  }}>{t.label}</button>
                ))}
              </div>

              <Input
                label={targetType === "ip" ? "IP / CIDR RANGE" :
                       targetType === "domain" ? "DOMAIN" :
                       targetType === "bugbounty" ? "PROGRAM NAME (e.g. google)" :
                       targetType === "ctf" ? "BOX IP / NAME (e.g. 10.10.10.40)" : "TARGET"}
                value={targetVal} onChange={setTargetVal}
                placeholder={targetType === "ip" ? "192.168.1.0/24" :
                             targetType === "domain" ? "example.com" :
                             targetType === "bugbounty" ? "google" : "target"}
              />

              {targetType === "bugbounty" && (
                <Input label="PROGRAM URL" value={programUrl} onChange={setProgramUrl}
                  placeholder="https://hackerone.com/google" />
              )}

              <Input label="SCOPE NOTES (what is in/out of scope)"
                value={scopeNotes} onChange={setScopeNotes}
                placeholder="e.g. *.example.com in scope, admin.example.com out of scope" />

              <Btn label="ADD TARGET" onClick={() => {
                ops.addTarget(targetType, targetVal, scopeNotes, programUrl);
                setTargetVal(""); setScopeNotes(""); setProgramUrl("");
              }} disabled={!targetVal.trim()} />
            </div>

            {/* Target list */}
            {ops.session && ops.session.targets.length > 0 && (
              <div>
                <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 10 }}>SCOPE</div>
                {ops.session.targets.map((t: OpsTarget) => (
                  <div key={t.id} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 12px", marginBottom: 4,
                    background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
                    borderRadius: 3,
                  }}>
                    <TypeBadge type={t.type} />
                    <span style={{ flex: 1, color: "#a0f4ff", fontSize: 11, fontFamily: "monospace" }}>{t.value}</span>
                    {t.scope_notes && (
                      <span style={{ fontSize: 8, color: DIM, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.scope_notes}</span>
                    )}
                    <div style={{ display: "flex", gap: 6 }}>
                      <Btn label="RECON" onClick={() => { setReconTarget(t.value); setSection("recon"); ops.autoRecon(t.value); }} />
                      <Btn label="ATTACK" onClick={() => { setOffTarget(t.value); setSection("attack"); }} />
                      <Btn label="DEL" onClick={() => ops.removeTarget(t.id)} danger />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── AUTO RECON ── */}
        {section === "recon" && (
          <div>
            <div style={{ ...CARD, marginBottom: 16 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                AUTOMATED RECON PIPELINE
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.5)", marginBottom: 12, lineHeight: 1.65 }}>
                Runs: nmap → service scripts → subdomains → CVE search → web headers → tech detection → SSL cert
              </div>
              <Input label="TARGET (IP or domain)" value={reconTarget} onChange={setReconTarget}
                placeholder="example.com or 192.168.1.1" />
              <Btn label="▶ RUN AUTO RECON" onClick={() => ops.autoRecon(reconTarget)}
                disabled={!reconTarget.trim()} active />
            </div>
            <ReconOutput lines={ops.reconLines} currentStep={ops.reconStep} done={ops.reconDone} />
          </div>
        )}

        {/* ── ATTACK TOOLS ── */}
        {section === "attack" && (
          <div>
            <div style={{ ...CARD, marginBottom: 16 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>TARGET</div>
              <Input label="IP / URL / DOMAIN" value={offTarget} onChange={setOffTarget}
                placeholder="192.168.1.1 or https://example.com" />
            </div>

            {/* Quick tool grid */}
            <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 10 }}>QUICK LAUNCH</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 20 }}>
              {QUICK_TOOLS.map(qt => (
                <button key={qt.tool} onClick={() => {
                  setOffTool(qt.tool);
                  off.dispatch(qt.tool, qt.flags);
                }} style={{
                  padding: "5px 12px", fontSize: 8, letterSpacing: 1,
                  background: offTool === qt.tool ? "rgba(0,212,255,0.1)" : "rgba(0,212,255,0.04)",
                  border: `1px solid rgba(0,212,255,${offTool === qt.tool ? "0.35" : "0.12"})`,
                  color: offTool === qt.tool ? J : DIM,
                  cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
                }}>{qt.label}</button>
              ))}
            </div>

            {/* Custom command */}
            <div style={{ ...CARD, marginBottom: 16 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 10 }}>CUSTOM TOOL</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 10, marginBottom: 10 }}>
                <Input label="TOOL" value={offTool} onChange={setOffTool} placeholder="nmap" />
                <Input label="FLAGS / PARAMS" value={offFlags} onChange={setOffFlags} placeholder="-sV -T4 --open" />
              </div>
              <Btn label="RUN" onClick={() => {
                const params: Record<string, string> = { target: offTarget };
                offFlags.split(" ").forEach((f, i) => {
                  if (f.startsWith("-")) params[`flag_${i}`] = f;
                });
                off.dispatch(offTool, { target: offTarget, flags: offFlags });
              }} />
            </div>

            {/* Stream output */}
            {off.streamLines.length > 0 && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 7, letterSpacing: 4, color: DIM }}>OUTPUT</span>
                  <button onClick={() => off.clearStream()} style={{
                    fontSize: 7, padding: "2px 8px", background: "transparent",
                    border: "1px solid rgba(0,212,255,0.15)", color: DIM,
                    cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
                  }}>CLEAR</button>
                </div>
                <div style={{
                  background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.07)",
                  borderRadius: 3, padding: "10px 12px", maxHeight: 400, overflowY: "auto",
                  fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.7)", lineHeight: 1.55,
                }}>
                  {off.streamLines.map((l, i) => (
                    <div key={i} style={{
                      color: l.chunk.startsWith("[ERROR]") ? "#ff4400" :
                             /open|found|200|success/i.test(l.chunk) ? "#00ff88" : undefined,
                    }}>{l.chunk}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── CTF ── */}
        {section === "ctf" && (
          <div>
            <div style={{ ...CARD, marginBottom: 16 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                CTF / HTB / THM BOX
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.5)", marginBottom: 14, lineHeight: 1.65 }}>
                T runs a full automated attack pipeline against CTF boxes:
                nmap → web recon → exploit search → auto-pwn attempt → flag search.
                Connect to HTB/THM VPN first, then enter the box IP.
              </div>
              <Input label="BOX IP (connect to VPN first)" value={offTarget} onChange={setOffTarget}
                placeholder="10.10.10.40" />

              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
                <Btn label="▶ FULL AUTO RECON" onClick={() => { ops.autoRecon(offTarget); setSection("recon"); setReconTarget(offTarget); }} active />
                <Btn label="NMAP ALL PORTS"    onClick={() => off.dispatch("nmap", { target: offTarget, flags: "-p- -T4" })} />
                <Btn label="GOBUSTER"          onClick={() => off.dispatch("gobuster", { url: `http://${offTarget}`, wordlist: "/usr/share/seclists/Discovery/Web-Content/common.txt" })} />
                <Btn label="NIKTO"             onClick={() => off.dispatch("nikto", { target: offTarget })} />
                <Btn label="NUCLEI"            onClick={() => off.dispatch("nuclei", { target: offTarget, tags: "cve,rce,sqli" })} />
                <Btn label="SEARCHSPLOIT"      onClick={() => off.dispatch("searchsploit", { query: offTarget })} />
              </div>

              <div style={{ ...CARD, borderColor: "rgba(0,255,136,0.1)" }}>
                <div style={{ fontSize: 8, letterSpacing: 4, color: "#00ff88", marginBottom: 10 }}>FLAG HUNTER</div>
                <div style={{ fontSize: 9, color: "rgba(0,212,255,0.5)", marginBottom: 10 }}>
                  If you have shell access via Meterpreter, T searches for flags automatically.
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <Btn label="SEARCH user.txt"  onClick={() => off.dispatch("msfconsole", { module: "post/multi/manage/shell_to_meterpreter", options: {} })} />
                  <Btn label="SEARCH root.txt"  onClick={() => off.dispatch("msfconsole", { module: "post/multi/recon/local_exploit_suggester", options: {} })} />
                  <Btn label="PRIVESC CHECK"    onClick={() => off.dispatch("msfconsole", { module: "post/multi/recon/local_exploit_suggester", options: {} })} />
                </div>
              </div>
            </div>

            {/* HTB / THM quick links */}
            <div style={{ ...CARD }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>PLATFORM LINKS</div>
              <div style={{ display: "flex", gap: 10 }}>
                {[
                  { label: "HackTheBox", url: "https://www.hackthebox.com" },
                  { label: "TryHackMe",  url: "https://tryhackme.com" },
                  { label: "HackerOne", url: "https://hackerone.com/opportunities/all/search" },
                  { label: "Bugcrowd",   url: "https://bugcrowd.com/engagements" },
                ].map(link => (
                  <a key={link.label} href={link.url} target="_blank" rel="noreferrer" style={{
                    padding: "5px 12px", fontSize: 8, letterSpacing: 2, borderRadius: 3,
                    background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)",
                    color: J, textDecoration: "none",
                  }}>{link.label}</a>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

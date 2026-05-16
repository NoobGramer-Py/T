import { useState } from "react";
import {
  nmapScan, checkIpReputationV2, getOpenPorts, analyzeProcesses,
  checkDnsLeak, getVpnStatus, getFirewallRules, checkPasswordStrength,
  checkUrlSafety, getSecurityLog, ipIntel, emailOsint, cveSearch, fullPortScan,
  detectProcessInjection, getArpTable,
} from "../../lib/tauri";
import type { FirewallRule, PasswordStrength, SecurityEvent, IpIntelResult, EmailOsintResult, CveEntry, FullScanResult, InjectionResult, ArpEntry } from "../../lib/tauri";
import { useTStore } from "../../store";
import { useLocalAccess, useOffensive, useVmStatus, type LocalAccessProgress, type OffensiveConfirmRequest, type RiskLevel } from "../../hooks/useBridge";

// ─── Shared ───────────────────────────────────────────────────────────────────

type Tab = "scanner" | "iprep" | "ports" | "processes" | "dns" | "vpn" | "firewall" | "password" | "url" | "log" | "ipintel" | "emailosint" | "cve" | "fullscan" | "localaccess" | "vm" | "crack" | "exploit" | "wifi" | "mitm" | "payload" | "web" | "osint" | "recon" | "router" | "mobile" | "iot" | "lab" | "ops" | "intel" | "auto" | "stealth" | "sqli";

function SectionHeader({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 8, borderBottom: "1px solid rgba(0,212,255,0.08)" }}>
      <span style={{ fontSize: 14, color: "#00d4ff", textShadow: "0 0 8px #00d4ff" }}>{icon}</span>
      <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(0,212,255,0.6)" }}>{title}</span>
    </div>
  );
}

function Btn({ label, onClick, disabled = false, danger = false }: {
  label: string; onClick: () => void; disabled?: boolean; danger?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 16px", fontSize: 8, letterSpacing: 2,
      background: danger ? "rgba(255,68,0,0.07)" : "rgba(0,212,255,0.07)",
      border: `1px solid ${danger ? "rgba(255,68,0,0.3)" : "rgba(0,212,255,0.25)"}`,
      color: danger ? "#ff4400" : "#00d4ff",
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", opacity: disabled ? 0.4 : 1, transition: "all 0.2s",
    }}>
      {label}
    </button>
  );
}

function Field({ label, value, onChange, type = "text", placeholder = "" }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>{label}</div>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        style={{ width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
        onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
      />
    </div>
  );
}

function StatusBadge({ value, labels }: { value: string; labels: Record<string, string> }) {
  const colors: Record<string, string> = {
    clean: "#00ff88", safe: "#00ff88", low: "#00ff88",
    suspicious: "#00d4ff", unknown: "#00d4ff", medium: "#00d4ff",
    malicious: "#ff4400", critical: "#ff4400", high: "#ff4400",
  };
  const color = colors[value.toLowerCase()] ?? "rgba(0,212,255,0.5)";
  return (
    <span style={{ fontSize: 8, letterSpacing: 2, padding: "2px 8px", border: `1px solid ${color}`, color, borderRadius: 2, textShadow: `0 0 6px ${color}` }}>
      {labels[value] ?? value.toUpperCase()}
    </span>
  );
}

function ResultBox({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, padding: "14px 16px", marginTop: 14 }}>
      {children}
    </div>
  );
}

// ─── Nmap Scanner ─────────────────────────────────────────────────────────────

function ScannerTab() {
  const [target, setTarget] = useState("");
  const [flags, setFlags]   = useState("-sV -T4");
  const [result, setResult] = useState<{ host: string; ports: { port: number; state: string; service: string; version: string }[]; os_guess: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const scan = async () => {
    if (!target.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await nmapScan(target.trim(), flags.trim()));
    } catch (e) { setError(e instanceof Error ? e.message : "Scan failed"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="NMAP PORT SCANNER" icon="⬡" />
      <Field label="TARGET (IP or hostname)" value={target} onChange={setTarget} placeholder="192.168.1.1 or example.com" />
      <Field label="FLAGS" value={flags} onChange={setFlags} placeholder="-sV -T4 -p 1-1000" />
      <Btn label={loading ? "SCANNING···" : "RUN SCAN"} onClick={scan} disabled={loading || !target.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.5)", marginBottom: 10 }}>HOST: {result.host}{result.os_guess && ` · OS: ${result.os_guess}`}</div>
          {result.ports.length === 0
            ? <div style={{ fontSize: 10, color: "rgba(0,212,255,0.4)" }}>No open ports found.</div>
            : <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead>
                  <tr style={{ color: "rgba(0,212,255,0.4)", fontSize: 8, letterSpacing: 2 }}>
                    {["PORT", "STATE", "SERVICE", "VERSION"].map((h) => (
                      <td key={h} style={{ padding: "4px 8px", borderBottom: "1px solid rgba(0,212,255,0.08)" }}>{h}</td>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.ports.map((p) => (
                    <tr key={p.port} style={{ borderBottom: "1px solid rgba(0,212,255,0.04)" }}>
                      <td style={{ padding: "5px 8px", color: "#a0f4ff" }}>{p.port}</td>
                      <td style={{ padding: "5px 8px", color: "#00ff88" }}>{p.state}</td>
                      <td style={{ padding: "5px 8px", color: "rgba(0,212,255,0.8)" }}>{p.service}</td>
                      <td style={{ padding: "5px 8px", color: "rgba(0,212,255,0.5)", fontSize: 9 }}>{p.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
          }
        </ResultBox>
      )}
    </div>
  );
}

// ─── IP Reputation ────────────────────────────────────────────────────────────

function IpRepTab() {
  const { profile } = useTStore();
  const [ip, setIp]       = useState("");
  const [result, setResult] = useState<{ ip: string; reputation: string; detail: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const check = async () => {
    if (!ip.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      // abuseipdb_key stored in profile notes or as a separate key
      const key = profile.abuseipdbKey;
      setResult(await checkIpReputationV2(ip.trim(), key));
    } catch (e) { setError(e instanceof Error ? e.message : "Check failed"); }
    finally { setLoading(false); }
  };

  const repColors: Record<string, string> = { clean: "#00ff88", suspicious: "#00d4ff", malicious: "#ff4400", unknown: "rgba(0,212,255,0.4)" };

  return (
    <div>
      <SectionHeader title="IP REPUTATION" icon="◎" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12, lineHeight: 1.6 }}>
        Powered by AbuseIPDB. Add your key in Settings → Profile → ABUSEIPDB API KEY.
      </div>
      <Field label="IP ADDRESS" value={ip} onChange={setIp} placeholder="8.8.8.8" />
      <Btn label={loading ? "CHECKING···" : "CHECK REPUTATION"} onClick={check} disabled={loading || !ip.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: repColors[result.reputation] ?? "#00d4ff", textShadow: `0 0 8px ${repColors[result.reputation] ?? "#00d4ff"}` }}>
              {result.reputation.toUpperCase()}
            </span>
            <span style={{ fontSize: 9, color: "rgba(0,212,255,0.5)" }}>{result.ip}</span>
          </div>
          <div style={{ fontSize: 10, color: "rgba(0,212,255,0.7)" }}>{result.detail}</div>
        </ResultBox>
      )}
    </div>
  );
}

// ─── Port Scanner (quick, no nmap) ────────────────────────────────────────────

function PortsTab() {
  const [host, setHost]     = useState("");
  const [result, setResult] = useState<{ port: number; service: string }[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const scan = async () => {
    if (!host.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try { setResult(await getOpenPorts(host.trim())); }
    catch (e) { setError(e instanceof Error ? e.message : "Scan failed"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="QUICK PORT SCAN" icon="⊹" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>Checks 17 common ports via TCP connect. No nmap required.</div>
      <Field label="HOST" value={host} onChange={setHost} placeholder="192.168.1.1 or domain.com" />
      <Btn label={loading ? "SCANNING···" : "SCAN PORTS"} onClick={scan} disabled={loading || !host.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result !== null && (
        <ResultBox>
          {result.length === 0
            ? <div style={{ fontSize: 10, color: "#00ff88" }}>All common ports closed or filtered.</div>
            : result.map((p) => (
              <div key={p.port} style={{ display: "flex", gap: 12, padding: "5px 0", borderBottom: "1px solid rgba(0,212,255,0.05)" }}>
                <span style={{ color: "#a0f4ff", minWidth: 50, fontSize: 11 }}>{p.port}</span>
                <span style={{ color: "#ff4400", fontSize: 10 }}>OPEN</span>
                <span style={{ color: "rgba(0,212,255,0.7)", fontSize: 10 }}>{p.service}</span>
              </div>
            ))
          }
        </ResultBox>
      )}
    </div>
  );
}

// ─── Process Audit ────────────────────────────────────────────────────────────

function ProcessAuditTab() {
  const [result, setResult] = useState<{ pid: number; name: string; suspicion: string; reason: string }[] | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try { setResult(await analyzeProcesses()); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="PROCESS AUDIT" icon="⬡" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Detects known malicious tools and anomalous CPU usage patterns.
      </div>
      <Btn label={loading ? "SCANNING···" : "AUDIT PROCESSES"} onClick={run} disabled={loading} />
      {result !== null && (
        <ResultBox>
          {result.length === 0
            ? <div style={{ fontSize: 10, color: "#00ff88" }}>✓ No suspicious processes detected.</div>
            : result.map((p) => (
              <div key={p.pid} style={{ padding: "8px 0", borderBottom: "1px solid rgba(0,212,255,0.06)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <StatusBadge value={p.suspicion} labels={{ critical: "CRITICAL", suspicious: "SUSPICIOUS" }} />
                  <span style={{ color: "#a0f4ff", fontSize: 11 }}>{p.name}</span>
                  <span style={{ color: "rgba(0,212,255,0.4)", fontSize: 9 }}>PID {p.pid}</span>
                </div>
                <div style={{ fontSize: 9, color: "rgba(0,212,255,0.6)" }}>{p.reason}</div>
              </div>
            ))
          }
        </ResultBox>
      )}
    </div>
  );
}

// ─── DNS Leak ─────────────────────────────────────────────────────────────────

function DnsTab() {
  const [result, setResult] = useState<{ leaking: boolean; servers: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const check = async () => {
    setLoading(true); setError(""); setResult(null);
    try { setResult(await checkDnsLeak()); }
    catch (e) { setError(e instanceof Error ? e.message : "Check failed"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="DNS LEAK TEST" icon="◎" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Checks if your DNS requests are leaking outside your VPN tunnel.
      </div>
      <Btn label={loading ? "TESTING···" : "RUN LEAK TEST"} onClick={check} disabled={loading} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <span style={{ fontSize: 13, color: result.leaking ? "#ff4400" : "#00ff88", textShadow: `0 0 8px ${result.leaking ? "#ff4400" : "#00ff88"}` }}>
              {result.leaking ? "⚠ LEAK DETECTED" : "✓ NO LEAK"}
            </span>
          </div>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 8 }}>DNS SERVERS</div>
          {result.servers.map((s) => (
            <div key={s} style={{ fontSize: 10, color: "rgba(0,212,255,0.8)", padding: "3px 0" }}>{s}</div>
          ))}
        </ResultBox>
      )}
    </div>
  );
}

// ─── VPN Status ───────────────────────────────────────────────────────────────

function VpnTab() {
  const [result, setResult] = useState<{ connected: boolean; provider: string; ip: string; location: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const check = async () => {
    setLoading(true); setError(""); setResult(null);
    try { setResult(await getVpnStatus()); }
    catch (e) { setError(e instanceof Error ? e.message : "Check failed"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="VPN STATUS" icon="⊞" />
      <Btn label={loading ? "CHECKING···" : "CHECK VPN"} onClick={check} disabled={loading} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <span style={{ fontSize: 13, color: result.connected ? "#00ff88" : "#ff4400", textShadow: `0 0 8px ${result.connected ? "#00ff88" : "#ff4400"}` }}>
              {result.connected ? "● VPN ACTIVE" : "○ NOT CONNECTED"}
            </span>
          </div>
          {[
            { label: "PUBLIC IP",  value: result.ip },
            { label: "LOCATION",   value: result.location },
            { label: "PROVIDER",   value: result.provider || "Unknown" },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: "flex", gap: 12, marginBottom: 8 }}>
              <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.4)", minWidth: 80 }}>{label}</span>
              <span style={{ fontSize: 10, color: "rgba(0,212,255,0.85)" }}>{value}</span>
            </div>
          ))}
        </ResultBox>
      )}
    </div>
  );
}

// ─── Firewall Rules ───────────────────────────────────────────────────────────

function FirewallTab() {
  const [rules, setRules]   = useState<FirewallRule[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");
  const [filter, setFilter] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try { setRules(await getFirewallRules()); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed to load rules"); }
    finally { setLoading(false); }
  };

  const filtered = rules?.filter((r) =>
    !filter || r.name.toLowerCase().includes(filter.toLowerCase())
  ) ?? [];

  return (
    <div>
      <SectionHeader title="FIREWALL RULES" icon="⬡" />
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <Btn label={loading ? "LOADING···" : "LOAD RULES"} onClick={load} disabled={loading} />
        {rules && (
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="filter by name..."
            style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
          />
        )}
      </div>
      {error && <div style={{ fontSize: 9, color: "#ff4400" }}>{error}</div>}
      {rules && (
        <div style={{ maxHeight: 360, overflowY: "auto", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px 60px", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(0,212,255,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)" }}>
            <span>NAME</span><span>DIRECTION</span><span>ACTION</span><span>STATUS</span>
          </div>
          {filtered.map((r, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px 60px", gap: 8, padding: "5px 12px", borderBottom: "1px solid rgba(0,212,255,0.04)", fontSize: 10, alignItems: "center" }}>
              <span style={{ color: "rgba(0,212,255,0.85)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.name}</span>
              <span style={{ color: "rgba(0,212,255,0.5)", fontSize: 9 }}>{r.direction}</span>
              <span style={{ color: r.action.toLowerCase().includes("allow") ? "#00ff88" : "#ff4400", fontSize: 9 }}>{r.action}</span>
              <span style={{ color: r.enabled ? "#00ff88" : "rgba(0,212,255,0.3)", fontSize: 8 }}>{r.enabled ? "ON" : "OFF"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Password Strength ────────────────────────────────────────────────────────

function PasswordTab() {
  const [password, setPassword] = useState("");
  const [result, setResult]     = useState<PasswordStrength | null>(null);
  const [loading, setLoading]   = useState(false);
  const [show, setShow]         = useState(false);

  const check = async () => {
    if (!password) return;
    setLoading(true);
    try { setResult(await checkPasswordStrength(password)); }
    finally { setLoading(false); }
  };

  const scoreColors = ["#ff4400", "#ff6600", "#00d4ff", "#a0f4ff", "#00ff88"];
  const color = result ? scoreColors[result.score] ?? "#00d4ff" : "#00d4ff";

  return (
    <div>
      <SectionHeader title="PASSWORD STRENGTH ANALYSER" icon="◎" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>Password is checked locally — never sent anywhere.</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>PASSWORD</div>
          <input type={show ? "text" : "password"} value={password}
            onChange={(e) => { setPassword(e.target.value); setResult(null); }}
            onKeyDown={(e) => e.key === "Enter" && check()}
            placeholder="Enter password to analyse..."
            style={{ width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ height: 16 }} />
          <button onClick={() => setShow(!show)} style={{ padding: "6px 10px", fontSize: 9, background: "transparent", border: "1px solid rgba(0,212,255,0.15)", color: "rgba(0,212,255,0.5)", cursor: "pointer", borderRadius: 3, fontFamily: "inherit" }}>
            {show ? "HIDE" : "SHOW"}
          </button>
        </div>
      </div>
      <Btn label={loading ? "ANALYSING···" : "ANALYSE"} onClick={check} disabled={loading || !password} />

      {result && (
        <ResultBox>
          {/* Score bar */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 14, color, textShadow: `0 0 8px ${color}` }}>{result.label}</span>
              <span style={{ fontSize: 10, color: "rgba(0,212,255,0.5)" }}>Entropy: {result.entropy.toFixed(1)} bits</span>
            </div>
            <div style={{ height: 4, background: "rgba(0,212,255,0.08)", borderRadius: 2 }}>
              <div style={{ height: "100%", width: `${(result.score / 4) * 100}%`, background: color, borderRadius: 2, boxShadow: `0 0 8px ${color}`, transition: "width 0.5s ease" }} />
            </div>
          </div>
          {result.feedback.length > 0 && (
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 8 }}>RECOMMENDATIONS</div>
              {result.feedback.map((f, i) => (
                <div key={i} style={{ display: "flex", gap: 8, fontSize: 10, color: "rgba(0,212,255,0.75)", marginBottom: 5 }}>
                  <span style={{ color: "#00d4ff" }}>›</span>{f}
                </div>
              ))}
            </div>
          )}
        </ResultBox>
      )}
    </div>
  );
}

// ─── URL Safety ───────────────────────────────────────────────────────────────

function UrlTab() {
  const { profile } = useTStore();
  const [url, setUrl]       = useState("");
  const [result, setResult] = useState<{ url: string; safe: boolean; detail: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const check = async () => {
    if (!url.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const key = profile.virusTotalKey;
      setResult(await checkUrlSafety(url.trim(), key));
    } catch (e) { setError(e instanceof Error ? e.message : "Check failed"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="URL SAFETY CHECK" icon="⊹" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Powered by VirusTotal. Add your key in Settings → Profile → VIRUSTOTAL API KEY.
      </div>
      <Field label="URL" value={url} onChange={setUrl} placeholder="https://example.com" />
      <Btn label={loading ? "CHECKING···" : "CHECK URL"} onClick={check} disabled={loading || !url.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: result.safe ? "#00ff88" : "#ff4400", textShadow: `0 0 8px ${result.safe ? "#00ff88" : "#ff4400"}` }}>
              {result.safe ? "✓ SAFE" : "⚠ THREAT DETECTED"}
            </span>
          </div>
          <div style={{ fontSize: 10, color: "rgba(0,212,255,0.7)" }}>{result.detail}</div>
        </ResultBox>
      )}
    </div>
  );
}

// ─── Security Log ─────────────────────────────────────────────────────────────

function LogTab() {
  const [events, setEvents] = useState<SecurityEvent[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");
  const [filter, setFilter] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try { setEvents(await getSecurityLog()); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  const filtered = events?.filter((e) =>
    !filter || e.message.toLowerCase().includes(filter.toLowerCase()) || e.source.toLowerCase().includes(filter.toLowerCase())
  ) ?? [];

  const levelColor: Record<string, string> = {
    error: "#ff4400", warning: "#00d4ff", info: "rgba(0,212,255,0.5)",
    Error: "#ff4400", Warning: "#00d4ff", Information: "rgba(0,212,255,0.5)",
  };

  return (
    <div>
      <SectionHeader title="SECURITY EVENT LOG" icon="◎" />
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <Btn label={loading ? "LOADING···" : "LOAD EVENTS"} onClick={load} disabled={loading} />
        {events && (
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="filter events..."
            style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
          />
        )}
      </div>
      {error && <div style={{ fontSize: 9, color: "#ff4400" }}>{error}</div>}
      {events && (
        <div style={{ maxHeight: 380, overflowY: "auto", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3 }}>
          {filtered.length === 0
            ? <div style={{ padding: 14, fontSize: 10, color: "rgba(0,212,255,0.4)" }}>No events found.</div>
            : filtered.map((ev, i) => (
              <div key={i} style={{ padding: "8px 12px", borderBottom: "1px solid rgba(0,212,255,0.04)" }}>
                <div style={{ display: "flex", gap: 10, marginBottom: 3 }}>
                  <span style={{ fontSize: 8, color: levelColor[ev.level] ?? "rgba(0,212,255,0.5)", letterSpacing: 1 }}>{ev.level.toUpperCase()}</span>
                  <span style={{ fontSize: 8, color: "rgba(0,212,255,0.35)" }}>{ev.source}</span>
                  {ev.time && <span style={{ fontSize: 8, color: "rgba(0,212,255,0.25)", marginLeft: "auto" }}>{ev.time}</span>}
                </div>
                <div style={{ fontSize: 10, color: "rgba(0,212,255,0.7)", lineHeight: 1.5 }}>{ev.message}</div>
              </div>
            ))
          }
        </div>
      )}
    </div>
  );
}


// ─── IP Intel ─────────────────────────────────────────────────────────────────

function IpIntelTab() {
  const { profile } = useTStore();
  const [ip, setIp]         = useState("");
  const [result, setResult] = useState<IpIntelResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const run = async () => {
    if (!ip.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await ipIntel(ip.trim(), profile.abuseipdbKey));
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  const scoreColor = (s: number) => s > 75 ? "#ff4400" : s > 25 ? "#00d4ff" : "#00ff88";

  return (
    <div>
      <SectionHeader title="IP INTELLIGENCE" icon="◉" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Geolocation · ASN · Reverse DNS · Abuse Score · Open Ports
      </div>
      <Field label="TARGET IP" value={ip} onChange={setIp} placeholder="1.1.1.1" />
      <Btn label={loading ? "SCANNING···" : "RUN INTEL"} onClick={run} disabled={loading || !ip.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 20px", marginBottom: 14 }}>
            {[
              ["IP",       result.ip],
              ["HOSTNAME", result.hostname],
              ["COUNTRY",  result.country],
              ["REGION",   result.region],
              ["CITY",     result.city],
              ["ASN",      result.asn],
              ["ORG",      result.org],
              ["COORDS",   `${result.latitude.toFixed(4)}, ${result.longitude.toFixed(4)}`],
            ].map(([k, v]) => (
              <div key={k}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 2 }}>{k}</div>
                <div style={{ fontSize: 10, color: "rgba(160,244,255,0.85)", wordBreak: "break-all" }}>{v || "—"}</div>
              </div>
            ))}
          </div>

          <div style={{ borderTop: "1px solid rgba(0,212,255,0.08)", paddingTop: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 6 }}>ABUSE SCORE</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 22, fontWeight: "bold", color: scoreColor(result.abuse_score), textShadow: `0 0 12px ${scoreColor(result.abuse_score)}` }}>
                {result.abuse_score}%
              </span>
              <span style={{ fontSize: 9, color: "rgba(0,212,255,0.5)" }}>{result.abuse_detail}</span>
            </div>
          </div>

          <div style={{ borderTop: "1px solid rgba(0,212,255,0.08)", paddingTop: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 6 }}>
              OPEN PORTS ({result.open_ports.length})
            </div>
            {result.open_ports.length === 0
              ? <div style={{ fontSize: 9, color: "#00ff88" }}>No common ports open</div>
              : <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {result.open_ports.map((p) => (
                    <span key={p} style={{ fontSize: 9, padding: "2px 8px", border: "1px solid rgba(255,68,0,0.4)", color: "#0088cc", borderRadius: 2 }}>
                      {p}
                    </span>
                  ))}
                </div>
            }
          </div>
        </ResultBox>
      )}
    </div>
  );
}

// ─── Email OSINT ──────────────────────────────────────────────────────────────

function EmailOsintTab() {
  const { profile } = useTStore();
  const [email, setEmail]   = useState("");
  const [hibpKey, setHibpKey] = useState("");
  const [result, setResult] = useState<EmailOsintResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const run = async () => {
    if (!email.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await emailOsint(email.trim(), hibpKey || profile.hibpKey));
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="EMAIL OSINT" icon="✉" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Breach history · MX records · Gravatar profile · Domain intel
      </div>
      <Field label="EMAIL ADDRESS" value={email} onChange={setEmail} placeholder="target@example.com" />
      <Field label="HIBP API KEY (optional)" value={hibpKey} onChange={setHibpKey} placeholder="Get free key at haveibeenpwned.com" />
      <Btn label={loading ? "SCANNING···" : "RUN OSINT"} onClick={run} disabled={loading || !email.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          {/* Validity + Domain */}
          <div style={{ display: "flex", gap: 16, marginBottom: 14, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>STATUS</div>
              <span style={{ fontSize: 10, color: result.valid ? "#00ff88" : "#ff4400" }}>
                {result.valid ? "VALID FORMAT" : "INVALID FORMAT"}
              </span>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>DOMAIN</div>
              <span style={{ fontSize: 10, color: "rgba(160,244,255,0.85)" }}>{result.domain || "—"}</span>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>GRAVATAR</div>
              <span style={{ fontSize: 10, color: result.gravatar_url ? "#00ff88" : "rgba(0,212,255,0.4)" }}>
                {result.gravatar_url ? "PROFILE EXISTS" : "NOT FOUND"}
              </span>
            </div>
          </div>

          {/* Gravatar image */}
          {result.gravatar_url && (
            <div style={{ marginBottom: 14 }}>
              <img src={result.gravatar_url} alt="gravatar" style={{ width: 60, height: 60, borderRadius: 4, border: "1px solid rgba(0,212,255,0.2)" }} />
            </div>
          )}

          {/* MX Records */}
          {result.mx_records.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 6 }}>MX RECORDS</div>
              {result.mx_records.map((mx, i) => (
                <div key={i} style={{ fontSize: 9, color: "rgba(0,212,255,0.65)", marginBottom: 2 }}>{mx}</div>
              ))}
            </div>
          )}

          {/* Breach summary */}
          <div style={{ borderTop: "1px solid rgba(0,212,255,0.08)", paddingTop: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: 18, fontWeight: "bold", color: result.breach_count > 0 ? "#ff4400" : "#00ff88", textShadow: result.breach_count > 0 ? "0 0 12px #ff4400" : "0 0 8px #00ff88" }}>
                {result.breach_count}
              </span>
              <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.5)" }}>
                {result.breach_count === 0 ? "NO BREACHES FOUND" : "BREACHES DETECTED"}
              </span>
            </div>
            {result.breaches.map((b) => (
              <div key={b.name} style={{ marginBottom: 10, padding: "8px 10px", background: "rgba(255,68,0,0.04)", border: "1px solid rgba(255,68,0,0.15)", borderRadius: 3 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 10, color: "#0088cc", fontWeight: "bold" }}>{b.name}</span>
                  <span style={{ fontSize: 8, color: "rgba(0,212,255,0.4)" }}>{b.breach_date}</span>
                </div>
                <div style={{ fontSize: 8, color: "rgba(0,212,255,0.5)", marginBottom: 4 }}>{b.domain}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {b.data_classes.map((dc) => (
                    <span key={dc} style={{ fontSize: 7, padding: "1px 6px", border: "1px solid rgba(255,68,0,0.25)", color: "#ff4400", borderRadius: 2 }}>{dc}</span>
                  ))}
                </div>
                <div style={{ fontSize: 8, color: "rgba(0,212,255,0.35)", marginTop: 4 }}>
                  {b.pwn_count.toLocaleString()} accounts compromised
                </div>
              </div>
            ))}
          </div>
        </ResultBox>
      )}
    </div>
  );
}

// ─── CVE Search ───────────────────────────────────────────────────────────────

function CveTab() {
  const [query, setQuery]   = useState("");
  const [results, setResults] = useState<CveEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const run = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(""); setResults([]);
    try {
      setResults(await cveSearch(query.trim()));
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  const severityColor = (s: string) => {
    switch (s.toUpperCase()) {
      case "CRITICAL": return "#ff0000";
      case "HIGH":     return "#ff4400";
      case "MEDIUM":   return "#00d4ff";
      case "LOW":      return "#a0f4ff";
      default:         return "rgba(0,212,255,0.4)";
    }
  };

  return (
    <div>
      <SectionHeader title="CVE SEARCH" icon="⚠" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Search NIST National Vulnerability Database. Enter service name, software, or CVE ID.
      </div>
      <Field label="SEARCH QUERY" value={query} onChange={setQuery} placeholder="apache 2.4 / openssl / CVE-2024-..." />
      <Btn label={loading ? "SEARCHING···" : "SEARCH NVD"} onClick={run} disabled={loading || !query.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {results.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>
            {results.length} RESULTS
          </div>
          {results.map((cve) => (
            <div key={cve.id} style={{ marginBottom: 10, padding: "10px 14px", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.08)", borderLeft: `3px solid ${severityColor(cve.severity)}`, borderRadius: "0 3px 3px 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: "bold", color: "#a0f4ff", letterSpacing: 1 }}>{cve.id}</span>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: severityColor(cve.severity), fontWeight: "bold", textShadow: `0 0 8px ${severityColor(cve.severity)}` }}>
                    {cve.cvss_score.toFixed(1)}
                  </span>
                  <span style={{ fontSize: 7, padding: "1px 7px", border: `1px solid ${severityColor(cve.severity)}`, color: severityColor(cve.severity), borderRadius: 2, letterSpacing: 2 }}>
                    {cve.severity}
                  </span>
                </div>
              </div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.65)", lineHeight: 1.6, marginBottom: 6 }}>
                {cve.description.slice(0, 300)}{cve.description.length > 300 ? "..." : ""}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 7, color: "rgba(0,212,255,0.3)", letterSpacing: 2 }}>
                  {cve.published.slice(0, 10)}
                </span>
                {cve.references[0] && (
                  <a href={cve.references[0]} target="_blank" rel="noreferrer" style={{ fontSize: 7, color: "rgba(0,212,255,0.4)", letterSpacing: 2 }}>
                    REF ↗
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Panel ───────────────────────────────────────────────────────────────


// ─── Full Port Scanner ────────────────────────────────────────────────────────

function FullPortScanTab() {
  const [host, setHost]         = useState("");
  const [startPort, setStartPort] = useState("1");
  const [endPort, setEndPort]   = useState("1024");
  const [result, setResult]     = useState<FullScanResult | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  const run = async () => {
    const s = parseInt(startPort, 10);
    const e = parseInt(endPort, 10);
    if (!host.trim()) { setError("Enter a host or IP"); return; }
    if (isNaN(s) || isNaN(e) || s < 1 || e > 65535 || s > e) { setError("Invalid port range (1-65535, start ≤ end)"); return; }
    if (e - s + 1 > 10000) { setError("Maximum 10 000 ports per scan"); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await fullPortScan(host.trim(), s, e));
    } catch (err) { setError(err instanceof Error ? err.message : "Scan failed"); }
    finally { setLoading(false); }
  };

  const presets = [
    { label: "TOP 100",  s: "1",   e: "1024"  },
    { label: "TOP 1K",   s: "1",   e: "1000"  },
    { label: "WEB",      s: "80",  e: "9000"  },
    { label: "DB",       s: "1433",e: "27017" },
  ];

  return (
    <div>
      <SectionHeader title="FULL PORT SCANNER" icon="⬡" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12 }}>
        Parallel TCP connect scan · Max 10 000 ports · Only scan systems you own or have permission to test
      </div>

      <Field label="HOST / IP" value={host} onChange={setHost} placeholder="192.168.1.1 or example.com" />

      <div style={{ display: "flex", gap: 10, marginBottom: 12, alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>START PORT</div>
          <input
            value={startPort} onChange={(e) => setStartPort(e.target.value)}
            style={{ width: "100%", background: "rgba(0,212,255,0.04)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none" }}
          />
        </div>
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.3)", paddingBottom: 8 }}>–</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>END PORT</div>
          <input
            value={endPort} onChange={(e) => setEndPort(e.target.value)}
            style={{ width: "100%", background: "rgba(0,212,255,0.04)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none" }}
          />
        </div>
      </div>

      {/* Presets */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {presets.map((p) => (
          <button key={p.label} onClick={() => { setStartPort(p.s); setEndPort(p.e); }}
            style={{ fontSize: 7, letterSpacing: 2, padding: "3px 10px", background: "transparent", border: "1px solid rgba(0,212,255,0.2)", color: "rgba(0,212,255,0.5)", borderRadius: 2, cursor: "pointer", fontFamily: "inherit" }}>
            {p.label}
          </button>
        ))}
      </div>

      <Btn label={loading ? `SCANNING···` : "RUN SCAN"} onClick={run} disabled={loading || !host.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}

      {result && (
        <ResultBox>
          {/* Summary row */}
          <div style={{ display: "flex", gap: 24, marginBottom: 14, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>HOST</div>
              <div style={{ fontSize: 10, color: "rgba(160,244,255,0.85)" }}>{result.host}</div>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>SCANNED</div>
              <div style={{ fontSize: 10, color: "rgba(160,244,255,0.85)" }}>{result.scanned.toLocaleString()} ports</div>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>OPEN</div>
              <div style={{ fontSize: 18, fontWeight: "bold", color: result.open.length > 0 ? "#0088cc" : "#00ff88", textShadow: result.open.length > 0 ? "0 0 10px #0088cc" : "0 0 8px #00ff88" }}>
                {result.open.length}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 3 }}>DURATION</div>
              <div style={{ fontSize: 10, color: "rgba(160,244,255,0.85)" }}>{(result.duration_ms / 1000).toFixed(1)}s</div>
            </div>
          </div>

          {result.open.length === 0
            ? <div style={{ fontSize: 9, color: "#00ff88" }}>No open ports found in range</div>
            : (
              <div>
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>OPEN PORTS</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 6 }}>
                  {result.open.map((p) => (
                    <div key={p.port} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 10px", background: "rgba(0,136,204,0.05)", border: "1px solid rgba(0,136,204,0.2)", borderRadius: 3 }}>
                      <span style={{ fontSize: 11, fontWeight: "bold", color: "#0088cc", minWidth: 36 }}>{p.port}</span>
                      <span style={{ fontSize: 8, color: "rgba(0,212,255,0.55)", letterSpacing: 1 }}>{p.service || "UNKNOWN"}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          }
        </ResultBox>
      )}
    </div>
  );
}

// ─── Local Access ─────────────────────────────────────────────────────────────

function LocalAccessTab() {
  const {
    state, readyPayload, progress, fullOutput, hashes,
    summary, error, memoryResult,
    startSession, confirm, cancel, endSession, inspectMemory,
  } = (window as any).__useLocalAccess?.() ?? _useLocalAccessFallback();

  const [pidInput, setPidInput] = useState("");
  const [patInput, setPatInput] = useState("");

  const isIdle    = state === "idle"    || state === "done" || state === "error";
  const statusColors: Record<string, string> = {
    idle:             "rgba(0,212,255,0.4)",
    checking:         "#00d4ff",
    awaiting_confirm: "#00d4ff",
    elevating:        "#ff9900",
    running:          "#00ff88",
    done:             "#00ff88",
    error:            "#ff4400",
  };
  const statusColor = statusColors[state] ?? "rgba(0,212,255,0.4)";

  return (
    <div>
      <SectionHeader title="LOCAL ACCESS" icon="⚡" />

      {/* Status row + kill switch */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor, boxShadow: `0 0 6px ${statusColor}` }} />
          <span style={{ fontSize: 9, letterSpacing: 3, color: statusColor }}>{state.toUpperCase().replace("_", " ")}</span>
        </div>
        {!isIdle && (
          <Btn label="■ END SESSION" onClick={endSession} danger />
        )}
      </div>

      {/* Error */}
      {error && (
        <div style={{ background: "rgba(255,68,0,0.08)", border: "1px solid rgba(255,68,0,0.2)", borderRadius: 3, padding: "10px 14px", marginBottom: 14, fontSize: 10, color: "#ff6644" }}>
          {error}
        </div>
      )}

      {/* Start button */}
      {state === "idle" && (
        <div style={{ marginBottom: 16 }}>
          <Btn label="EXTRACT ALL CREDENTIALS" onClick={startSession} />
          <div style={{ marginTop: 8, fontSize: 9, color: "rgba(0,212,255,0.35)", lineHeight: 1.6 }}>
            Extracts from: LSASS · SAM · Credential Manager · Browsers · WiFi · Env Vars · Scheduled Tasks · Registry
          </div>
        </div>
      )}

      {/* Confirmation prompt */}
      {state === "awaiting_confirm" && readyPayload && (
        <div style={{ background: "rgba(0,212,255,0.04)", border: "1px solid rgba(0,212,255,0.2)", borderRadius: 4, padding: "14px 16px", marginBottom: 16 }}>
          <div style={{ fontSize: 9, letterSpacing: 2, color: "#00d4ff", marginBottom: 10 }}>CONFIRMATION REQUIRED</div>
          <pre style={{ fontSize: 9, color: "rgba(160,244,255,0.7)", lineHeight: 1.7, whiteSpace: "pre-wrap", margin: "0 0 14px" }}>
            {(readyPayload as any).risk_summary}
          </pre>
          <div style={{ display: "flex", gap: 10 }}>
            <Btn label="YES — PROCEED" onClick={confirm} />
            <Btn label="CANCEL"        onClick={cancel}  danger />
          </div>
        </div>
      )}

      {/* Progress */}
      {progress.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 8 }}>PROGRESS</div>
          {progress.map((p: LocalAccessProgress) => (
            <div key={p.source} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <span style={{
                fontSize: 8, letterSpacing: 2, padding: "1px 6px",
                border: `1px solid ${p.status === "done" ? "#00ff88" : p.status === "failed" ? "#ff4400" : "#00d4ff"}`,
                color:         p.status === "done" ? "#00ff88" : p.status === "failed" ? "#ff4400" : "#00d4ff",
                borderRadius: 2, minWidth: 50, textAlign: "center",
              }}>
                {p.status.toUpperCase()}
              </span>
              <span style={{ fontSize: 10, color: "rgba(160,244,255,0.7)" }}>{p.source}</span>
              {p.error && <span style={{ fontSize: 9, color: "#ff6644" }}>{p.error}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div style={{ background: "rgba(0,255,136,0.04)", border: "1px solid rgba(0,255,136,0.15)", borderRadius: 3, padding: "10px 14px", marginBottom: 14, fontSize: 10, color: "#00ff88", lineHeight: 1.6 }}>
          {summary}
        </div>
      )}

      {/* NTLM Hashes */}
      {hashes.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 6 }}>NTLM HASHES ({hashes.length})</div>
          <div style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, padding: "10px 14px", fontFamily: "monospace", fontSize: 10 }}>
            {hashes.map((h: string, i: number) => (
              <div key={i} style={{ color: "rgba(160,244,255,0.8)", marginBottom: 2 }}>{h}</div>
            ))}
          </div>
        </div>
      )}

      {/* Full output */}
      {fullOutput && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 6 }}>FULL OUTPUT</div>
          <pre style={{
            background: "rgba(0,0,0,0.4)", border: "1px solid rgba(0,212,255,0.08)",
            borderRadius: 3, padding: "12px 14px", fontSize: 9, lineHeight: 1.7,
            color: "rgba(160,244,255,0.75)", overflowX: "auto", whiteSpace: "pre-wrap",
            maxHeight: 400, overflowY: "auto",
          }}>
            {fullOutput}
          </pre>
        </div>
      )}

      {/* Memory inspector */}
      {(state === "running" || state === "done") && (
        <div style={{ borderTop: "1px solid rgba(0,212,255,0.08)", paddingTop: 16 }}>
          <SectionHeader title="MEMORY INSPECTOR" icon="🔍" />
          <div style={{ display: "flex", gap: 10, marginBottom: 10, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <Field label="PID (blank = all processes)" value={pidInput} onChange={setPidInput} placeholder="e.g. 1234" />
            </div>
            <div style={{ flex: 2 }}>
              <Field label="Pattern (optional)" value={patInput} onChange={setPatInput} placeholder="e.g. password[:=]" />
            </div>
            <Btn label="SCAN" onClick={() => {
              const pid  = pidInput ? parseInt(pidInput) : null;
              const pats = patInput ? [patInput] : undefined;
              inspectMemory(pid, pats);
            }} />
          </div>
          {memoryResult && (
            <pre style={{
              background: "rgba(0,0,0,0.4)", border: "1px solid rgba(0,212,255,0.08)",
              borderRadius: 3, padding: "10px 14px", fontSize: 9, lineHeight: 1.7,
              color: "rgba(160,244,255,0.75)", whiteSpace: "pre-wrap",
              maxHeight: 300, overflowY: "auto",
            }}>
              {JSON.stringify(memoryResult, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

function _useLocalAccessFallback() {
  return {
    state: "idle" as const, readyPayload: null, progress: [], fullOutput: "",
    hashes: [], summary: "", error: "", memoryResult: null,
    startSession: () => {}, confirm: () => {}, cancel: () => {},
    endSession: () => {}, inspectMemory: () => {},
  };
}

// ─── Shared offensive helpers ─────────────────────────────────────────────────

const RISK_COLOR: Record<RiskLevel, string> = {
  LOW:      "#00ff88",
  MEDIUM:   "#ffb300",
  HIGH:     "#ff6600",
  CRITICAL: "#ff2200",
};

function ConfirmModal({ req, onConfirm }: { req: OffensiveConfirmRequest; onConfirm: (confirmed: boolean) => void }) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      background: "rgba(0,0,0,0.82)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "#000a15", border: "1px solid rgba(0,212,255,0.25)",
        borderRadius: 6, padding: "28px 32px", maxWidth: 520, width: "90%",
      }}>
        <div style={{ fontSize: 8, letterSpacing: 5, color: "rgba(0,212,255,0.4)", marginBottom: 14 }}>
          OFFENSIVE ACTION · CONFIRMATION REQUIRED
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{
            padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
            border: `1px solid ${RISK_COLOR[req.risk]}`,
            color: RISK_COLOR[req.risk],
          }}>{req.risk}</div>
          <span style={{ color: "#a0f4ff", fontSize: 13, fontWeight: 600 }}>{req.tool}</span>
        </div>
        <div style={{
          fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.7)",
          background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.08)",
          borderRadius: 3, padding: "8px 12px", marginBottom: 14, wordBreak: "break-all",
        }}>{req.command}</div>
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.55)", marginBottom: 22, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
          {req.description}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn label="CANCEL"  onClick={() => onConfirm(false)} danger />
          <Btn label="CONFIRM" onClick={() => onConfirm(true)} />
        </div>
      </div>
    </div>
  );
}

function ToolMissingModal({ tool, install_cmd, onInstall, onDismiss }: {
  tool: string; install_cmd: string;
  onInstall: () => void; onDismiss: () => void;
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      background: "rgba(0,0,0,0.80)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "#000a15", border: "1px solid rgba(255,179,0,0.25)",
        borderRadius: 6, padding: "24px 28px", maxWidth: 440, width: "90%",
      }}>
        <div style={{ fontSize: 8, letterSpacing: 5, color: "#ffb300", marginBottom: 12 }}>TOOL NOT FOUND</div>
        <div style={{ fontSize: 12, color: "#a0f4ff", marginBottom: 8 }}>
          <strong>{tool}</strong> is not installed on the VM.
        </div>
        <div style={{
          fontFamily: "monospace", fontSize: 9, color: "rgba(0,212,255,0.6)",
          background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.08)",
          borderRadius: 3, padding: "6px 10px", marginBottom: 18,
        }}>{install_cmd}</div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn label="CANCEL"  onClick={onDismiss} danger />
          <Btn label="INSTALL ON VM" onClick={onInstall} />
        </div>
      </div>
    </div>
  );
}

function StreamOutput({ lines, onClear }: { lines: { chunk: string; ts: number }[]; onClear: () => void }) {
  if (lines.length === 0) return null;
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.35)" }}>OUTPUT</span>
        <button onClick={onClear} style={{
          fontSize: 7, padding: "2px 8px", background: "transparent",
          border: "1px solid rgba(0,212,255,0.15)", color: "rgba(0,212,255,0.4)",
          cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
        }}>CLEAR</button>
      </div>
      <div style={{
        background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
        borderRadius: 3, padding: "10px 12px", maxHeight: 340, overflowY: "auto",
        fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.75)", lineHeight: 1.6,
      }}>
        {lines.map((l, i) => (
          <div key={i} style={{ color: l.chunk.startsWith("[ERROR]") || l.chunk.startsWith("[EXIT:") ? "#ff4400" : undefined }}>
            {l.chunk}
          </div>
        ))}
      </div>
    </div>
  );
}

// Generic param input row
function ParamRow({ label, value, onChange, placeholder = "" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>{label}</div>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{
          width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
          borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
          fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff",
        }}
        onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
        onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
      />
    </div>
  );
}

// Offensive tab wrapper — handles confirm/missing modals and stream output
function OffensiveTab({ title, icon, children, actionId }: {
  title: string; icon: string;
  children: (dispatch: ReturnType<typeof useOffensive>["dispatch"]) => React.ReactNode;
  actionId: React.MutableRefObject<string>;
}) {
  const off = useOffensive();
  const myLines = off.streamLines.filter(l => l.id === actionId.current);

  return (
    <div>
      {off.confirmReq && <ConfirmModal req={off.confirmReq} onConfirm={confirmed => off.confirm(off.confirmReq!.id, confirmed)} />}
      {off.toolMissing && (
        <ToolMissingModal
          tool={off.toolMissing.tool}
          install_cmd={off.toolMissing.install_cmd}
          onInstall={() => off.installTool(off.toolMissing!.tool)}
          onDismiss={() => {}}
        />
      )}
      <SectionHeader title={title} icon={icon} />
      {off.error && (
        <div style={{
          background: "rgba(255,68,0,0.06)", border: "1px solid rgba(255,68,0,0.2)",
          borderRadius: 3, padding: "8px 12px", marginBottom: 12, fontSize: 10,
          color: "#ff4400", display: "flex", justifyContent: "space-between",
        }}>
          <span>{off.error}</span>
          <button onClick={off.clearError} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}
      {children(off.dispatch)}
      <StreamOutput lines={myLines} onClear={() => off.clearStream(actionId.current)} />
    </div>
  );
}

// ─── VM Tab ───────────────────────────────────────────────────────────────────

function VmTab() {
  const vm = useVmStatus();
  const off = useOffensive();
  const [snapName, setSnapName] = useState("clean_state");
  const [customCmd, setCustomCmd] = useState("");
  const [checkingTools, setCheckingTools] = useState(false);
  const actionId = { current: "vm-terminal" };
  const myLines = off.streamLines.filter(l => l.id === actionId.current);

  const TOOL_GROUPS = [
    { label: "Recon",    tools: ["nmap","masscan","amass","subfinder","theharvester"] },
    { label: "Web",      tools: ["nikto","sqlmap","ffuf","gobuster","nuclei","wpscan"] },
    { label: "Crack",    tools: ["hashcat","john","hydra","medusa"] },
    { label: "Exploit",  tools: ["msfconsole","searchsploit","beef-xss"] },
    { label: "WiFi",     tools: ["airmon-ng","airodump-ng","aireplay-ng","hcxdumptool","wifite"] },
    { label: "MITM",     tools: ["ettercap","arpspoof","mitmproxy","responder","tcpdump","tshark"] },
    { label: "Payload",  tools: ["msfvenom","veil"] },
    { label: "OSINT",    tools: ["phoneinfoga","sherlock","holehe","maigret","exiftool"] },
    { label: "Forensics",tools: ["binwalk","steghide","foremost","volatility3"] },
  ];
  const allTools = TOOL_GROUPS.flatMap(g => g.tools);

  const runCheck = () => {
    setCheckingTools(true);
    vm.checkTools(allTools);
    setTimeout(() => setCheckingTools(false), 8000);
  };

  const runCustom = () => {
    if (!customCmd.trim()) return;
    actionId.current = crypto.randomUUID();
    off.dispatch("custom", {}, customCmd.trim());
  };

  return (
    <div>
      {off.confirmReq && <ConfirmModal req={off.confirmReq} onConfirm={confirmed => off.confirm(off.confirmReq!.id, confirmed)} />}
      <SectionHeader title="ATTACK VM — VIRTUALBOX" icon="⌁" />

      {/* Status */}
      <div style={{ display: "flex", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        {[
          { label: "VM STATE", val: vm.status?.running ? "RUNNING" : "STOPPED",
            color: vm.status?.running ? "#00ff88" : "rgba(0,212,255,0.3)" },
          { label: "SSH",  val: vm.status?.ssh_ok ? "CONNECTED" : "OFFLINE",
            color: vm.status?.ssh_ok ? "#00ff88" : "#ff4400" },
          { label: "IP",   val: vm.status?.vm_ip || "—",    color: "#00d4ff" },
          { label: "NAME", val: vm.status?.vm_name || "—",  color: "#00d4ff" },
        ].map(({ label, val, color }) => (
          <div key={label} style={{
            background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.08)",
            borderRadius: 3, padding: "8px 14px",
          }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 11, color, fontWeight: 600 }}>{val}</div>
          </div>
        ))}
      </div>

      {/* VM message */}
      {vm.status?.message && (
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.6)", marginBottom: 12, fontFamily: "monospace" }}>
          {vm.status.message}
        </div>
      )}

      {/* Controls */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
        <Btn label={vm.loading ? "···" : "REFRESH"} onClick={vm.refresh} disabled={vm.loading} />
        <Btn label="START VM" onClick={vm.start}   disabled={vm.loading || !!vm.status?.running} />
        <Btn label="STOP VM"  onClick={vm.stop}    disabled={vm.loading || !vm.status?.running} danger />
        <Btn label={checkingTools ? "CHECKING···" : "CHECK ALL TOOLS"} onClick={runCheck} disabled={checkingTools} />
      </div>

      {/* Snapshot */}
      <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
        <input value={snapName} onChange={e => setSnapName(e.target.value)}
          style={{
            flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
            borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
            fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff",
          }}
          onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
        <Btn label="SNAPSHOT" onClick={() => vm.snapshot(snapName)} />
        <Btn label="RESTORE"  onClick={() => vm.restore(snapName)} danger />
      </div>

      {/* Tool status grid */}
      {Object.keys(vm.toolStatus).length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>TOOL STATUS</div>
          {TOOL_GROUPS.map(({ label, tools }) => (
            <div key={label} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.3)", marginBottom: 4 }}>{label}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {tools.map(t => {
                  const found = vm.toolStatus[t];
                  return (
                    <div key={t} style={{
                      padding: "2px 8px", fontSize: 8, borderRadius: 2,
                      background: found ? "rgba(0,255,136,0.06)" : "rgba(255,68,0,0.06)",
                      border: `1px solid ${found ? "rgba(0,255,136,0.2)" : "rgba(255,68,0,0.15)"}`,
                      color: found ? "#00ff88" : "rgba(255,68,0,0.7)",
                    }}>{t}</div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SSH terminal */}
      <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>SSH TERMINAL</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
        <input value={customCmd} onChange={e => setCustomCmd(e.target.value)}
          onKeyDown={e => e.key === "Enter" && runCustom()}
          placeholder="Enter any command to run on VM..."
          style={{
            flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
            borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
            fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: "#00d4ff",
          }}
          onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
        <Btn label="RUN" onClick={runCustom} />
      </div>
      <StreamOutput lines={myLines} onClear={() => off.clearStream(actionId.current)} />
    </div>
  );
}

// ─── Crack Tab ────────────────────────────────────────────────────────────────

function CrackTab() {
  const [hash,     setHash]     = useState("");
  const [wordlist, setWordlist] = useState("/usr/share/wordlists/rockyou.txt");
  const [mode,     setMode]     = useState("1000");
  const actionId = { current: "" };
  const MODES = [
    { v: "1000",  l: "NTLM (1000)" }, { v: "0",     l: "MD5 (0)"        },
    { v: "100",   l: "SHA1 (100)"  }, { v: "1400",  l: "SHA256 (1400)"  },
    { v: "22000", l: "WPA (22000)" }, { v: "3200",  l: "bcrypt (3200)"  },
    { v: "13100", l: "Kerberoast (13100)" }, { v: "5500", l: "NTLMv1 (5500)" },
  ];
  return (
    <OffensiveTab title="HASH CRACKING" icon="🔑" actionId={actionId}>
      {dispatch => (
        <>
          <ParamRow label="HASH VALUE / HASHFILE PATH" value={hash} onChange={setHash} placeholder="aad3b435b51404eeaad3b435b51404ee or /tmp/hashes.txt" />
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>MODE</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {MODES.map(m => (
                <button key={m.v} onClick={() => setMode(m.v)} style={{
                  padding: "4px 10px", fontSize: 8, letterSpacing: 1,
                  background: mode === m.v ? "rgba(0,212,255,0.1)" : "transparent",
                  border: `1px solid ${mode === m.v ? "rgba(0,212,255,0.4)" : "rgba(0,212,255,0.12)"}`,
                  color: mode === m.v ? "#00d4ff" : "rgba(0,212,255,0.4)",
                  cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
                }}>{m.l}</button>
              ))}
            </div>
          </div>
          <ParamRow label="WORDLIST (VM PATH)" value={wordlist} onChange={setWordlist} placeholder="/usr/share/wordlists/rockyou.txt" />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn label="CRACK WITH HASHCAT" onClick={() => { actionId.current = dispatch("hashcat", { hash, mode, wordlist }); }} />
            <Btn label="CRACK WITH JOHN"    onClick={() => { actionId.current = dispatch("john", { hashfile: hash, wordlist }); }} />
          </div>
        </>
      )}
    </OffensiveTab>
  );
}

// ─── Exploit Tab ──────────────────────────────────────────────────────────────

function ExploitTab() {
  const [query,   setQuery]   = useState("");
  const [module,  setModule]  = useState("");
  const [options, setOptions] = useState("RHOSTS= LHOST= LPORT=4444");
  const actionId = { current: "" };

  return (
    <OffensiveTab title="EXPLOITATION — METASPLOIT" icon="💀" actionId={actionId}>
      {dispatch => (
        <>
          {/* Searchsploit */}
          <div style={{ marginBottom: 18 }}>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>SEARCHSPLOIT</div>
            <div style={{ display: "flex", gap: 8 }}>
              <input value={query} onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && (actionId.current = dispatch("searchsploit", { query }))}
                placeholder="e.g. apache 2.4 rce"
                style={{
                  flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
                  borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
                  fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff",
                }}
                onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
                onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
              />
              <Btn label="SEARCH" onClick={() => { actionId.current = dispatch("searchsploit", { query }); }} />
            </div>
          </div>

          {/* Metasploit */}
          <div style={{ marginBottom: 18 }}>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>METASPLOIT MODULE</div>
            <ParamRow label="MODULE PATH" value={module} onChange={setModule} placeholder="exploit/multi/handler" />
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>OPTIONS (space-separated KEY=VALUE)</div>
              <textarea value={options} onChange={e => setOptions(e.target.value)} rows={2}
                style={{
                  width: "100%", resize: "vertical",
                  background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
                  borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
                  fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: "#00d4ff",
                }}
                onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
                onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
              />
            </div>
            <Btn label="RUN METASPLOIT MODULE" onClick={() => {
              const opts: Record<string, string> = {};
              options.split(/\s+/).forEach(pair => {
                const [k, ...v] = pair.split("=");
                if (k && v.length) opts[k] = v.join("=");
              });
              actionId.current = dispatch("msfconsole", { module, options: opts });
            }} />
          </div>
        </>
      )}
    </OffensiveTab>
  );
}

// ─── WiFi Tab ─────────────────────────────────────────────────────────────────

function WifiTab() {
  const [iface,    setIface]    = useState("wlan0");
  const [bssid,    setBssid]    = useState("");
  const [channel,  setChannel]  = useState("");
  const [capture,  setCapture]  = useState("/tmp/handshake.cap");
  const [wordlist, setWordlist] = useState("/usr/share/wordlists/rockyou.txt");
  const [deauthCount, setDeauthCount] = useState("10");
  const actionId = { current: "" };

  return (
    <OffensiveTab title="WIFI ATTACKS" icon="📡" actionId={actionId}>
      {dispatch => (
        <>
          <div style={{
            background: "rgba(255,34,0,0.05)", border: "1px solid rgba(255,34,0,0.15)",
            borderRadius: 3, padding: "8px 12px", marginBottom: 14, fontSize: 9,
            color: "rgba(255,100,0,0.8)",
          }}>
            ⚠ Only use against networks you own or have explicit written permission to test.
          </div>
          <ParamRow label="WIRELESS INTERFACE"      value={iface}   onChange={setIface}   placeholder="wlan0" />
          <ParamRow label="TARGET BSSID (optional)" value={bssid}   onChange={setBssid}   placeholder="AA:BB:CC:DD:EE:FF" />
          <ParamRow label="CHANNEL (optional)"      value={channel} onChange={setChannel} placeholder="6" />
          <ParamRow label="CAPTURE OUTPUT PATH"     value={capture} onChange={setCapture} placeholder="/tmp/handshake.cap" />

          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <Btn label="ENABLE MONITOR MODE" onClick={() => { actionId.current = dispatch("airmon-ng", { interface: iface, action: "start" }); }} />
            <Btn label="STOP MONITOR MODE"   onClick={() => { actionId.current = dispatch("airmon-ng", { interface: `${iface}mon`, action: "stop" }); }} />
            <Btn label="SCAN NETWORKS"       onClick={() => { actionId.current = dispatch("airodump-ng", { interface: `${iface}mon`, output: capture }); }} />
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <ParamRow label="DEAUTH COUNT" value={deauthCount} onChange={setDeauthCount} placeholder="10" />
            </div>
            <div style={{ paddingBottom: 10 }}>
              <Btn label="DEAUTH ATTACK" onClick={() => { actionId.current = dispatch("aireplay-ng", { interface: `${iface}mon`, bssid, attack: "0", count: deauthCount }); }} danger />
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <Btn label="PMKID CAPTURE (hcxdumptool)" onClick={() => { actionId.current = dispatch("hcxdumptool", { interface: iface, output: capture.replace(".cap", ".pcapng") }); }} />
            <Btn label="CONVERT → HASHCAT"           onClick={() => { actionId.current = dispatch("hcxtools",   { input: capture.replace(".cap",".pcapng"), output: capture.replace(".cap",".hash") }); }} />
          </div>

          <ParamRow label="WORDLIST FOR CRACK" value={wordlist} onChange={setWordlist} placeholder="/usr/share/wordlists/rockyou.txt" />
          <Btn label="CRACK WPA HANDSHAKE (hashcat mode 22000)" onClick={() => { actionId.current = dispatch("hashcat", { hash: capture.replace(".cap",".hash"), mode: "22000", wordlist }); }} />
        </>
      )}
    </OffensiveTab>
  );
}

// ─── MITM Tab ─────────────────────────────────────────────────────────────────

function MitmTab() {
  const [iface,   setIface]   = useState("eth0");
  const [target,  setTarget]  = useState("");
  const [gateway, setGateway] = useState("");
  const [port,    setPort]    = useState("8080");
  const [filter,  setFilter]  = useState("");
  const actionId = { current: "" };

  return (
    <OffensiveTab title="MITM & NETWORK INTERCEPTION" icon="🕸" actionId={actionId}>
      {dispatch => (
        <>
          <div style={{
            background: "rgba(255,34,0,0.05)", border: "1px solid rgba(255,34,0,0.15)",
            borderRadius: 3, padding: "8px 12px", marginBottom: 14, fontSize: 9,
            color: "rgba(255,100,0,0.8)",
          }}>
            ⚠ ARP poisoning on networks you don't own is illegal. Only test on your own lab network.
          </div>
          <ParamRow label="INTERFACE"      value={iface}   onChange={setIface}   placeholder="eth0" />
          <ParamRow label="TARGET IP"      value={target}  onChange={setTarget}  placeholder="192.168.1.50" />
          <ParamRow label="GATEWAY IP"     value={gateway} onChange={setGateway} placeholder="192.168.1.1" />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <Btn label="ARP POISON (arpspoof)" onClick={() => { actionId.current = dispatch("arpspoof", { interface: iface, target, gateway }); }} danger />
            <Btn label="RESPONDER (LLMNR)"     onClick={() => { actionId.current = dispatch("responder", { interface: iface }); }} danger />
            <Btn label="SSL STRIP"             onClick={() => { actionId.current = dispatch("sslstrip",  { port: "10000" }); }} danger />
          </div>
          <ParamRow label="MITMPROXY PORT" value={port}   onChange={setPort}   placeholder="8080" />
          <Btn label="START MITMPROXY" onClick={() => { actionId.current = dispatch("mitmproxy", { port }); }} />
          <div style={{ marginTop: 16 }}>
            <ParamRow label="TCPDUMP FILTER (optional)" value={filter} onChange={setFilter} placeholder="port 80 or host 192.168.1.50" />
            <div style={{ display: "flex", gap: 8 }}>
              <Btn label="TCPDUMP CAPTURE" onClick={() => { actionId.current = dispatch("tcpdump", { interface: iface, filter, output: "/tmp/capture.pcap" }); }} />
              <Btn label="TSHARK CAPTURE"  onClick={() => { actionId.current = dispatch("tshark",  { interface: iface, filter, count: "500" }); }} />
            </div>
          </div>
        </>
      )}
    </OffensiveTab>
  );
}

// ─── Payload Tab ──────────────────────────────────────────────────────────────

function PayloadTab() {
  const [payload, setPayload] = useState("windows/meterpreter/reverse_tcp");
  const [lhost,   setLhost]   = useState("");
  const [lport,   setLport]   = useState("4444");
  const [fmt,     setFmt]     = useState("exe");
  const [output,  setOutput]  = useState("/tmp/payload.exe");
  const actionId = { current: "" };
  const PAYLOADS = [
    "windows/meterpreter/reverse_tcp", "windows/meterpreter/reverse_https",
    "windows/x64/meterpreter/reverse_tcp", "linux/x64/meterpreter/reverse_tcp",
    "python/meterpreter/reverse_tcp", "php/meterpreter/reverse_tcp",
    "windows/shell/reverse_tcp",
  ];
  const FORMATS = ["exe","elf","raw","dll","ps1","py","rb","sh","asp","aspx","war","jar"];

  return (
    <OffensiveTab title="PAYLOAD GENERATION — MSFVENOM" icon="💣" actionId={actionId}>
      {dispatch => (
        <>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 6 }}>PAYLOAD</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
              {PAYLOADS.map(p => (
                <button key={p} onClick={() => { setPayload(p); setOutput(`/tmp/payload.${fmt}`); }} style={{
                  padding: "3px 8px", fontSize: 8,
                  background: payload === p ? "rgba(0,212,255,0.1)" : "transparent",
                  border: `1px solid ${payload === p ? "rgba(0,212,255,0.4)" : "rgba(0,212,255,0.1)"}`,
                  color: payload === p ? "#00d4ff" : "rgba(0,212,255,0.4)",
                  cursor: "pointer", fontFamily: "monospace", borderRadius: 2,
                }}>{p}</button>
              ))}
            </div>
            <input value={payload} onChange={e => setPayload(e.target.value)}
              style={{
                width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
                borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
                fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: "#00d4ff",
              }}
              onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
              onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
            />
          </div>
          <ParamRow label="LHOST (your IP / VM IP)" value={lhost}  onChange={setLhost} placeholder="192.168.56.1" />
          <ParamRow label="LPORT"                   value={lport}  onChange={setLport} placeholder="4444" />
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 6 }}>FORMAT</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {FORMATS.map(f => (
                <button key={f} onClick={() => { setFmt(f); setOutput(`/tmp/payload.${f}`); }} style={{
                  padding: "3px 8px", fontSize: 8,
                  background: fmt === f ? "rgba(0,212,255,0.1)" : "transparent",
                  border: `1px solid ${fmt === f ? "rgba(0,212,255,0.4)" : "rgba(0,212,255,0.1)"}`,
                  color: fmt === f ? "#00d4ff" : "rgba(0,212,255,0.4)",
                  cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
                }}>{f}</button>
              ))}
            </div>
          </div>
          <ParamRow label="OUTPUT PATH ON VM" value={output} onChange={setOutput} placeholder="/tmp/payload.exe" />
          <Btn label="GENERATE PAYLOAD" onClick={() => { actionId.current = dispatch("msfvenom", { payload, lhost, lport, format: fmt, output }); }} />
        </>
      )}
    </OffensiveTab>
  );
}

// ─── Web Tab ──────────────────────────────────────────────────────────────────

function WebAppTab() {
  const [target,   setTarget]   = useState("");
  const [wordlist, setWordlist] = useState("/usr/share/seclists/Discovery/Web-Content/common.txt");
  const [extra,    setExtra]    = useState("--batch --level=2 --risk=2");
  const actionId = { current: "" };

  return (
    <OffensiveTab title="WEB APPLICATION" icon="🌐" actionId={actionId}>
      {dispatch => (
        <>
          <ParamRow label="TARGET URL" value={target} onChange={setTarget} placeholder="https://target.com" />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <Btn label="NIKTO SCAN"  onClick={() => { actionId.current = dispatch("nikto",  { target }); }} />
            <Btn label="WHATWEB"     onClick={() => { actionId.current = dispatch("whatweb", { target }); }} />
            <Btn label="WAF DETECT"  onClick={() => { actionId.current = dispatch("wafw00f", { url: target }); }} />
            <Btn label="WPSCAN"      onClick={() => { actionId.current = dispatch("wpscan",  { url: target }); }} />
          </div>
          <ParamRow label="WORDLIST" value={wordlist} onChange={setWordlist} />
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <Btn label="FFUF FUZZ"    onClick={() => { actionId.current = dispatch("ffuf",      { url: target, wordlist }); }} />
            <Btn label="GOBUSTER DIR" onClick={() => { actionId.current = dispatch("gobuster",  { url: target, wordlist }); }} />
            <Btn label="NUCLEI SCAN"  onClick={() => { actionId.current = dispatch("nuclei",    { target, tags: "cve,rce,sqli" }); }} />
          </div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>SQLMAP EXTRA FLAGS</div>
            <input value={extra} onChange={e => setExtra(e.target.value)} style={{
              width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)",
              borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)",
              fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: "#00d4ff",
            }}
            onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
            onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
            />
          </div>
          <Btn label="SQLMAP INJECTION TEST" onClick={() => { actionId.current = dispatch("sqlmap", { url: target, extra }); }} danger />
        </>
      )}
    </OffensiveTab>
  );
}

// ─── OSINT Tab ────────────────────────────────────────────────────────────────

function OsintTab() {
  const [username, setUsername] = useState("");
  const [email,    setEmail]    = useState("");
  const [phone,    setPhone]    = useState("");
  const [domain,   setDomain]   = useState("");
  const [file,     setFile]     = useState("");
  const actionId = { current: "" };

  return (
    <OffensiveTab title="OSINT & LOCATION TRACKING" icon="🔍" actionId={actionId}>
      {dispatch => (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>USERNAME</div>
              <ParamRow label="USERNAME" value={username} onChange={setUsername} placeholder="john_doe" />
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <Btn label="SHERLOCK (300+ sites)"    onClick={() => { actionId.current = dispatch("sherlock",     { username }); }} />
                <Btn label="MAIGRET (3000+ sites)"    onClick={() => { actionId.current = dispatch("maigret",      { username }); }} />
                <Btn label="OSRFRAMEWORK"              onClick={() => { actionId.current = dispatch("osrframework", { username }); }} />
              </div>
            </div>
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>EMAIL</div>
              <ParamRow label="EMAIL ADDRESS" value={email} onChange={setEmail} placeholder="target@example.com" />
              <Btn label="HOLEHE (account check)" onClick={() => { actionId.current = dispatch("holehe", { email }); }} />
            </div>
          </div>

          <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>PHONE</div>
              <ParamRow label="PHONE NUMBER (+intl)" value={phone} onChange={setPhone} placeholder="+14155552671" />
              <Btn label="PHONEINFOGA" onClick={() => { actionId.current = dispatch("phoneinfoga", { number: phone }); }} />
            </div>
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>DOMAIN</div>
              <ParamRow label="DOMAIN" value={domain} onChange={setDomain} placeholder="example.com" />
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <Btn label="THEHARVESTER" onClick={() => { actionId.current = dispatch("theharvester", { domain }); }} />
                <Btn label="AMASS"        onClick={() => { actionId.current = dispatch("amass",         { domain }); }} />
              </div>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>FILE METADATA / GPS</div>
            <ParamRow label="FILE PATH (on VM)" value={file} onChange={setFile} placeholder="/tmp/photo.jpg" />
            <Btn label="EXIFTOOL — EXTRACT METADATA + GPS" onClick={() => { actionId.current = dispatch("exiftool", { file }); }} />
          </div>
        </>
      )}
    </OffensiveTab>
  );
}

// ─── Recon Tab ────────────────────────────────────────────────────────────────

function ReconTab() {
  const [target,  setTarget]  = useState("");
  const [domain,  setDomain]  = useState("");
  const [ports,   setPorts]   = useState("1-65535");
  const [rate,    setRate]    = useState("1000");
  const actionId = { current: "" };

  // Injection detection (Windows-native Rust)
  const [pid,       setPid]       = useState("");
  const [injection, setInjection] = useState<InjectionResult | null>(null);
  const [arp,       setArp]       = useState<ArpEntry[]>([]);

  return (
    <OffensiveTab title="RECONNAISSANCE" icon="🛰" actionId={actionId}>
      {dispatch => (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>HOST / IP</div>
              <ParamRow label="TARGET" value={target} onChange={setTarget} placeholder="192.168.1.0/24" />
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <Btn label="NMAP -sV -sC"  onClick={() => { actionId.current = dispatch("nmap",    { target, flags: "-sV -sC -T4" }); }} />
                <Btn label="NMAP VULN"     onClick={() => { actionId.current = dispatch("nmap",    { target, flags: "--script vuln" }); }} />
                <Btn label="NMAP OS DET"   onClick={() => { actionId.current = dispatch("nmap",    { target, flags: "-O -T4" }); }} />
                <Btn label="WHATWEB"       onClick={() => { actionId.current = dispatch("whatweb", { target }); }} />
              </div>
            </div>
            <div>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 10 }}>DOMAIN</div>
              <ParamRow label="DOMAIN" value={domain} onChange={setDomain} placeholder="example.com" />
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <Btn label="SUBFINDER"   onClick={() => { actionId.current = dispatch("subfinder",    { domain }); }} />
                <Btn label="AMASS"       onClick={() => { actionId.current = dispatch("amass",         { domain }); }} />
                <Btn label="DNSRECON"    onClick={() => { actionId.current = dispatch("dnsrecon",      { domain }); }} />
              </div>
            </div>
          </div>

          {/* Masscan */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>MASSCAN — FAST PORT SCAN</div>
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 2 }}><ParamRow label="TARGET RANGE" value={target} onChange={setTarget} placeholder="192.168.1.0/24" /></div>
              <div style={{ flex: 1 }}><ParamRow label="PORTS" value={ports} onChange={setPorts} placeholder="1-65535" /></div>
              <div style={{ flex: 1 }}><ParamRow label="RATE (pps)" value={rate} onChange={setRate} placeholder="1000" /></div>
            </div>
            <Btn label="RUN MASSCAN" onClick={() => { actionId.current = dispatch("masscan", { target, ports, rate }); }} />
          </div>

          {/* Windows-native */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>WINDOWS NATIVE — NO VM REQUIRED</div>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 8 }}>
              <div style={{ flex: 1 }}><ParamRow label="PROCESS ID (PID)" value={pid} onChange={setPid} placeholder="1234" /></div>
              <div style={{ paddingBottom: 10 }}>
                <Btn label="DETECT INJECTION" onClick={async () => {
                  if (!pid) return;
                  try { setInjection(await detectProcessInjection(parseInt(pid))); } catch { /* ignore */ }
                }} />
              </div>
            </div>
            {injection && (
              <div style={{
                background: "rgba(0,212,255,0.02)", border: `1px solid ${injection.verdict === "clean" ? "rgba(0,255,136,0.15)" : "rgba(255,68,0,0.2)"}`,
                borderRadius: 3, padding: "10px 14px", marginBottom: 8, fontSize: 10,
              }}>
                <div style={{ color: injection.verdict === "clean" ? "#00ff88" : "#ff4400", fontWeight: 600, marginBottom: 4 }}>
                  PID {injection.pid} ({injection.process_name}) — {injection.verdict.toUpperCase()}
                </div>
                {injection.suspicious_dlls.map((d, i) => <div key={i} style={{ color: "#ff6600" }}>⚠ {d}</div>)}
                {injection.details.map((d, i) => <div key={i} style={{ color: "rgba(0,212,255,0.6)" }}>{d}</div>)}
              </div>
            )}
            <Btn label="GET ARP TABLE" onClick={async () => {
              try { setArp(await getArpTable()); } catch { /* ignore */ }
            }} />
            {arp.length > 0 && (
              <div style={{
                marginTop: 8, background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
                borderRadius: 3, padding: "8px 12px", fontSize: 10, fontFamily: "monospace",
              }}>
                {arp.map((e, i) => (
                  <div key={i} style={{ color: "rgba(0,212,255,0.7)", marginBottom: 2 }}>
                    <span style={{ color: "#a0f4ff", minWidth: 130, display: "inline-block" }}>{e.ip}</span>
                    <span style={{ color: "#00d4ff",  minWidth: 140, display: "inline-block" }}>{e.mac}</span>
                    <span style={{ color: "rgba(0,212,255,0.4)", minWidth: 80, display: "inline-block" }}>{e.entry_type}</span>
                    <span style={{ color: "rgba(0,212,255,0.3)" }}>{e.interface}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </OffensiveTab>
  );
}

import { useDevices, type DeviceConfirmRequest } from "../../hooks/useBridge";
import { detectUsbDevices, type UsbDevice } from "../../lib/tauri";
import { LabTab }        from "./LabTab";
import { OpsTab }        from "./OpsTab";
import { IntelTab }      from "./IntelTab";
import { AutonomousTab } from "./AutonomousTab";
import { StealthTab }    from "./StealthTab";
import { SqliTab }       from "./SqliTab";

// ─── Phase 9 shared ───────────────────────────────────────────────────────────

function DeviceConfirmModal({ req, onConfirm }: { req: DeviceConfirmRequest; onConfirm: (c: boolean) => void }) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.82)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "#000a15", border: "1px solid rgba(0,212,255,0.25)",
        borderRadius: 6, padding: "28px 32px", maxWidth: 520, width: "90%",
      }}>
        <div style={{ fontSize: 8, letterSpacing: 5, color: "rgba(0,212,255,0.4)", marginBottom: 14 }}>
          DEVICE ACTION · CONFIRMATION REQUIRED
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{
            padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
            border: `1px solid ${RISK_COLOR[req.risk]}`, color: RISK_COLOR[req.risk],
          }}>{req.risk}</div>
          <span style={{ color: "#a0f4ff", fontSize: 12, fontWeight: 600 }}>{req.action}</span>
        </div>
        <div style={{
          fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.7)",
          background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.08)",
          borderRadius: 3, padding: "8px 12px", marginBottom: 14, wordBreak: "break-all",
        }}>{req.command}</div>
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.55)", marginBottom: 22, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
          {req.description}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn label="CANCEL"  onClick={() => onConfirm(false)} danger />
          <Btn label="CONFIRM" onClick={() => onConfirm(true)} />
        </div>
      </div>
    </div>
  );
}

function DeviceStream({ lines, onClear }: { lines: { chunk: string; ts: number }[]; onClear: () => void }) {
  if (lines.length === 0) return null;
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.35)" }}>OUTPUT</span>
        <button onClick={onClear} style={{
          fontSize: 7, padding: "2px 8px", background: "transparent",
          border: "1px solid rgba(0,212,255,0.15)", color: "rgba(0,212,255,0.4)",
          cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
        }}>CLEAR</button>
      </div>
      <div style={{
        background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
        borderRadius: 3, padding: "10px 12px", maxHeight: 320, overflowY: "auto",
        fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.75)", lineHeight: 1.6,
      }}>
        {lines.map((l, i) => (
          <div key={i} style={{ color: l.chunk.startsWith("[ERROR]") || l.chunk.startsWith("[EXIT:") ? "#ff4400" : l.chunk.startsWith("[HIT]") || l.chunk.includes("ACCESS GRANTED") ? "#00ff88" : undefined }}>
            {l.chunk}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Router Tab ───────────────────────────────────────────────────────────────

function RouterTab() {
  const dev = useDevices();
  const [target,   setTarget]   = useState("");
  const [user,     setUser]     = useState("admin");
  const [wordlist, setWordlist] = useState("/usr/share/wordlists/rockyou.txt");
  const [community,setCommunity]= useState("public");
  const [bssid,    setBssid]    = useState("");
  const [iface,    setIface]    = useState("wlan0");
  const [activeId, setActiveId] = useState("");

  const go = (action: string, params: Record<string, unknown> = {}) => {
    const id = dev.dispatch(action, { target, ...params });
    setActiveId(id);
  };

  const myLines = dev.streamLines.filter(l => l.id === activeId);

  return (
    <div>
      {dev.confirmReq && <DeviceConfirmModal req={dev.confirmReq} onConfirm={c => dev.confirm(dev.confirmReq!.id, c)} />}
      <SectionHeader title="ROUTER & NETWORK INFRASTRUCTURE" icon="🛡" />
      {dev.error && (
        <div style={{ background: "rgba(255,68,0,0.06)", border: "1px solid rgba(255,68,0,0.2)", borderRadius: 3, padding: "8px 12px", marginBottom: 12, fontSize: 10, color: "#ff4400", display: "flex", justifyContent: "space-between" }}>
          <span>{dev.error}</span>
          <button onClick={dev.clearError} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}

      <ParamRow label="TARGET IP / HOSTNAME" value={target} onChange={setTarget} placeholder="192.168.1.1" />

      {/* Quick actions */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>QUICK ACTIONS</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Btn label="FINGERPRINT"    onClick={() => go("router_fingerprint")} />
          <Btn label="FULL AUDIT"     onClick={() => go("router_audit")} />
          <Btn label="AUTOPWN"        onClick={() => go("router_autopwn")} />
          <Btn label="DEFAULT CREDS"  onClick={() => go("router_default_creds")} />
          <Btn label="CONFIG DUMP"    onClick={() => go("router_config_dump")} />
          <Btn label="UPNP ENUM"      onClick={() => go("router_upnp")} />
        </div>
      </div>

      {/* Brute force */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>BRUTE FORCE</div>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ flex: 1 }}><ParamRow label="USERNAME" value={user} onChange={setUser} placeholder="admin" /></div>
          <div style={{ flex: 2 }}><ParamRow label="WORDLIST (VM)" value={wordlist} onChange={setWordlist} /></div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn label="BRUTE SSH"    onClick={() => go("router_brute_ssh",    { user, wordlist })} />
          <Btn label="BRUTE TELNET" onClick={() => go("router_brute_telnet", { user, wordlist })} />
          <Btn label="BRUTE HTTP"   onClick={() => go("router_brute_http",   { user, wordlist })} />
        </div>
      </div>

      {/* SNMP */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>SNMP</div>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}><ParamRow label="COMMUNITY STRING" value={community} onChange={setCommunity} placeholder="public" /></div>
          <div style={{ paddingBottom: 10, display: "flex", gap: 6 }}>
            <Btn label="SNMP WALK"  onClick={() => go("router_snmp_enum",  { community })} />
            <Btn label="SNMP BRUTE" onClick={() => go("router_snmp_brute", {})} />
          </div>
        </div>
      </div>

      {/* WPS */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>WPS ATTACK</div>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}><ParamRow label="BSSID" value={bssid} onChange={setBssid} placeholder="AA:BB:CC:DD:EE:FF" /></div>
          <div style={{ flex: 1 }}><ParamRow label="INTERFACE" value={iface} onChange={setIface} placeholder="wlan0" /></div>
          <div style={{ paddingBottom: 10 }}>
            <Btn label="REAVER WPS" onClick={() => go("router_wps", { bssid, interface: iface })} danger />
          </div>
        </div>
      </div>

      <DeviceStream lines={myLines} onClear={() => dev.clearStream(activeId)} />
    </div>
  );
}

// ─── Mobile Tab ───────────────────────────────────────────────────────────────

function MobileTab() {
  const dev = useDevices();
  const [selectedSerial, setSelectedSerial] = useState("");
  const [usbDevices,    setUsbDevices]    = useState<UsbDevice[]>([]);
  const [deviceIp,      setDeviceIp]      = useState("");
  const [package_,      setPackage]       = useState("");
  const [apkPath,       setApkPath]       = useState("");
  const [lhost,         setLhost]         = useState("");
  const [lport,         setLport]         = useState("4444");
  const [shellCmd,      setShellCmd]      = useState("");
  const [activeId,      setActiveId]      = useState("");
  const [activeSection, setActiveSection] = useState<"usb"|"network"|"apk"|"ios">("usb");

  const go = (action: string, params: Record<string, unknown> = {}) => {
    const id = dev.dispatch(action, { serial: selectedSerial, device_ip: deviceIp, ...params });
    setActiveId(id);
  };

  const myLines = dev.streamLines.filter(l => l.id === activeId);

  // Sync ADB devices from bridge
  // ADB devices come from dev.adbDevices directly

  const sections: { id: typeof activeSection; label: string }[] = [
    { id: "usb",     label: "USB / ADB"  },
    { id: "network", label: "NETWORK ADB"},
    { id: "apk",     label: "APK ANALYSIS"},
    { id: "ios",     label: "iOS"        },
  ];

  return (
    <div>
      {dev.confirmReq && <DeviceConfirmModal req={dev.confirmReq} onConfirm={c => dev.confirm(dev.confirmReq!.id, c)} />}
      <SectionHeader title="MOBILE DEVICES — ANDROID & iOS" icon="📱" />
      {dev.error && (
        <div style={{ background: "rgba(255,68,0,0.06)", border: "1px solid rgba(255,68,0,0.2)", borderRadius: 3, padding: "8px 12px", marginBottom: 12, fontSize: 10, color: "#ff4400", display: "flex", justifyContent: "space-between" }}>
          <span>{dev.error}</span>
          <button onClick={dev.clearError} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* Sub-section tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, borderBottom: "1px solid rgba(0,212,255,0.08)" }}>
        {sections.map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)} style={{
            padding: "5px 12px", fontSize: 8, letterSpacing: 2, background: "transparent",
            border: "none", borderBottom: `2px solid ${activeSection === s.id ? "#00d4ff" : "transparent"}`,
            color: activeSection === s.id ? "#00d4ff" : "rgba(0,212,255,0.35)",
            cursor: "pointer", fontFamily: "inherit",
          }}>{s.label}</button>
        ))}
      </div>

      {/* USB / ADB section */}
      {activeSection === "usb" && (
        <div>
          {/* USB device detection */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <Btn label="SCAN USB DEVICES" onClick={async () => {
                try { setUsbDevices(await detectUsbDevices()); } catch { /* ignore */ }
              }} />
              <Btn label="LIST ADB DEVICES" onClick={() => { dev.listAdb(); }} />
            </div>
            {usbDevices.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                {usbDevices.map((d, i) => (
                  <div key={i} style={{
                    display: "flex", gap: 10, padding: "6px 10px", marginBottom: 3,
                    background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)", borderRadius: 3,
                  }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 3, flexShrink: 0,
                      background: d.device_type === "android" ? "#00ff88" : d.device_type.includes("ducky") || d.device_type === "omg_cable" ? "#ff6600" : "#00d4ff",
                    }} />
                    <span style={{ color: "#a0f4ff", fontSize: 10, minWidth: 100 }}>{d.device_type.replace("_", " ").toUpperCase()}</span>
                    <span style={{ color: "rgba(0,212,255,0.7)", fontSize: 10, flex: 1 }}>{d.description}</span>
                    <span style={{ color: "rgba(0,212,255,0.4)", fontSize: 9 }}>{d.vendor_id}:{d.product_id}</span>
                    {d.drive_letter && <span style={{ color: "#ffb300", fontSize: 9 }}>{d.drive_letter}</span>}
                  </div>
                ))}
              </div>
            )}
            {dev.adbDevices.length > 0 && (
              <div>
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 6 }}>SELECT DEVICE</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {dev.adbDevices.map(d => (
                    <button key={d.serial} onClick={() => setSelectedSerial(d.serial)} style={{
                      padding: "4px 10px", fontSize: 9, background: selectedSerial === d.serial ? "rgba(0,212,255,0.1)" : "transparent",
                      border: `1px solid ${selectedSerial === d.serial ? "#00d4ff" : "rgba(0,212,255,0.15)"}`,
                      color: selectedSerial === d.serial ? "#00d4ff" : "rgba(0,212,255,0.5)",
                      cursor: "pointer", fontFamily: "monospace", borderRadius: 2,
                    }}>{d.serial} ({d.state})</button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Actions on selected device */}
          {selectedSerial && (
            <>
              <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>
                DEVICE: <span style={{ color: "#00d4ff" }}>{selectedSerial}</span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                <Btn label="FINGERPRINT"     onClick={() => go("adb_fingerprint")} />
                <Btn label="LIST APPS"       onClick={() => go("adb_list_packages")} />
                <Btn label="SCREENSHOT"      onClick={() => go("adb_screenshot")} />
                <Btn label="LOCATION"        onClick={() => { const id = dev.dispatch("adb_shell", { serial: selectedSerial, command: "dumpsys location | grep 'Last Known'" }); setActiveId(id); }} />
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                <Btn label="DUMP SMS"          onClick={() => go("adb_sms_dump")} danger />
                <Btn label="DUMP CONTACTS"     onClick={() => go("adb_contacts_dump")} danger />
                <Btn label="DUMP CALL LOG"     onClick={() => go("adb_call_log")} danger />
                <Btn label="CLIPBOARD"         onClick={() => go("adb_clipboard")} danger />
                <Btn label="WIFI PASSWORDS"    onClick={() => go("adb_wifi_passwords")} danger />
                <Btn label="ENABLE TCP ADB"    onClick={() => go("adb_enable_tcp")} />
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>SHELL COMMAND</div>
                  <input value={shellCmd} onChange={e => setShellCmd(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") { const id = dev.dispatch("adb_shell", { serial: selectedSerial, command: shellCmd }); setActiveId(id); }}}
                    placeholder="any shell command..."
                    style={{ width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "monospace", outline: "none", caretColor: "#00d4ff" }}
                    onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
                    onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
                  />
                </div>
                <div style={{ paddingTop: 18 }}>
                  <Btn label="RUN" onClick={() => { const id = dev.dispatch("adb_shell", { serial: selectedSerial, command: shellCmd }); setActiveId(id); }} />
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Network ADB section */}
      {activeSection === "network" && (
        <div>
          <ParamRow label="DEVICE IP" value={deviceIp} onChange={setDeviceIp} placeholder="192.168.1.50" />
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            <Btn label="CONNECT ADB (5555)" onClick={() => go("adb_connect_network", { ip: deviceIp, port: 5555 })} />
            <Btn label="FRIDA LIST APPS"    onClick={() => go("frida_list_apps", { device_ip: deviceIp })} />
          </div>
          <ParamRow label="PACKAGE NAME" value={package_} onChange={setPackage} placeholder="com.example.app" />
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            <Btn label="SSL PINNING BYPASS" onClick={() => go("frida_ssl_bypass", { device_ip: deviceIp, package: package_ })} danger />
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>PAYLOAD DELIVERY</div>
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}><ParamRow label="LHOST (listener IP)" value={lhost} onChange={setLhost} placeholder="192.168.1.100" /></div>
              <div style={{ flex: 1 }}><ParamRow label="LPORT" value={lport} onChange={setLport} placeholder="4444" /></div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn label="GEN ANDROID PAYLOAD" onClick={() => go("android_payload", { lhost, lport })} danger />
              <Btn label="START LISTENER"      onClick={() => go("android_listener",{ lhost, lport })} danger />
            </div>
          </div>
        </div>
      )}

      {/* APK Analysis section */}
      {activeSection === "apk" && (
        <div>
          <ParamRow label="APK PATH (on VM)" value={apkPath} onChange={setApkPath} placeholder="/tmp/app.apk" />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
            <Btn label="DECOMPILE (apktool)" onClick={() => go("apk_decompile",    { apk_path: apkPath })} />
            <Btn label="FIND SECRETS"        onClick={() => go("apk_find_secrets", { apk_path: apkPath })} />
            <Btn label="PERMISSIONS"         onClick={() => go("apk_permissions",  { apk_path: apkPath })} />
          </div>
          {selectedSerial && (
            <>
              <ParamRow label="PACKAGE (to extract APK from device)" value={package_} onChange={setPackage} placeholder="com.example.app" />
              <Btn label="PULL APK FROM DEVICE" onClick={() => go("adb_pull_apk", { serial: selectedSerial, package: package_ })} />
            </>
          )}
        </div>
      )}

      {/* iOS section */}
      {activeSection === "ios" && (
        <div>
          <div style={{ background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, padding: "10px 14px", marginBottom: 14, fontSize: 9, color: "rgba(0,212,255,0.45)", lineHeight: 1.7 }}>
            <div style={{ color: "#00d4ff", marginBottom: 4, fontSize: 8, letterSpacing: 2 }}>iOS REQUIREMENTS</div>
            USB backup: requires <code style={{ color: "#a0f4ff" }}>libimobiledevice</code> on VM + trust prompt on device.<br />
            SSH access: device must be jailbroken (Checkra1n, Palera1n, etc.).<br />
            IPA dump: requires <code style={{ color: "#a0f4ff" }}>frida-ios-dump</code> on VM.
          </div>
          <ParamRow label="DEVICE IP (jailbroken)" value={deviceIp} onChange={setDeviceIp} placeholder="192.168.1.50" />
          <ParamRow label="SUBNET (for discovery)"  value={deviceIp} onChange={setDeviceIp} placeholder="192.168.1.0/24" />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
            <Btn label="DISCOVER iOS DEVICES"   onClick={() => go("ios_discover", { subnet: deviceIp })} />
            <Btn label="EXTRACT BACKUP (USB)"   onClick={() => go("ios_backup")} danger />
            <Btn label="SSH (jailbroken)"        onClick={() => go("ios_ssh",     { device_ip: deviceIp })} danger />
          </div>
          <ParamRow label="BUNDLE ID (for IPA dump)" value={package_} onChange={setPackage} placeholder="com.example.app" />
          <Btn label="DUMP DECRYPTED IPA (jailbroken)" onClick={() => go("ios_dump_ipa", { device_ip: deviceIp, bundle_id: package_ })} danger />
        </div>
      )}

      <DeviceStream lines={myLines} onClear={() => dev.clearStream(activeId)} />
    </div>
  );
}

// ─── IoT Tab ──────────────────────────────────────────────────────────────────

function IotTab() {
  const dev = useDevices();
  const [target,   setTarget]   = useState("");
  const [broker,   setBroker]   = useState("");
  const [topic,    setTopic]    = useState("#");
  const [payload,  setPayload]  = useState("ON");
  const [firmware, setFirmware] = useState("");
  const [query,    setQuery]    = useState("");
  const [activeId, setActiveId] = useState("");

  const go = (action: string, params: Record<string, unknown> = {}) => {
    const id = dev.dispatch(action, params);
    setActiveId(id);
  };

  const myLines = dev.streamLines.filter(l => l.id === activeId);

  return (
    <div>
      {dev.confirmReq && <DeviceConfirmModal req={dev.confirmReq} onConfirm={c => dev.confirm(dev.confirmReq!.id, c)} />}
      <SectionHeader title="IoT & SMART HOME DEVICES" icon="🏠" />
      {dev.error && (
        <div style={{ background: "rgba(255,68,0,0.06)", border: "1px solid rgba(255,68,0,0.2)", borderRadius: 3, padding: "8px 12px", marginBottom: 12, fontSize: 10, color: "#ff4400", display: "flex", justifyContent: "space-between" }}>
          <span>{dev.error}</span>
          <button onClick={dev.clearError} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* Discovery */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>DISCOVERY</div>
        <ParamRow label="TARGET IP / SUBNET" value={target} onChange={setTarget} placeholder="192.168.1.0/24 or 192.168.1.100" />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <Btn label="SCAN NETWORK"      onClick={() => go("iot_scan",          { target })} />
          <Btn label="FULL AUDIT"        onClick={() => go("iot_audit",         { target })} />
          <Btn label="DEFAULT CREDS"     onClick={() => go("iot_default_creds", { target })} />
          <Btn label="CAMERA SCAN"       onClick={() => go("iot_camera_scan",   { target })} />
          <Btn label="CAMERA BRUTE"      onClick={() => go("iot_camera_brute",  { target })} danger />
          <Btn label="UPNP ENUM"         onClick={() => go("iot_upnp",          { target })} />
        </div>
      </div>

      {/* Shodan */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>SHODAN IoT SEARCH</div>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ flex: 1 }}><ParamRow label="QUERY" value={query} onChange={setQuery} placeholder="hikvision camera country:PK" /></div>
          <div style={{ paddingTop: 18 }}><Btn label="SEARCH" onClick={() => go("iot_shodan", { query })} /></div>
        </div>
      </div>

      {/* MQTT */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>MQTT BROKER</div>
        <ParamRow label="BROKER IP" value={broker} onChange={setBroker} placeholder="192.168.1.100" />
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 8 }}>
          <div style={{ flex: 2 }}><ParamRow label="TOPIC" value={topic} onChange={setTopic} placeholder="#" /></div>
          <div style={{ flex: 2 }}><ParamRow label="PAYLOAD" value={payload} onChange={setPayload} placeholder="ON" /></div>
          <div style={{ paddingBottom: 10, display: "flex", gap: 6 }}>
            <Btn label="SUBSCRIBE"  onClick={() => go("iot_mqtt_discover", { broker })} />
            <Btn label="PUBLISH"    onClick={() => go("iot_mqtt_publish",  { broker, topic, payload })} danger />
          </div>
        </div>
      </div>

      {/* Firmware */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 8, letterSpacing: 4, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>FIRMWARE ANALYSIS</div>
        <ParamRow label="FIRMWARE PATH (on VM)" value={firmware} onChange={setFirmware} placeholder="/tmp/firmware.bin" />
        <div style={{ display: "flex", gap: 8 }}>
          <Btn label="EXTRACT (binwalk)"  onClick={() => go("iot_firmware_extract",  { firmware_path: firmware })} />
          <Btn label="FIND SECRETS"        onClick={() => go("iot_firmware_secrets", { firmware_path: firmware })} />
          <Btn label="STRINGS"             onClick={() => go("iot_firmware_strings", { firmware_path: firmware })} />
        </div>
      </div>

      <DeviceStream lines={myLines} onClear={() => dev.clearStream(activeId)} />
    </div>
  );
}

const TABS: { id: Tab; label: string }[] = [
  { id: "scanner",    label: "NMAP"        },
  { id: "iprep",      label: "IP REP"      },
  { id: "ipintel",    label: "IP INTEL"    },
  { id: "fullscan",   label: "PORT SCAN"   },
  { id: "emailosint", label: "EMAIL OSINT" },
  { id: "cve",        label: "CVE SEARCH"  },
  { id: "ports",      label: "PORTS"       },
  { id: "processes",  label: "AUDIT"       },
  { id: "dns",        label: "DNS LEAK"    },
  { id: "vpn",        label: "VPN"         },
  { id: "firewall",   label: "FIREWALL"    },
  { id: "password",   label: "PASSWORD"    },
  { id: "url",        label: "URL SCAN"    },
  { id: "log",        label: "EVENT LOG"   },
  { id: "localaccess",label: "LOCAL ACCESS"},
  // ── Phase 8 — Offensive ──────────────────────────
  { id: "vm",         label: "VM"          },
  { id: "recon",      label: "RECON"       },
  { id: "crack",      label: "CRACK"       },
  { id: "exploit",    label: "EXPLOIT"     },
  { id: "wifi",       label: "WIFI"        },
  { id: "mitm",       label: "MITM"        },
  { id: "payload",    label: "PAYLOAD"     },
  { id: "web",        label: "WEB APP"     },
  { id: "osint",      label: "OSINT"       },
  // ── Phase 9 — Device Exploitation ───────────────────────
  { id: "router",     label: "ROUTER"      },
  { id: "mobile",     label: "MOBILE"      },
  { id: "iot",        label: "IoT"         },
  // ── Phase 10 — Red Team Lab ──────────────────────────────
  { id: "lab",        label: "🔴 LAB"      },
  { id: "ops",        label: "🌐 OPS"      },
  { id: "intel",      label: "🧠 INTEL"    },
  { id: "auto",       label: "⚡ AUTO"     },
  { id: "stealth",    label: "👻 STEALTH"  },
  { id: "sqli",       label: "💉 SQLi"     },
];

export function SecurityPanel() {
  const [tab, setTab] = useState<Tab>("scanner");
  const localAccess   = useLocalAccess();

  // Expose to LocalAccessTab via window (avoids prop-drilling through all tabs)
  (window as any).__useLocalAccess = () => localAccess;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Tab bar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 2, padding: "12px 16px 0", borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0 }}>
        {TABS.map(({ id, label }) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "6px 10px", fontSize: 7, letterSpacing: 3,
            background: tab === id ? "rgba(0,212,255,0.08)" : "transparent",
            border: "none", borderBottom: `2px solid ${tab === id ? "#00d4ff" : "transparent"}`,
            color: tab === id ? "#00d4ff" : "rgba(0,212,255,0.35)",
            cursor: "pointer", fontFamily: "inherit", transition: "all 0.2s",
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {tab === "scanner"    && <ScannerTab />}
        {tab === "iprep"      && <IpRepTab />}
        {tab === "ipintel"    && <IpIntelTab />}
        {tab === "fullscan"   && <FullPortScanTab />}
        {tab === "emailosint" && <EmailOsintTab />}
        {tab === "cve"        && <CveTab />}
        {tab === "ports"      && <PortsTab />}
        {tab === "processes"  && <ProcessAuditTab />}
        {tab === "dns"        && <DnsTab />}
        {tab === "vpn"        && <VpnTab />}
        {tab === "firewall"   && <FirewallTab />}
        {tab === "password"   && <PasswordTab />}
        {tab === "url"        && <UrlTab />}
        {tab === "log"        && <LogTab />}
        {tab === "localaccess"&& <LocalAccessTab />}
        {tab === "vm"         && <VmTab />}
        {tab === "recon"      && <ReconTab />}
        {tab === "crack"      && <CrackTab />}
        {tab === "exploit"    && <ExploitTab />}
        {tab === "wifi"       && <WifiTab />}
        {tab === "mitm"       && <MitmTab />}
        {tab === "payload"    && <PayloadTab />}
        {tab === "web"        && <WebAppTab />}
        {tab === "osint"      && <OsintTab />}
        {tab === "router"     && <RouterTab />}
        {tab === "mobile"     && <MobileTab />}
        {tab === "iot"        && <IotTab />}
        {tab === "lab"        && <LabTab />}
        {tab === "ops"        && <OpsTab />}
        {tab === "intel"      && <IntelTab />}
        {tab === "auto"       && <AutonomousTab />}
        {tab === "stealth"    && <StealthTab />}
        {tab === "sqli"       && <SqliTab />}
      </div>
    </div>
  );
}

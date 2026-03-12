import { useState } from "react";
import {
  nmapScan, checkIpReputationV2, getOpenPorts, analyzeProcesses,
  checkDnsLeak, getVpnStatus, getFirewallRules, checkPasswordStrength,
  checkUrlSafety, getSecurityLog, ipIntel, emailOsint, cveSearch, fullPortScan,
} from "../../lib/tauri";
import type { FirewallRule, PasswordStrength, SecurityEvent, IpIntelResult, EmailOsintResult, CveEntry, FullScanResult } from "../../lib/tauri";
import { useTStore } from "../../store";
import { useLocalAccess, type LocalAccessProgress } from "../../hooks/useBridge";

// ─── Shared ───────────────────────────────────────────────────────────────────

type Tab = "scanner" | "iprep" | "ports" | "processes" | "dns" | "vpn" | "firewall" | "password" | "url" | "log" | "ipintel" | "emailosint" | "cve" | "fullscan" | "localaccess";

function SectionHeader({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 8, borderBottom: "1px solid rgba(255,179,0,0.08)" }}>
      <span style={{ fontSize: 14, color: "#ffb300", textShadow: "0 0 8px #ffb300" }}>{icon}</span>
      <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(255,179,0,0.6)" }}>{title}</span>
    </div>
  );
}

function Btn({ label, onClick, disabled = false, danger = false }: {
  label: string; onClick: () => void; disabled?: boolean; danger?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 16px", fontSize: 8, letterSpacing: 2,
      background: danger ? "rgba(255,68,0,0.07)" : "rgba(255,179,0,0.07)",
      border: `1px solid ${danger ? "rgba(255,68,0,0.3)" : "rgba(255,179,0,0.25)"}`,
      color: danger ? "#ff4400" : "#ffb300",
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
      <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>{label}</div>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        style={{ width: "100%", background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(255,230,102,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
        onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
      />
    </div>
  );
}

function StatusBadge({ value, labels }: { value: string; labels: Record<string, string> }) {
  const colors: Record<string, string> = {
    clean: "#00ff88", safe: "#00ff88", low: "#00ff88",
    suspicious: "#ffb300", unknown: "#ffb300", medium: "#ffb300",
    malicious: "#ff4400", critical: "#ff4400", high: "#ff4400",
  };
  const color = colors[value.toLowerCase()] ?? "rgba(255,179,0,0.5)";
  return (
    <span style={{ fontSize: 8, letterSpacing: 2, padding: "2px 8px", border: `1px solid ${color}`, color, borderRadius: 2, textShadow: `0 0 6px ${color}` }}>
      {labels[value] ?? value.toUpperCase()}
    </span>
  );
}

function ResultBox({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3, padding: "14px 16px", marginTop: 14 }}>
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
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.5)", marginBottom: 10 }}>HOST: {result.host}{result.os_guess && ` · OS: ${result.os_guess}`}</div>
          {result.ports.length === 0
            ? <div style={{ fontSize: 10, color: "rgba(255,179,0,0.4)" }}>No open ports found.</div>
            : <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead>
                  <tr style={{ color: "rgba(255,179,0,0.4)", fontSize: 8, letterSpacing: 2 }}>
                    {["PORT", "STATE", "SERVICE", "VERSION"].map((h) => (
                      <td key={h} style={{ padding: "4px 8px", borderBottom: "1px solid rgba(255,179,0,0.08)" }}>{h}</td>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.ports.map((p) => (
                    <tr key={p.port} style={{ borderBottom: "1px solid rgba(255,179,0,0.04)" }}>
                      <td style={{ padding: "5px 8px", color: "#ffe566" }}>{p.port}</td>
                      <td style={{ padding: "5px 8px", color: "#00ff88" }}>{p.state}</td>
                      <td style={{ padding: "5px 8px", color: "rgba(255,179,0,0.8)" }}>{p.service}</td>
                      <td style={{ padding: "5px 8px", color: "rgba(255,179,0,0.5)", fontSize: 9 }}>{p.version}</td>
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

  const repColors: Record<string, string> = { clean: "#00ff88", suspicious: "#ffb300", malicious: "#ff4400", unknown: "rgba(255,179,0,0.4)" };

  return (
    <div>
      <SectionHeader title="IP REPUTATION" icon="◎" />
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12, lineHeight: 1.6 }}>
        Powered by AbuseIPDB. Add your key in Settings → Profile → ABUSEIPDB API KEY.
      </div>
      <Field label="IP ADDRESS" value={ip} onChange={setIp} placeholder="8.8.8.8" />
      <Btn label={loading ? "CHECKING···" : "CHECK REPUTATION"} onClick={check} disabled={loading || !ip.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result && (
        <ResultBox>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: repColors[result.reputation] ?? "#ffb300", textShadow: `0 0 8px ${repColors[result.reputation] ?? "#ffb300"}` }}>
              {result.reputation.toUpperCase()}
            </span>
            <span style={{ fontSize: 9, color: "rgba(255,179,0,0.5)" }}>{result.ip}</span>
          </div>
          <div style={{ fontSize: 10, color: "rgba(255,179,0,0.7)" }}>{result.detail}</div>
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
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>Checks 17 common ports via TCP connect. No nmap required.</div>
      <Field label="HOST" value={host} onChange={setHost} placeholder="192.168.1.1 or domain.com" />
      <Btn label={loading ? "SCANNING···" : "SCAN PORTS"} onClick={scan} disabled={loading || !host.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {result !== null && (
        <ResultBox>
          {result.length === 0
            ? <div style={{ fontSize: 10, color: "#00ff88" }}>All common ports closed or filtered.</div>
            : result.map((p) => (
              <div key={p.port} style={{ display: "flex", gap: 12, padding: "5px 0", borderBottom: "1px solid rgba(255,179,0,0.05)" }}>
                <span style={{ color: "#ffe566", minWidth: 50, fontSize: 11 }}>{p.port}</span>
                <span style={{ color: "#ff4400", fontSize: 10 }}>OPEN</span>
                <span style={{ color: "rgba(255,179,0,0.7)", fontSize: 10 }}>{p.service}</span>
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
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
        Detects known malicious tools and anomalous CPU usage patterns.
      </div>
      <Btn label={loading ? "SCANNING···" : "AUDIT PROCESSES"} onClick={run} disabled={loading} />
      {result !== null && (
        <ResultBox>
          {result.length === 0
            ? <div style={{ fontSize: 10, color: "#00ff88" }}>✓ No suspicious processes detected.</div>
            : result.map((p) => (
              <div key={p.pid} style={{ padding: "8px 0", borderBottom: "1px solid rgba(255,179,0,0.06)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <StatusBadge value={p.suspicion} labels={{ critical: "CRITICAL", suspicious: "SUSPICIOUS" }} />
                  <span style={{ color: "#ffe566", fontSize: 11 }}>{p.name}</span>
                  <span style={{ color: "rgba(255,179,0,0.4)", fontSize: 9 }}>PID {p.pid}</span>
                </div>
                <div style={{ fontSize: 9, color: "rgba(255,179,0,0.6)" }}>{p.reason}</div>
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
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
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
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 8 }}>DNS SERVERS</div>
          {result.servers.map((s) => (
            <div key={s} style={{ fontSize: 10, color: "rgba(255,179,0,0.8)", padding: "3px 0" }}>{s}</div>
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
              <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.4)", minWidth: 80 }}>{label}</span>
              <span style={{ fontSize: 10, color: "rgba(255,179,0,0.85)" }}>{value}</span>
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
            style={{ flex: 1, background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
          />
        )}
      </div>
      {error && <div style={{ fontSize: 9, color: "#ff4400" }}>{error}</div>}
      {rules && (
        <div style={{ maxHeight: 360, overflowY: "auto", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px 60px", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(255,179,0,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)" }}>
            <span>NAME</span><span>DIRECTION</span><span>ACTION</span><span>STATUS</span>
          </div>
          {filtered.map((r, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px 60px", gap: 8, padding: "5px 12px", borderBottom: "1px solid rgba(255,179,0,0.04)", fontSize: 10, alignItems: "center" }}>
              <span style={{ color: "rgba(255,179,0,0.85)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.name}</span>
              <span style={{ color: "rgba(255,179,0,0.5)", fontSize: 9 }}>{r.direction}</span>
              <span style={{ color: r.action.toLowerCase().includes("allow") ? "#00ff88" : "#ff4400", fontSize: 9 }}>{r.action}</span>
              <span style={{ color: r.enabled ? "#00ff88" : "rgba(255,179,0,0.3)", fontSize: 8 }}>{r.enabled ? "ON" : "OFF"}</span>
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

  const scoreColors = ["#ff4400", "#ff6600", "#ffb300", "#ffe566", "#00ff88"];
  const color = result ? scoreColors[result.score] ?? "#ffb300" : "#ffb300";

  return (
    <div>
      <SectionHeader title="PASSWORD STRENGTH ANALYSER" icon="◎" />
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>Password is checked locally — never sent anywhere.</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>PASSWORD</div>
          <input type={show ? "text" : "password"} value={password}
            onChange={(e) => { setPassword(e.target.value); setResult(null); }}
            onKeyDown={(e) => e.key === "Enter" && check()}
            placeholder="Enter password to analyse..."
            style={{ width: "100%", background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(255,230,102,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ height: 16 }} />
          <button onClick={() => setShow(!show)} style={{ padding: "6px 10px", fontSize: 9, background: "transparent", border: "1px solid rgba(255,179,0,0.15)", color: "rgba(255,179,0,0.5)", cursor: "pointer", borderRadius: 3, fontFamily: "inherit" }}>
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
              <span style={{ fontSize: 10, color: "rgba(255,179,0,0.5)" }}>Entropy: {result.entropy.toFixed(1)} bits</span>
            </div>
            <div style={{ height: 4, background: "rgba(255,179,0,0.08)", borderRadius: 2 }}>
              <div style={{ height: "100%", width: `${(result.score / 4) * 100}%`, background: color, borderRadius: 2, boxShadow: `0 0 8px ${color}`, transition: "width 0.5s ease" }} />
            </div>
          </div>
          {result.feedback.length > 0 && (
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 8 }}>RECOMMENDATIONS</div>
              {result.feedback.map((f, i) => (
                <div key={i} style={{ display: "flex", gap: 8, fontSize: 10, color: "rgba(255,179,0,0.75)", marginBottom: 5 }}>
                  <span style={{ color: "#ffb300" }}>›</span>{f}
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
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
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
          <div style={{ fontSize: 10, color: "rgba(255,179,0,0.7)" }}>{result.detail}</div>
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
    error: "#ff4400", warning: "#ffb300", info: "rgba(255,179,0,0.5)",
    Error: "#ff4400", Warning: "#ffb300", Information: "rgba(255,179,0,0.5)",
  };

  return (
    <div>
      <SectionHeader title="SECURITY EVENT LOG" icon="◎" />
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <Btn label={loading ? "LOADING···" : "LOAD EVENTS"} onClick={load} disabled={loading} />
        {events && (
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="filter events..."
            style={{ flex: 1, background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
          />
        )}
      </div>
      {error && <div style={{ fontSize: 9, color: "#ff4400" }}>{error}</div>}
      {events && (
        <div style={{ maxHeight: 380, overflowY: "auto", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3 }}>
          {filtered.length === 0
            ? <div style={{ padding: 14, fontSize: 10, color: "rgba(255,179,0,0.4)" }}>No events found.</div>
            : filtered.map((ev, i) => (
              <div key={i} style={{ padding: "8px 12px", borderBottom: "1px solid rgba(255,179,0,0.04)" }}>
                <div style={{ display: "flex", gap: 10, marginBottom: 3 }}>
                  <span style={{ fontSize: 8, color: levelColor[ev.level] ?? "rgba(255,179,0,0.5)", letterSpacing: 1 }}>{ev.level.toUpperCase()}</span>
                  <span style={{ fontSize: 8, color: "rgba(255,179,0,0.35)" }}>{ev.source}</span>
                  {ev.time && <span style={{ fontSize: 8, color: "rgba(255,179,0,0.25)", marginLeft: "auto" }}>{ev.time}</span>}
                </div>
                <div style={{ fontSize: 10, color: "rgba(255,179,0,0.7)", lineHeight: 1.5 }}>{ev.message}</div>
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

  const scoreColor = (s: number) => s > 75 ? "#ff4400" : s > 25 ? "#ffb300" : "#00ff88";

  return (
    <div>
      <SectionHeader title="IP INTELLIGENCE" icon="◉" />
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
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
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 2 }}>{k}</div>
                <div style={{ fontSize: 10, color: "rgba(255,230,102,0.85)", wordBreak: "break-all" }}>{v || "—"}</div>
              </div>
            ))}
          </div>

          <div style={{ borderTop: "1px solid rgba(255,179,0,0.08)", paddingTop: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 6 }}>ABUSE SCORE</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 22, fontWeight: "bold", color: scoreColor(result.abuse_score), textShadow: `0 0 12px ${scoreColor(result.abuse_score)}` }}>
                {result.abuse_score}%
              </span>
              <span style={{ fontSize: 9, color: "rgba(255,179,0,0.5)" }}>{result.abuse_detail}</span>
            </div>
          </div>

          <div style={{ borderTop: "1px solid rgba(255,179,0,0.08)", paddingTop: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 6 }}>
              OPEN PORTS ({result.open_ports.length})
            </div>
            {result.open_ports.length === 0
              ? <div style={{ fontSize: 9, color: "#00ff88" }}>No common ports open</div>
              : <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {result.open_ports.map((p) => (
                    <span key={p} style={{ fontSize: 9, padding: "2px 8px", border: "1px solid rgba(255,68,0,0.4)", color: "#ff6e00", borderRadius: 2 }}>
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
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
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
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>STATUS</div>
              <span style={{ fontSize: 10, color: result.valid ? "#00ff88" : "#ff4400" }}>
                {result.valid ? "VALID FORMAT" : "INVALID FORMAT"}
              </span>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>DOMAIN</div>
              <span style={{ fontSize: 10, color: "rgba(255,230,102,0.85)" }}>{result.domain || "—"}</span>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>GRAVATAR</div>
              <span style={{ fontSize: 10, color: result.gravatar_url ? "#00ff88" : "rgba(255,179,0,0.4)" }}>
                {result.gravatar_url ? "PROFILE EXISTS" : "NOT FOUND"}
              </span>
            </div>
          </div>

          {/* Gravatar image */}
          {result.gravatar_url && (
            <div style={{ marginBottom: 14 }}>
              <img src={result.gravatar_url} alt="gravatar" style={{ width: 60, height: 60, borderRadius: 4, border: "1px solid rgba(255,179,0,0.2)" }} />
            </div>
          )}

          {/* MX Records */}
          {result.mx_records.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 6 }}>MX RECORDS</div>
              {result.mx_records.map((mx, i) => (
                <div key={i} style={{ fontSize: 9, color: "rgba(255,179,0,0.65)", marginBottom: 2 }}>{mx}</div>
              ))}
            </div>
          )}

          {/* Breach summary */}
          <div style={{ borderTop: "1px solid rgba(255,179,0,0.08)", paddingTop: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: 18, fontWeight: "bold", color: result.breach_count > 0 ? "#ff4400" : "#00ff88", textShadow: result.breach_count > 0 ? "0 0 12px #ff4400" : "0 0 8px #00ff88" }}>
                {result.breach_count}
              </span>
              <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.5)" }}>
                {result.breach_count === 0 ? "NO BREACHES FOUND" : "BREACHES DETECTED"}
              </span>
            </div>
            {result.breaches.map((b) => (
              <div key={b.name} style={{ marginBottom: 10, padding: "8px 10px", background: "rgba(255,68,0,0.04)", border: "1px solid rgba(255,68,0,0.15)", borderRadius: 3 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 10, color: "#ff6e00", fontWeight: "bold" }}>{b.name}</span>
                  <span style={{ fontSize: 8, color: "rgba(255,179,0,0.4)" }}>{b.breach_date}</span>
                </div>
                <div style={{ fontSize: 8, color: "rgba(255,179,0,0.5)", marginBottom: 4 }}>{b.domain}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {b.data_classes.map((dc) => (
                    <span key={dc} style={{ fontSize: 7, padding: "1px 6px", border: "1px solid rgba(255,68,0,0.25)", color: "#ff4400", borderRadius: 2 }}>{dc}</span>
                  ))}
                </div>
                <div style={{ fontSize: 8, color: "rgba(255,179,0,0.35)", marginTop: 4 }}>
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
      case "MEDIUM":   return "#ffb300";
      case "LOW":      return "#ffe566";
      default:         return "rgba(255,179,0,0.4)";
    }
  };

  return (
    <div>
      <SectionHeader title="CVE SEARCH" icon="⚠" />
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
        Search NIST National Vulnerability Database. Enter service name, software, or CVE ID.
      </div>
      <Field label="SEARCH QUERY" value={query} onChange={setQuery} placeholder="apache 2.4 / openssl / CVE-2024-..." />
      <Btn label={loading ? "SEARCHING···" : "SEARCH NVD"} onClick={run} disabled={loading || !query.trim()} />
      {error && <div style={{ fontSize: 9, color: "#ff4400", marginTop: 10 }}>{error}</div>}
      {results.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(255,179,0,0.35)", marginBottom: 10 }}>
            {results.length} RESULTS
          </div>
          {results.map((cve) => (
            <div key={cve.id} style={{ marginBottom: 10, padding: "10px 14px", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,179,0,0.08)", borderLeft: `3px solid ${severityColor(cve.severity)}`, borderRadius: "0 3px 3px 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: "bold", color: "#ffe566", letterSpacing: 1 }}>{cve.id}</span>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: severityColor(cve.severity), fontWeight: "bold", textShadow: `0 0 8px ${severityColor(cve.severity)}` }}>
                    {cve.cvss_score.toFixed(1)}
                  </span>
                  <span style={{ fontSize: 7, padding: "1px 7px", border: `1px solid ${severityColor(cve.severity)}`, color: severityColor(cve.severity), borderRadius: 2, letterSpacing: 2 }}>
                    {cve.severity}
                  </span>
                </div>
              </div>
              <div style={{ fontSize: 9, color: "rgba(255,179,0,0.65)", lineHeight: 1.6, marginBottom: 6 }}>
                {cve.description.slice(0, 300)}{cve.description.length > 300 ? "..." : ""}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 7, color: "rgba(255,179,0,0.3)", letterSpacing: 2 }}>
                  {cve.published.slice(0, 10)}
                </span>
                {cve.references[0] && (
                  <a href={cve.references[0]} target="_blank" rel="noreferrer" style={{ fontSize: 7, color: "rgba(255,179,0,0.4)", letterSpacing: 2 }}>
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
      <div style={{ fontSize: 9, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>
        Parallel TCP connect scan · Max 10 000 ports · Only scan systems you own or have permission to test
      </div>

      <Field label="HOST / IP" value={host} onChange={setHost} placeholder="192.168.1.1 or example.com" />

      <div style={{ display: "flex", gap: 10, marginBottom: 12, alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>START PORT</div>
          <input
            value={startPort} onChange={(e) => setStartPort(e.target.value)}
            style={{ width: "100%", background: "rgba(255,179,0,0.04)", border: "1px solid rgba(255,179,0,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(255,230,102,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none" }}
          />
        </div>
        <div style={{ fontSize: 10, color: "rgba(255,179,0,0.3)", paddingBottom: 8 }}>–</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>END PORT</div>
          <input
            value={endPort} onChange={(e) => setEndPort(e.target.value)}
            style={{ width: "100%", background: "rgba(255,179,0,0.04)", border: "1px solid rgba(255,179,0,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(255,230,102,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none" }}
          />
        </div>
      </div>

      {/* Presets */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {presets.map((p) => (
          <button key={p.label} onClick={() => { setStartPort(p.s); setEndPort(p.e); }}
            style={{ fontSize: 7, letterSpacing: 2, padding: "3px 10px", background: "transparent", border: "1px solid rgba(255,179,0,0.2)", color: "rgba(255,179,0,0.5)", borderRadius: 2, cursor: "pointer", fontFamily: "inherit" }}>
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
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>HOST</div>
              <div style={{ fontSize: 10, color: "rgba(255,230,102,0.85)" }}>{result.host}</div>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>SCANNED</div>
              <div style={{ fontSize: 10, color: "rgba(255,230,102,0.85)" }}>{result.scanned.toLocaleString()} ports</div>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>OPEN</div>
              <div style={{ fontSize: 18, fontWeight: "bold", color: result.open.length > 0 ? "#ff6e00" : "#00ff88", textShadow: result.open.length > 0 ? "0 0 10px #ff6e00" : "0 0 8px #00ff88" }}>
                {result.open.length}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 3 }}>DURATION</div>
              <div style={{ fontSize: 10, color: "rgba(255,230,102,0.85)" }}>{(result.duration_ms / 1000).toFixed(1)}s</div>
            </div>
          </div>

          {result.open.length === 0
            ? <div style={{ fontSize: 9, color: "#00ff88" }}>No open ports found in range</div>
            : (
              <div>
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.35)", marginBottom: 8 }}>OPEN PORTS</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 6 }}>
                  {result.open.map((p) => (
                    <div key={p.port} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 10px", background: "rgba(255,110,0,0.05)", border: "1px solid rgba(255,110,0,0.2)", borderRadius: 3 }}>
                      <span style={{ fontSize: 11, fontWeight: "bold", color: "#ff6e00", minWidth: 36 }}>{p.port}</span>
                      <span style={{ fontSize: 8, color: "rgba(255,179,0,0.55)", letterSpacing: 1 }}>{p.service || "UNKNOWN"}</span>
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
    idle:             "rgba(255,179,0,0.4)",
    checking:         "#ffb300",
    awaiting_confirm: "#ffb300",
    elevating:        "#ff9900",
    running:          "#00ff88",
    done:             "#00ff88",
    error:            "#ff4400",
  };
  const statusColor = statusColors[state] ?? "rgba(255,179,0,0.4)";

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
          <div style={{ marginTop: 8, fontSize: 9, color: "rgba(255,179,0,0.35)", lineHeight: 1.6 }}>
            Extracts from: LSASS · SAM · Credential Manager · Browsers · WiFi · Env Vars · Scheduled Tasks · Registry
          </div>
        </div>
      )}

      {/* Confirmation prompt */}
      {state === "awaiting_confirm" && readyPayload && (
        <div style={{ background: "rgba(255,179,0,0.04)", border: "1px solid rgba(255,179,0,0.2)", borderRadius: 4, padding: "14px 16px", marginBottom: 16 }}>
          <div style={{ fontSize: 9, letterSpacing: 2, color: "#ffb300", marginBottom: 10 }}>CONFIRMATION REQUIRED</div>
          <pre style={{ fontSize: 9, color: "rgba(255,230,102,0.7)", lineHeight: 1.7, whiteSpace: "pre-wrap", margin: "0 0 14px" }}>
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
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 8 }}>PROGRESS</div>
          {progress.map((p: LocalAccessProgress) => (
            <div key={p.source} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <span style={{
                fontSize: 8, letterSpacing: 2, padding: "1px 6px",
                border: `1px solid ${p.status === "done" ? "#00ff88" : p.status === "failed" ? "#ff4400" : "#ffb300"}`,
                color:         p.status === "done" ? "#00ff88" : p.status === "failed" ? "#ff4400" : "#ffb300",
                borderRadius: 2, minWidth: 50, textAlign: "center",
              }}>
                {p.status.toUpperCase()}
              </span>
              <span style={{ fontSize: 10, color: "rgba(255,230,102,0.7)" }}>{p.source}</span>
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
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 6 }}>NTLM HASHES ({hashes.length})</div>
          <div style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3, padding: "10px 14px", fontFamily: "monospace", fontSize: 10 }}>
            {hashes.map((h: string, i: number) => (
              <div key={i} style={{ color: "rgba(255,230,102,0.8)", marginBottom: 2 }}>{h}</div>
            ))}
          </div>
        </div>
      )}

      {/* Full output */}
      {fullOutput && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 6 }}>FULL OUTPUT</div>
          <pre style={{
            background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,179,0,0.08)",
            borderRadius: 3, padding: "12px 14px", fontSize: 9, lineHeight: 1.7,
            color: "rgba(255,230,102,0.75)", overflowX: "auto", whiteSpace: "pre-wrap",
            maxHeight: 400, overflowY: "auto",
          }}>
            {fullOutput}
          </pre>
        </div>
      )}

      {/* Memory inspector */}
      {(state === "running" || state === "done") && (
        <div style={{ borderTop: "1px solid rgba(255,179,0,0.08)", paddingTop: 16 }}>
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
              background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,179,0,0.08)",
              borderRadius: 3, padding: "10px 14px", fontSize: 9, lineHeight: 1.7,
              color: "rgba(255,230,102,0.75)", whiteSpace: "pre-wrap",
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

const TABS: { id: Tab; label: string }[] = [
  { id: "scanner",   label: "NMAP"      },
  { id: "iprep",     label: "IP REP"    },
  { id: "ipintel",   label: "IP INTEL"  },
  { id: "fullscan",  label: "PORT SCAN" },
  { id: "emailosint",label: "EMAIL OSINT"},
  { id: "cve",       label: "CVE SEARCH"},
  { id: "ports",     label: "PORTS"     },
  { id: "processes", label: "AUDIT"     },
  { id: "dns",       label: "DNS LEAK"  },
  { id: "vpn",       label: "VPN"       },
  { id: "firewall",  label: "FIREWALL"  },
  { id: "password",  label: "PASSWORD"  },
  { id: "url",       label: "URL SCAN"  },
  { id: "log",       label: "EVENT LOG" },
  { id: "localaccess", label: "LOCAL ACCESS" },
];

export function SecurityPanel() {
  const [tab, setTab] = useState<Tab>("scanner");
  const localAccess   = useLocalAccess();

  // Expose to LocalAccessTab via window (avoids prop-drilling through all tabs)
  (window as any).__useLocalAccess = () => localAccess;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Tab bar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 2, padding: "12px 16px 0", borderBottom: "1px solid rgba(255,179,0,0.08)", flexShrink: 0 }}>
        {TABS.map(({ id, label }) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "6px 10px", fontSize: 7, letterSpacing: 3,
            background: tab === id ? "rgba(255,179,0,0.08)" : "transparent",
            border: "none", borderBottom: `2px solid ${tab === id ? "#ffb300" : "transparent"}`,
            color: tab === id ? "#ffb300" : "rgba(255,179,0,0.35)",
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
        {tab === "url"         && <UrlTab />}
        {tab === "log"         && <LogTab />}
        {tab === "localaccess" && <LocalAccessTab />}
      </div>
    </div>
  );
}

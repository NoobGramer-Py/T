import { useState, useEffect } from "react";
import {
  pingHost, traceroute, dnsLookup, whoisLookup, scanLocalNetwork,
  getActiveConnections, getNetworkInterfaces, checkSslCert, getHttpHeaders,
} from "../../lib/tauri";
import type {
  PingResult, HopInfo, DnsResult, DeviceInfo,
  Connection, NetworkInterface, SslCertInfo, HttpHeaderResult,
} from "../../lib/tauri";

const errMsg = (e: unknown, fallback: string): string =>
  (e as Error)?.message ?? fallback;

// ─── Shared UI ────────────────────────────────────────────────────────────────

type Tab = "ping" | "trace" | "dns" | "whois" | "lan" | "connections" | "interfaces" | "ssl" | "headers";

function SectionHeader({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 8, borderBottom: "1px solid rgba(0,212,255,0.08)" }}>
      <span style={{ fontSize: 14, color: "#00d4ff", textShadow: "0 0 8px #00d4ff" }}>{icon}</span>
      <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(0,212,255,0.6)" }}>{title}</span>
    </div>
  );
}

function InputRow({ value, onChange, onRun, placeholder, loading, btnLabel = "RUN" }: {
  value: string; onChange: (v: string) => void; onRun: () => void;
  placeholder: string; loading: boolean; btnLabel?: string;
}) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
      <input value={value} onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onRun()} placeholder={placeholder}
        style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
        onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
      />
      <button onClick={onRun} disabled={loading} style={{
        padding: "6px 16px", fontSize: 8, letterSpacing: 3,
        background: loading ? "transparent" : "rgba(0,212,255,0.08)",
        border: `1px solid ${loading ? "rgba(0,212,255,0.1)" : "rgba(0,212,255,0.3)"}`,
        color: loading ? "rgba(0,212,255,0.3)" : "#00d4ff",
        borderRadius: 3, cursor: loading ? "not-allowed" : "pointer", fontFamily: "inherit",
      }}>
        {loading ? "···" : btnLabel}
      </button>
    </div>
  );
}

function ResultBox({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, padding: "12px 14px", fontSize: 10, color: "rgba(0,212,255,0.75)", lineHeight: 1.7 }}>
      {children}
    </div>
  );
}

function ErrBox({ msg }: { msg: string }) {
  return (
    <div style={{ fontSize: 9, color: "#ff4400", marginTop: 8, padding: "6px 10px", background: "rgba(255,68,0,0.05)", border: "1px solid rgba(255,68,0,0.15)", borderRadius: 3 }}>
      {msg}
    </div>
  );
}

// ─── Ping Tab ─────────────────────────────────────────────────────────────────

function PingTab() {
  const [host, setHost]       = useState("");
  const [count, setCount]     = useState("4");
  const [result, setResult]   = useState<PingResult | null>(null);
  const [history, setHistory] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!host.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const r = await pingHost(host.trim(), parseInt(count) || 4);
      setResult(r);
      setHistory((h) => [...h.slice(-9), r.avg_ms]);
    } catch (err) {
      setError(errMsg(err, "Ping failed"));
    } finally {
      setLoading(false);
    }
  };

  const latColor = (ms: number) =>
    ms === 0 ? "rgba(0,212,255,0.3)" : ms < 50 ? "#00ff88" : ms < 150 ? "#00d4ff" : "#ff4400";
  const maxH = Math.max(...history, 1);

  return (
    <div>
      <SectionHeader title="PING" icon="◎" />
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input value={host} onChange={(e) => setHost(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()} placeholder="host or IP"
          style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
        />
        <select value={count} onChange={(e) => setCount(e.target.value)}
          style={{ background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 8px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", cursor: "pointer" }}>
          {["4", "8", "16", "32"].map((n) => (
            <option key={n} value={n} style={{ background: "#000" }}>{n} packets</option>
          ))}
        </select>
        <button onClick={run} disabled={loading || !host.trim()} style={{
          padding: "6px 16px", fontSize: 8, letterSpacing: 3,
          background: loading ? "transparent" : "rgba(0,212,255,0.08)",
          border: `1px solid ${loading ? "rgba(0,212,255,0.1)" : "rgba(0,212,255,0.3)"}`,
          color: loading ? "rgba(0,212,255,0.3)" : "#00d4ff",
          borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        }}>
          {loading ? "···" : "PING"}
        </button>
      </div>

      {error && <ErrBox msg={error} />}

      {result && (
        <ResultBox>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 16 }}>
            {([
              { label: "AVG",  val: `${result.avg_ms.toFixed(1)} ms`, color: latColor(result.avg_ms) },
              { label: "MIN",  val: `${result.min_ms.toFixed(1)} ms`, color: "#00ff88" },
              { label: "MAX",  val: `${result.max_ms.toFixed(1)} ms`, color: latColor(result.max_ms) },
              { label: "LOSS", val: `${result.packet_loss}%`,          color: result.packet_loss > 0 ? "#ff4400" : "#00ff88" },
            ] as const).map(({ label, val, color }) => (
              <div key={label} style={{ textAlign: "center", padding: "8px", background: "rgba(0,212,255,0.02)", borderRadius: 3 }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 14, color, textShadow: `0 0 8px ${color}` }}>{val}</div>
              </div>
            ))}
          </div>

          {history.length > 1 && (
            <div>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 8 }}>LATENCY HISTORY</div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 40 }}>
                {history.map((ms, i) => (
                  <div key={i} title={`${ms.toFixed(1)} ms`} style={{
                    flex: 1, background: latColor(ms),
                    height: `${Math.max((ms / maxH) * 100, 4)}%`,
                    borderRadius: 2, opacity: 0.8,
                    boxShadow: `0 0 4px ${latColor(ms)}`,
                    transition: "height 0.3s ease",
                  }} />
                ))}
              </div>
            </div>
          )}
        </ResultBox>
      )}
    </div>
  );
}

// ─── Traceroute Tab ───────────────────────────────────────────────────────────

function TraceTab() {
  const [host, setHost]       = useState("");
  const [hops, setHops]       = useState<HopInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!host.trim()) return;
    setLoading(true); setHops([]); setError("");
    try {
      setHops(await traceroute(host.trim()));
    } catch (err) {
      setError(errMsg(err, "Traceroute failed"));
    } finally {
      setLoading(false);
    }
  };

  const maxMs = Math.max(...hops.filter((h) => !h.timeout).map((h) => h.ms), 1);

  return (
    <div>
      <SectionHeader title="TRACEROUTE" icon="⬡" />
      <InputRow value={host} onChange={setHost} onRun={run} placeholder="host or IP" loading={loading} btnLabel="TRACE" />
      {error && <ErrBox msg={error} />}
      {loading && (
        <div style={{ fontSize: 9, color: "rgba(0,212,255,0.4)", margin: "12px 0" }}>
          Tracing route — this may take 30–60 seconds...
        </div>
      )}
      {hops.length > 0 && (
        <div style={{ border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "32px 1fr 120px 60px", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(0,212,255,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)" }}>
            <span>#</span><span>HOST</span><span>LATENCY BAR</span><span style={{ textAlign: "right" }}>MS</span>
          </div>
          {hops.map((h) => (
            <div key={h.hop} style={{ display: "grid", gridTemplateColumns: "32px 1fr 120px 60px", gap: 8, padding: "5px 12px", borderBottom: "1px solid rgba(0,212,255,0.04)", fontSize: 10, color: "rgba(0,212,255,0.75)", alignItems: "center" }}>
              <span style={{ color: "rgba(0,212,255,0.35)", fontSize: 9 }}>{h.hop}</span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: h.timeout ? "rgba(0,212,255,0.25)" : "inherit" }}>
                {h.timeout ? "* * *" : h.host}
              </span>
              <div style={{ height: 4, background: "rgba(0,212,255,0.08)", borderRadius: 2 }}>
                {!h.timeout && (
                  <div style={{ height: "100%", width: `${(h.ms / maxMs) * 100}%`, background: h.ms > 150 ? "#ff4400" : h.ms > 50 ? "#00d4ff" : "#00ff88", borderRadius: 2, transition: "width 0.5s ease" }} />
                )}
              </div>
              <span style={{ textAlign: "right", color: h.timeout ? "rgba(0,212,255,0.25)" : h.ms > 150 ? "#ff4400" : "#00d4ff" }}>
                {h.timeout ? "—" : `${h.ms.toFixed(1)}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── DNS Tab ──────────────────────────────────────────────────────────────────

function DnsTab() {
  const [domain, setDomain]   = useState("");
  const [result, setResult]   = useState<DnsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!domain.trim()) return;
    setLoading(true); setResult(null); setError("");
    try {
      setResult(await dnsLookup(domain.trim()));
    } catch (err) {
      setError(errMsg(err, "DNS lookup failed"));
    } finally {
      setLoading(false);
    }
  };

  const RecordRow = ({ label, values }: { label: string; values: string[] }) =>
    values.length > 0 ? (
      <div style={{ marginBottom: 8, padding: "6px 10px", background: "rgba(0,212,255,0.02)", borderRadius: 3 }}>
        <span style={{ display: "inline-block", width: 52, fontSize: 8, letterSpacing: 2, color: "rgba(0,212,255,0.4)", verticalAlign: "top", marginRight: 8 }}>{label}</span>
        <span style={{ color: "rgba(160,244,255,0.85)", fontSize: 10, wordBreak: "break-all" }}>
          {values.map((v, i) => <span key={i} style={{ display: "block" }}>{v}</span>)}
        </span>
      </div>
    ) : null;

  return (
    <div>
      <SectionHeader title="DNS LOOKUP" icon="⊹" />
      <InputRow value={domain} onChange={setDomain} onRun={run} placeholder="domain.com" loading={loading} btnLabel="LOOKUP" />
      {error && <ErrBox msg={error} />}
      {result && (
        <div>
          <RecordRow label="A"     values={result.a} />
          <RecordRow label="AAAA"  values={result.aaaa} />
          <RecordRow label="MX"    values={result.mx} />
          <RecordRow label="NS"    values={result.ns} />
          <RecordRow label="TXT"   values={result.txt} />
          <RecordRow label="CNAME" values={result.cname} />
          {Object.values(result).every((v) => v.length === 0) && (
            <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", fontStyle: "italic" }}>
              No records found for {domain}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Whois Tab ────────────────────────────────────────────────────────────────

function WhoisTab() {
  const [domain, setDomain]   = useState("");
  const [result, setResult]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!domain.trim()) return;
    setLoading(true); setResult(""); setError("");
    try {
      setResult(await whoisLookup(domain.trim()));
    } catch (err) {
      setError(errMsg(err, "WHOIS failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <SectionHeader title="WHOIS" icon="⊞" />
      <InputRow value={domain} onChange={setDomain} onRun={run} placeholder="domain.com or IP" loading={loading} btnLabel="WHOIS" />
      {error && <ErrBox msg={error} />}
      {result && (
        <pre style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, padding: "10px 14px", maxHeight: 340, overflowY: "auto", color: "rgba(160,244,255,0.75)", fontSize: 9, lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {result}
        </pre>
      )}
    </div>
  );
}

// ─── LAN Scan Tab ─────────────────────────────────────────────────────────────

function LanTab() {
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    setLoading(true); setDevices([]); setError("");
    try {
      setDevices(await scanLocalNetwork());
    } catch (err) {
      setError(errMsg(err, "Scan failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <SectionHeader title="LOCAL NETWORK SCAN" icon="◎" />
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <button onClick={run} disabled={loading} style={{
          padding: "6px 18px", fontSize: 8, letterSpacing: 3,
          background: "rgba(0,212,255,0.07)", border: "1px solid rgba(0,212,255,0.25)",
          color: "#00d4ff", borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
          opacity: loading ? 0.5 : 1,
        }}>
          {loading ? "SCANNING···" : "SCAN LOCAL NETWORK"}
        </button>
        <span style={{ fontSize: 9, color: "rgba(0,212,255,0.3)" }}>Requires nmap installed</span>
      </div>
      {loading && (
        <div style={{ fontSize: 9, color: "rgba(0,212,255,0.4)", marginBottom: 10 }}>
          Auto-detecting subnet and scanning — may take 15–30 seconds...
        </div>
      )}
      {error && <ErrBox msg={error} />}
      {devices.length > 0 && (
        <>
          <div style={{ fontSize: 9, color: "rgba(0,212,255,0.4)", marginBottom: 8 }}>
            {devices.length} device{devices.length !== 1 ? "s" : ""} found
          </div>
          <div style={{ border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "110px 155px 1fr 1fr", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(0,212,255,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)" }}>
              <span>IP</span><span>MAC</span><span>HOSTNAME</span><span>VENDOR</span>
            </div>
            {devices.map((d) => (
              <div key={d.ip} style={{ display: "grid", gridTemplateColumns: "110px 155px 1fr 1fr", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(0,212,255,0.04)", fontSize: 10, color: "rgba(0,212,255,0.75)", alignItems: "center" }}>
                <span style={{ color: "#a0f4ff" }}>{d.ip}</span>
                <span style={{ color: "rgba(0,212,255,0.45)", fontSize: 9 }}>{d.mac || "—"}</span>
                <span>{d.hostname || "—"}</span>
                <span style={{ color: "rgba(0,212,255,0.45)", fontSize: 9 }}>{d.vendor || "—"}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Active Connections Tab ───────────────────────────────────────────────────

function ConnectionsTab() {
  const [conns, setConns]     = useState<Connection[]>([]);
  const [filter, setFilter]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    setLoading(true); setConns([]); setError("");
    try {
      setConns(await getActiveConnections());
    } catch (err) {
      setError(errMsg(err, "Failed to fetch connections"));
    } finally {
      setLoading(false);
    }
  };

  const filtered = filter
    ? conns.filter((c) =>
        c.local_addr.includes(filter) ||
        c.remote_addr.includes(filter) ||
        c.state.toLowerCase().includes(filter.toLowerCase()) ||
        c.protocol.toLowerCase().includes(filter.toLowerCase())
      )
    : conns;

  const stateColor = (s: string) => {
    if (s.includes("LISTEN"))      return "#00ff88";
    if (s.includes("ESTABLISHED")) return "#00d4ff";
    if (s.includes("WAIT"))        return "#0088cc";
    if (s.includes("CLOSE"))       return "#ff4400";
    return "rgba(0,212,255,0.6)";
  };

  return (
    <div>
      <SectionHeader title="ACTIVE CONNECTIONS" icon="⬡" />
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={run} disabled={loading} style={{
          padding: "6px 16px", fontSize: 8, letterSpacing: 3,
          background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.3)",
          color: "#00d4ff", borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        }}>
          {loading ? "···" : "REFRESH"}
        </button>
        {conns.length > 0 && (
          <input value={filter} onChange={(e) => setFilter(e.target.value)}
            placeholder="filter by IP, port, state..."
            style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "5px 10px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
          />
        )}
      </div>
      {error && <ErrBox msg={error} />}
      {filtered.length > 0 && (
        <div style={{ border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, overflow: "hidden", maxHeight: 360, overflowY: "auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "55px 1fr 1fr 100px 50px", gap: 6, padding: "5px 12px", borderBottom: "1px solid rgba(0,212,255,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", position: "sticky", top: 0, background: "#000a15" }}>
            <span>PROTO</span><span>LOCAL</span><span>REMOTE</span><span>STATE</span><span>PID</span>
          </div>
          {filtered.slice(0, 100).map((c, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "55px 1fr 1fr 100px 50px", gap: 6, padding: "4px 12px", borderBottom: "1px solid rgba(0,212,255,0.03)", fontSize: 9, alignItems: "center" }}>
              <span style={{ color: "rgba(0,212,255,0.5)" }}>{c.protocol}</span>
              <span style={{ color: "rgba(160,244,255,0.8)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.local_addr}</span>
              <span style={{ color: "rgba(0,212,255,0.6)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.remote_addr}</span>
              <span style={{ color: stateColor(c.state), fontSize: 8 }}>{c.state}</span>
              <span style={{ color: "rgba(0,212,255,0.35)", fontSize: 8 }}>{c.pid || "—"}</span>
            </div>
          ))}
          {filtered.length > 100 && (
            <div style={{ padding: "6px 12px", fontSize: 8, color: "rgba(0,212,255,0.35)" }}>
              Showing 100 of {filtered.length} — use filter to narrow
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Network Interfaces Tab ───────────────────────────────────────────────────

function InterfacesTab() {
  const [ifaces, setIfaces]   = useState<NetworkInterface[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      setIfaces(await getNetworkInterfaces());
    } catch (err) {
      setError(errMsg(err, "Failed to fetch interfaces"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <SectionHeader title="NETWORK INTERFACES" icon="⊹" />
      <div style={{ marginBottom: 12 }}>
        <button onClick={load} disabled={loading} style={{
          padding: "5px 14px", fontSize: 8, letterSpacing: 3,
          background: "rgba(0,212,255,0.07)", border: "1px solid rgba(0,212,255,0.25)",
          color: "#00d4ff", borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        }}>
          {loading ? "···" : "REFRESH"}
        </button>
      </div>
      {error && <ErrBox msg={error} />}
      {ifaces.map((iface) => (
        <div key={iface.name} style={{ marginBottom: 10, padding: "12px 14px", background: "rgba(0,212,255,0.02)", border: `1px solid ${iface.status === "Up" ? "rgba(0,212,255,0.12)" : "rgba(0,212,255,0.05)"}`, borderRadius: 3 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: "#a0f4ff" }}>{iface.name}</span>
            <span style={{ fontSize: 8, padding: "2px 8px", borderRadius: 10, background: iface.status === "Up" ? "rgba(0,255,136,0.08)" : "rgba(255,68,0,0.08)", border: `1px solid ${iface.status === "Up" ? "rgba(0,255,136,0.3)" : "rgba(255,68,0,0.3)"}`, color: iface.status === "Up" ? "#00ff88" : "#ff4400" }}>
              {iface.status}
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8, fontSize: 9 }}>
            {([
              { label: "IPv4",  val: iface.ip_v4 },
              { label: "IPv6",  val: iface.ip_v6 },
              { label: "MAC",   val: iface.mac },
              { label: "SPEED", val: iface.speed_mbps },
            ] as const).map(({ label, val }) => (
              <div key={label}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.35)", marginBottom: 2 }}>{label}</div>
                <div style={{ color: "rgba(160,244,255,0.8)" }}>{val}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── SSL Certificate Tab ──────────────────────────────────────────────────────

function SslTab() {
  const [host, setHost]       = useState("");
  const [result, setResult]   = useState<SslCertInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!host.trim()) return;
    const clean = host.trim().replace(/^https?:\/\//, "").split("/")[0];
    setLoading(true); setResult(null); setError("");
    try {
      setResult(await checkSslCert(clean));
    } catch (err) {
      setError(errMsg(err, "SSL check failed"));
    } finally {
      setLoading(false);
    }
  };

  const daysColor = (d: number) => d > 60 ? "#00ff88" : d > 14 ? "#00d4ff" : "#ff4400";

  return (
    <div>
      <SectionHeader title="SSL CERTIFICATE" icon="◎" />
      <InputRow value={host} onChange={setHost} onRun={run} placeholder="example.com" loading={loading} btnLabel="CHECK" />
      {error && <ErrBox msg={error} />}
      {result && (
        <ResultBox>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <span style={{ fontSize: 20, color: result.valid ? "#00ff88" : "#ff4400", textShadow: `0 0 12px ${result.valid ? "#00ff88" : "#ff4400"}` }}>
              {result.valid ? "✓" : "✗"}
            </span>
            <div>
              <div style={{ fontSize: 11, color: result.valid ? "#00ff88" : "#ff4400" }}>
                {result.valid ? "VALID CERTIFICATE" : "INVALID / EXPIRED"}
              </div>
              <div style={{ fontSize: 9, color: daysColor(result.days_left), marginTop: 2 }}>
                {result.days_left > 0 ? `${result.days_left} days remaining` : "Expired"}
              </div>
            </div>
          </div>
          {([
            { label: "SUBJECT",    val: result.subject },
            { label: "ISSUER",     val: result.issuer },
            { label: "VALID FROM", val: result.not_before },
            { label: "EXPIRES",    val: result.not_after },
          ] as const).map(({ label, val }) => val ? (
            <div key={label} style={{ marginBottom: 6 }}>
              <span style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginRight: 8 }}>{label}</span>
              <span style={{ fontSize: 10, color: "rgba(160,244,255,0.85)", wordBreak: "break-all" }}>{val}</span>
            </div>
          ) : null)}
          {result.san.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 6 }}>SAN DOMAINS</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {result.san.map((s) => (
                  <span key={s} style={{ padding: "2px 8px", background: "rgba(0,212,255,0.06)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 10, fontSize: 9, color: "rgba(160,244,255,0.75)" }}>{s}</span>
                ))}
              </div>
            </div>
          )}
        </ResultBox>
      )}
    </div>
  );
}

// ─── HTTP Headers Tab ─────────────────────────────────────────────────────────

const SECURITY_HEADERS = [
  "strict-transport-security", "content-security-policy",
  "x-frame-options", "x-content-type-options",
  "referrer-policy", "permissions-policy",
];

function HeadersTab() {
  const [url, setUrl]         = useState("");
  const [result, setResult]   = useState<HttpHeaderResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!url.trim()) return;
    const clean = url.trim().startsWith("http") ? url.trim() : `https://${url.trim()}`;
    setLoading(true); setResult(null); setError("");
    try {
      setResult(await getHttpHeaders(clean));
    } catch (err) {
      setError(errMsg(err, "Request failed"));
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (s: number) => s < 300 ? "#00ff88" : s < 400 ? "#00d4ff" : "#ff4400";

  return (
    <div>
      <SectionHeader title="HTTP HEADERS" icon="⊞" />
      <InputRow value={url} onChange={setUrl} onRun={run} placeholder="https://example.com" loading={loading} btnLabel="FETCH" />
      {error && <ErrBox msg={error} />}
      {result && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14, padding: "8px 12px", background: "rgba(0,212,255,0.02)", borderRadius: 3 }}>
            <span style={{ fontSize: 18, color: statusColor(result.status), textShadow: `0 0 8px ${statusColor(result.status)}` }}>
              {result.status}
            </span>
            <span style={{ fontSize: 10, color: "rgba(160,244,255,0.7)" }}>{result.status_text}</span>
          </div>

          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.4)", marginBottom: 8 }}>SECURITY HEADER AUDIT</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {SECURITY_HEADERS.map((h) => {
                const present = result.headers.some(([k]) => k.toLowerCase() === h);
                return (
                  <span key={h} style={{ padding: "2px 8px", fontSize: 8, borderRadius: 10, background: present ? "rgba(0,255,136,0.06)" : "rgba(255,68,0,0.06)", border: `1px solid ${present ? "rgba(0,255,136,0.2)" : "rgba(255,68,0,0.15)"}`, color: present ? "#00ff88" : "rgba(255,68,0,0.6)" }}>
                    {present ? "✓" : "✗"} {h}
                  </span>
                );
              })}
            </div>
          </div>

          <div style={{ border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3, overflow: "hidden", maxHeight: 280, overflowY: "auto" }}>
            {result.headers.map(([k, v], i) => {
              const isSec = SECURITY_HEADERS.includes(k.toLowerCase());
              return (
                <div key={i} style={{ display: "flex", gap: 12, padding: "5px 12px", borderBottom: "1px solid rgba(0,212,255,0.04)", fontSize: 9, alignItems: "flex-start" }}>
                  <span style={{ minWidth: 200, color: isSec ? "#a0f4ff" : "rgba(0,212,255,0.55)", fontWeight: isSec ? "bold" : "normal" }}>{k}</span>
                  <span style={{ color: "rgba(160,244,255,0.75)", wordBreak: "break-all", flex: 1 }}>{v}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Panel ───────────────────────────────────────────────────────────────

const TABS: { id: Tab; label: string }[] = [
  { id: "ping",        label: "PING"        },
  { id: "trace",       label: "TRACE"       },
  { id: "dns",         label: "DNS"         },
  { id: "whois",       label: "WHOIS"       },
  { id: "lan",         label: "LAN SCAN"    },
  { id: "connections", label: "CONNECTIONS" },
  { id: "interfaces",  label: "INTERFACES"  },
  { id: "ssl",         label: "SSL"         },
  { id: "headers",     label: "HEADERS"     },
];

export function NetworkPanel() {
  const [tab, setTab] = useState<Tab>("ping");

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ display: "flex", flexWrap: "nowrap", overflowX: "auto", padding: "12px 16px 0", borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0 }}>
        {TABS.map(({ id, label }) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "6px 10px", fontSize: 7, letterSpacing: 2, flexShrink: 0,
            background: tab === id ? "rgba(0,212,255,0.08)" : "transparent",
            border: "none", borderBottom: `2px solid ${tab === id ? "#00d4ff" : "transparent"}`,
            color: tab === id ? "#00d4ff" : "rgba(0,212,255,0.35)",
            cursor: "pointer", fontFamily: "inherit", transition: "all 0.2s ease",
          }}>
            {label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {tab === "ping"        && <PingTab />}
        {tab === "trace"       && <TraceTab />}
        {tab === "dns"         && <DnsTab />}
        {tab === "whois"       && <WhoisTab />}
        {tab === "lan"         && <LanTab />}
        {tab === "connections" && <ConnectionsTab />}
        {tab === "interfaces"  && <InterfacesTab />}
        {tab === "ssl"         && <SslTab />}
        {tab === "headers"     && <HeadersTab />}
      </div>
    </div>
  );
}

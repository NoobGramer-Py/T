import { useState, useEffect, useRef } from "react";
import { useIntel, type IntelConfirmRequest, type IntelGraph } from "../../hooks/useBridge";

const J    = "#00d4ff";
const DIM  = "rgba(0,212,255,0.35)";
const CARD: React.CSSProperties = {
  background: "rgba(0,212,255,0.02)",
  border:     "1px solid rgba(0,212,255,0.09)",
  borderRadius: 4, padding: "14px 16px",
};

const RISK_COLOR: Record<string, string> = {
  LOW: "#00ff88", MEDIUM: "#ffb300", HIGH: "#ff6600", CRITICAL: "#ff2200",
};

// ── Shared UI ─────────────────────────────────────────────────────────────────

function Btn({ label, onClick, danger = false, disabled = false, glow = false }: {
  label: string; onClick: () => void;
  danger?: boolean; disabled?: boolean; glow?: boolean;
}) {
  const c = danger ? "#ff3300" : glow ? "#00ff88" : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 14px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${danger ? "255,51,0" : glow ? "0,255,136" : "0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.08)" : `rgba(${danger ? "255,51,0" : glow ? "0,255,136" : "0,212,255"},0.3)`}`,
      color: disabled ? "rgba(0,212,255,0.2)" : c,
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", whiteSpace: "nowrap" as const,
      boxShadow: glow && !disabled ? "0 0 10px rgba(0,255,136,0.18)" : "none",
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

// ── Confirm modal ─────────────────────────────────────────────────────────────

function ConfirmModal({ req, onConfirm }: {
  req: IntelConfirmRequest;
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
          INTELLIGENCE ACTION · CONFIRMATION
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{
            padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
            border: `1px solid ${RISK_COLOR[req.risk] || J}`,
            color: RISK_COLOR[req.risk] || J,
          }}>{req.risk}</div>
          <span style={{ color: "#a0f4ff", fontSize: 12, fontWeight: 600 }}>
            {req.action.replace(/_/g, " ").toUpperCase()}
          </span>
        </div>
        <div style={{
          fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.7)",
          background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.08)",
          borderRadius: 3, padding: "8px 12px", marginBottom: 14, wordBreak: "break-all",
        }}>{req.command}</div>
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.55)", marginBottom: 22, lineHeight: 1.65 }}>
          {req.description}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn label="CANCEL"  onClick={() => onConfirm(false)} danger />
          <Btn label="CONFIRM" onClick={() => onConfirm(true)}  glow />
        </div>
      </div>
    </div>
  );
}

// ── Stream output ─────────────────────────────────────────────────────────────

function StreamOutput({ lines, onClear }: {
  lines: { chunk: string; ts: number }[];
  onClear: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  if (lines.length === 0) return null;
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 7, letterSpacing: 4, color: DIM }}>INTELLIGENCE OUTPUT</span>
        <button onClick={onClear} style={{
          fontSize: 7, padding: "2px 8px", background: "transparent",
          border: "1px solid rgba(0,212,255,0.15)", color: DIM,
          cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
        }}>CLEAR</button>
      </div>
      <div style={{
        background: "rgba(0,0,0,0.4)", border: "1px solid rgba(0,212,255,0.07)",
        borderRadius: 3, padding: "10px 12px", maxHeight: 380, overflowY: "auto",
        fontFamily: "monospace", fontSize: 10, lineHeight: 1.6,
      }}>
        {lines.map((l, i) => (
          <div key={i} style={{
            color: l.chunk.startsWith("[ERROR]") ? "#ff4400" :
                   l.chunk.startsWith("[T]")     ? J :
                   l.chunk.startsWith("[+]") || l.chunk.startsWith("FOUND") ? "#00ff88" :
                   l.chunk.startsWith("─") || l.chunk.startsWith("═") ? "rgba(0,212,255,0.25)" :
                   "rgba(0,212,255,0.72)",
            fontWeight: l.chunk.startsWith("[+]") || l.chunk.startsWith("FOUND") ? 600 : undefined,
          }}>{l.chunk}</div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ── D3-style graph canvas (pure canvas, no D3 dep needed) ─────────────────────

function GraphCanvas({ graph }: { graph: IntelGraph }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef   = useRef<number>(0);

  // Simple force-directed layout simulation
  const posRef = useRef<Record<string, { x: number; y: number; vx: number; vy: number }>>({});

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;

    // Initialise positions for new nodes
    graph.nodes.forEach(n => {
      if (!posRef.current[n.id]) {
        posRef.current[n.id] = {
          x: W / 2 + (Math.random() - 0.5) * 300,
          y: H / 2 + (Math.random() - 0.5) * 200,
          vx: 0, vy: 0,
        };
      }
    });

    // Remove positions for deleted nodes
    const ids = new Set(graph.nodes.map(n => n.id));
    Object.keys(posRef.current).forEach(k => {
      if (!ids.has(k)) delete posRef.current[k];
    });

    let tick = 0;

    const draw = () => {
      animRef.current = requestAnimationFrame(draw);
      tick++;

      // Force simulation (100 ticks only, then freeze)
      if (tick < 120) {
        const pos = posRef.current;
        const k = 80;   // spring rest length

        // Repulsion between all nodes
        graph.nodes.forEach(a => {
          graph.nodes.forEach(b => {
            if (a.id === b.id) return;
            const pa = pos[a.id], pb = pos[b.id];
            if (!pa || !pb) return;
            const dx = pa.x - pb.x;
            const dy = pa.y - pb.y;
            const d  = Math.sqrt(dx * dx + dy * dy) || 1;
            const f  = 2000 / (d * d);
            pa.vx += dx / d * f;
            pa.vy += dy / d * f;
          });
        });

        // Attraction along edges
        graph.edges.forEach(e => {
          const pa = pos[e.source], pb = pos[e.target];
          if (!pa || !pb) return;
          const dx = pb.x - pa.x;
          const dy = pb.y - pa.y;
          const d  = Math.sqrt(dx * dx + dy * dy) || 1;
          const f  = (d - k) * 0.05;
          pa.vx += dx / d * f; pa.vy += dy / d * f;
          pb.vx -= dx / d * f; pb.vy -= dy / d * f;
        });

        // Center gravity
        graph.nodes.forEach(n => {
          const p = pos[n.id];
          if (!p) return;
          p.vx += (W / 2 - p.x) * 0.005;
          p.vy += (H / 2 - p.y) * 0.005;
          // Damping + integrate
          p.vx *= 0.85; p.vy *= 0.85;
          p.x  += p.vx; p.y  += p.vy;
          // Clamp to canvas
          p.x = Math.max(24, Math.min(W - 24, p.x));
          p.y = Math.max(24, Math.min(H - 24, p.y));
        });
      }

      // Draw
      ctx.clearRect(0, 0, W, H);

      // Grid background
      ctx.strokeStyle = "rgba(0,212,255,0.04)";
      ctx.lineWidth = 0.5;
      for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (let y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

      // Edges
      graph.edges.forEach(e => {
        const pa = posRef.current[e.source];
        const pb = posRef.current[e.target];
        if (!pa || !pb) return;

        ctx.beginPath();
        ctx.moveTo(pa.x, pa.y);
        ctx.lineTo(pb.x, pb.y);
        ctx.strokeStyle = "rgba(0,212,255,0.15)";
        ctx.lineWidth = Math.max(0.5, e.weight * 0.5);
        ctx.stroke();

        // Edge label
        const mx = (pa.x + pb.x) / 2;
        const my = (pa.y + pb.y) / 2;
        ctx.fillStyle = "rgba(0,212,255,0.3)";
        ctx.font = "7px Courier New";
        ctx.textAlign = "center";
        ctx.fillText(e.label, mx, my - 4);
      });

      // Nodes
      graph.nodes.forEach(n => {
        const p = posRef.current[n.id];
        if (!p) return;
        const r = 10;
        const color = n.color || "#00d4ff";

        // Glow
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 2.5);
        grad.addColorStop(0, color + "40");
        grad.addColorStop(1, "transparent");
        ctx.beginPath();
        ctx.arc(p.x, p.y, r * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        // Circle
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color + "22";
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Label
        ctx.fillStyle = color;
        ctx.font      = "bold 8px Courier New";
        ctx.textAlign = "center";
        ctx.fillText(n.label.slice(0, 20), p.x, p.y + r + 12);
      });
    };

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [graph]);

  if (graph.nodes.length === 0) {
    return (
      <div style={{
        height: 300, display: "flex", alignItems: "center", justifyContent: "center",
        border: "1px solid rgba(0,212,255,0.07)", borderRadius: 4,
        color: "rgba(0,212,255,0.2)", fontSize: 9, letterSpacing: 4,
        flexDirection: "column", gap: 12,
      }}>
        <div style={{ fontSize: 20, opacity: 0.3 }}>◎</div>
        GRAPH EMPTY — RUN INTEL TO POPULATE
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      width={780}
      height={380}
      style={{
        width: "100%", height: 380,
        border: "1px solid rgba(0,212,255,0.07)", borderRadius: 4,
        background: "rgba(0,6,18,0.6)",
      }}
    />
  );
}

// ── Graph legend ──────────────────────────────────────────────────────────────

function GraphLegend({ graph }: { graph: IntelGraph }) {
  const counts: Record<string, number> = {};
  graph.nodes.forEach(n => { counts[n.type] = (counts[n.type] || 0) + 1; });

  const COLORS: Record<string, string> = {
    person: "#00ff88", org: "#00d4ff", domain: "#a0f4ff",
    ip: "#ffb300", email: "#ff88cc", username: "#cc88ff",
    phone: "#ff6600", breach: "#ff3300", social: "#0088ff",
    location: "#88ff88",
  };

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
      {Object.entries(counts).map(([type, count]) => (
        <div key={type} style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: COLORS[type] || "#888",
            boxShadow: `0 0 5px ${COLORS[type] || "#888"}`,
          }} />
          <span style={{ fontSize: 8, color: "rgba(0,212,255,0.5)", letterSpacing: 2 }}>
            {type} ({count})
          </span>
        </div>
      ))}
      <div style={{ fontSize: 8, color: DIM, marginLeft: "auto" }}>
        {graph.nodes.length} nodes · {graph.edges.length} edges
      </div>
    </div>
  );
}

// ── Main IntelTab ─────────────────────────────────────────────────────────────

export function IntelTab() {
  const intel = useIntel();

  // Person
  const [pQuery,    setPQuery]    = useState("");
  const [pType,     setPType]     = useState<"username"|"email"|"phone"|"name"|"ip">("username");
  // Org
  const [orgDomain, setOrgDomain] = useState("");
  // Breach
  const [bEmail,    setBEmail]    = useState("");
  const [bPass,     setBPass]     = useState("");
  const [wlInfo,    setWlInfo]    = useState({ first: "", last: "", pet: "", company: "", birthdate: "" });
  // Dark web
  const [dwQuery,   setDwQuery]   = useState("");
  const [dwEmail,   setDwEmail]   = useState("");
  // Section
  const [section,   setSection]   = useState<"person"|"org"|"breach"|"darkweb"|"graph">("person");

  const myLines = intel.streamLines.map(l => ({ chunk: l.chunk, ts: l.ts }));

  const SECTIONS = [
    { id: "person",  label: "PERSON"    },
    { id: "org",     label: "ORG"       },
    { id: "breach",  label: "BREACH"    },
    { id: "darkweb", label: "DARK WEB"  },
    { id: "graph",   label: "REL GRAPH" },
  ];

  const P_TYPES: { id: typeof pType; label: string }[] = [
    { id: "username", label: "Username" },
    { id: "email",    label: "Email"    },
    { id: "phone",    label: "Phone"    },
    { id: "name",     label: "Full name"},
    { id: "ip",       label: "IP"       },
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Confirm modal */}
      {intel.confirmReq && (
        <ConfirmModal
          req={intel.confirmReq}
          onConfirm={c => intel.confirm(intel.confirmReq!.id, c)}
        />
      )}

      {/* Header */}
      <div style={{
        padding: "12px 20px 0", borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 10 }}>
          <div style={{ fontSize: 9, letterSpacing: 6, color: DIM }}>
            T · INTELLIGENCE SYSTEM
          </div>
          {intel.lastDone && (
            <div style={{
              padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
              background: "rgba(0,255,136,0.06)", border: "1px solid rgba(0,255,136,0.2)",
              color: "#00ff88",
            }}>
              {intel.lastDone.action.replace(/_/g, " ")} · {intel.lastDone.duration}s
            </div>
          )}
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <Btn label="GRAPH" onClick={() => { intel.getGraph(); setSection("graph"); }} />
            <Btn label="RESET GRAPH" onClick={intel.resetGraph} danger />
            <Btn label="CLEAR OUTPUT" onClick={intel.clearStream} />
          </div>
        </div>
        <div style={{ display: "flex", gap: 2 }}>
          {SECTIONS.map(s => (
            <button key={s.id} onClick={() => setSection(s.id as typeof section)} style={{
              padding: "5px 12px", fontSize: 7, letterSpacing: 3, background: "transparent",
              border: "none",
              borderBottom: `2px solid ${section === s.id ? J : "transparent"}`,
              color: section === s.id ? J : DIM,
              cursor: "pointer", fontFamily: "inherit",
            }}>{s.label}</button>
          ))}
        </div>
      </div>

      {/* Error */}
      {intel.error && (
        <div style={{
          flexShrink: 0, margin: "8px 20px 0",
          background: "rgba(255,51,0,0.07)", border: "1px solid rgba(255,51,0,0.2)",
          borderRadius: 3, padding: "8px 12px", fontSize: 10, color: "#ff4400",
          display: "flex", justifyContent: "space-between",
        }}>
          <span>{intel.error}</span>
          <button onClick={intel.clearError} style={{ background: "none", border: "none", color: "#ff4400", cursor: "pointer" }}>✕</button>
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

        {/* ── PERSON PROFILER ── */}
        {section === "person" && (
          <div>
            <div style={{ ...CARD, marginBottom: 16 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>PERSON PROFILER</div>

              {/* Type selector */}
              <div style={{ display: "flex", gap: 4, marginBottom: 12, flexWrap: "wrap" }}>
                {P_TYPES.map(t => (
                  <button key={t.id} onClick={() => setPType(t.id)} style={{
                    padding: "4px 10px", fontSize: 8, cursor: "pointer", fontFamily: "inherit",
                    background: pType === t.id ? "rgba(0,212,255,0.1)" : "transparent",
                    border: `1px solid rgba(0,212,255,${pType === t.id ? "0.4" : "0.1"})`,
                    color: pType === t.id ? J : DIM, borderRadius: 2,
                  }}>{t.label}</button>
                ))}
              </div>

              <Input
                label={pType === "username" ? "USERNAME" :
                       pType === "email"    ? "EMAIL ADDRESS" :
                       pType === "phone"    ? "PHONE NUMBER (+intl format)" :
                       pType === "name"     ? "FULL NAME" : "IP ADDRESS"}
                value={pQuery} onChange={setPQuery}
                placeholder={pType === "username" ? "john_doe" :
                             pType === "email"    ? "john@example.com" :
                             pType === "phone"    ? "+14155552671 or +923001234567" :
                             pType === "name"     ? "John Doe" : "8.8.8.8"}
              />

              {/* Phone — dedicated full dossier block */}
              {pType === "phone" && (
                <div style={{
                  background: "rgba(0,212,255,0.02)",
                  border: "1px solid rgba(0,212,255,0.1)",
                  borderRadius: 4, padding: "12px 14px", marginBottom: 12,
                }}>
                  <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 10 }}>
                    PHONE DOSSIER — 9-STAGE PIPELINE
                  </div>
                  <div style={{ fontSize: 9, color: "rgba(0,212,255,0.5)", marginBottom: 12, lineHeight: 1.7 }}>
                    Stage 1: PhoneInfoga — carrier, region, line type<br />
                    Stage 2: Country code decode + number format<br />
                    Stage 3: Caller-ID / spam reputation + NumVerify<br />
                    Stage 4: WhatsApp / Telegram presence check<br />
                    Stage 5: Social media search by number<br />
                    Stage 6: Breach databases + paste sites + GitHub<br />
                    Stage 7: Dark web / Ahmia search<br />
                    Stage 8: Reverse lookup — name + address derivation<br />
                    Stage 9: Derived usernames → Sherlock + Maigret cross-search
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Btn label="▶ FULL PERSON DOSSIER" glow
                      onClick={() => intel.dispatch("phone_dossier", { query: pQuery })}
                      disabled={!pQuery.trim()} />
                    <Btn label="PHONE INTEL ONLY"
                      onClick={() => intel.dispatch("person_phone", { query: pQuery })}
                      disabled={!pQuery.trim()} />
                  </div>
                </div>
              )}

              {/* Non-phone query buttons */}
              {pType !== "phone" && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  <Btn label="▶ FULL DOSSIER" glow
                    onClick={() => intel.dispatch("person_dossier", { query: pQuery, query_type: pType })}
                    disabled={!pQuery.trim()} />
                  {pType === "username" && <Btn label="SHERLOCK + MAIGRET" onClick={() => intel.dispatch("person_username", { query: pQuery })} />}
                  {pType === "email"    && <Btn label="HOLEHE + WHOIS"     onClick={() => intel.dispatch("person_email",    { query: pQuery })} />}
                  {pType === "name"     && <Btn label="THEHARVESTER"        onClick={() => intel.dispatch("person_name",     { query: pQuery })} />}
                  {pType === "ip"       && <Btn label="GEOLOCATION"         onClick={() => intel.dispatch("person_ip",       { query: pQuery })} />}
                </div>
              )}

              {/* Full dossier button for all types */}
              {pType !== "phone" && (
                <div style={{ marginTop: 6 }}></div>
              )}
            </div>
            <StreamOutput lines={myLines} onClear={intel.clearStream} />
          </div>
        )}

        {/* ── ORG PROFILER ── */}
        {section === "org" && (
          <div>
            <div style={{ ...CARD, marginBottom: 16 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>ORGANISATION PROFILER</div>
              <Input label="DOMAIN / COMPANY NAME" value={orgDomain} onChange={setOrgDomain}
                placeholder="example.com" />
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                <Btn label="▶ FULL FOOTPRINT" glow
                  onClick={() => intel.dispatch("org_full", { domain: orgDomain })}
                  disabled={!orgDomain.trim()} />
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                <Btn label="WHOIS"        onClick={() => intel.dispatch("org_whois",      { domain: orgDomain })} />
                <Btn label="DNS"          onClick={() => intel.dispatch("org_dns",        { domain: orgDomain })} />
                <Btn label="SUBDOMAINS"   onClick={() => intel.dispatch("org_subdomains", { domain: orgDomain })} />
                <Btn label="TECH STACK"   onClick={() => intel.dispatch("org_tech",       { domain: orgDomain })} />
                <Btn label="EMAIL HARVEST"onClick={() => intel.dispatch("org_emails",     { domain: orgDomain })} />
                <Btn label="SHODAN"       onClick={() => intel.dispatch("org_shodan",     { domain: orgDomain })} />
              </div>
            </div>
            <StreamOutput lines={myLines} onClear={intel.clearStream} />
          </div>
        )}

        {/* ── BREACH ── */}
        {section === "breach" && (
          <div>
            {/* Email breach check */}
            <div style={{ ...CARD, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>BREACH DATABASE SEARCH</div>
              <Input label="EMAIL ADDRESS" value={bEmail} onChange={setBEmail} placeholder="victim@example.com" />
              <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
                <Btn label="HIVP CHECK"      onClick={() => intel.dispatch("breach_hibp",    { email: bEmail })} />
                <Btn label="DEHASHED SEARCH" onClick={() => intel.dispatch("breach_dehashed", { query: bEmail, query_type: "email" })} />
                <Btn label="PASTE SITES"     onClick={() => intel.dispatch("breach_paste",    { query: bEmail })} />
                <Btn label="DARK WEB"        onClick={() => intel.dispatch("darkweb_email",   { email: bEmail })} />
              </div>
            </div>

            {/* Password check */}
            <div style={{ ...CARD, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>PASSWORD BREACH CHECK</div>
              <div style={{ fontSize: 9, color: "rgba(0,212,255,0.45)", marginBottom: 10, lineHeight: 1.6 }}>
                Uses k-anonymity — only the first 5 chars of the SHA1 hash are sent. Password never transmitted.
              </div>
              <Input label="PASSWORD TO CHECK" value={bPass} onChange={setBPass} type="password" placeholder="enter password to check" />
              <Btn label="CHECK AGAINST HIBP" onClick={() => intel.dispatch("breach_password_check", { password: bPass })} />
            </div>

            {/* Targeted wordlist */}
            <div style={{ ...CARD, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>TARGETED WORDLIST — CUPP</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Input label="FIRST NAME" value={wlInfo.first} onChange={v => setWlInfo(p => ({...p, first: v}))} placeholder="John" />
                <Input label="LAST NAME"  value={wlInfo.last}  onChange={v => setWlInfo(p => ({...p, last:  v}))} placeholder="Doe" />
                <Input label="PET NAME"   value={wlInfo.pet}   onChange={v => setWlInfo(p => ({...p, pet:   v}))} placeholder="Fluffy" />
                <Input label="COMPANY"    value={wlInfo.company} onChange={v => setWlInfo(p => ({...p, company: v}))} placeholder="Acme" />
                <Input label="BIRTHDATE (DDMMYYYY)" value={wlInfo.birthdate} onChange={v => setWlInfo(p => ({...p, birthdate: v}))} placeholder="01011990" />
              </div>
              <Btn label="GENERATE WORDLIST" onClick={() => intel.dispatch("breach_wordlist", wlInfo)} />
            </div>

            <StreamOutput lines={myLines} onClear={intel.clearStream} />
          </div>
        )}

        {/* ── DARK WEB ── */}
        {section === "darkweb" && (
          <div>
            <div style={{
              background: "rgba(128,0,255,0.04)", border: "1px solid rgba(128,0,255,0.15)",
              borderRadius: 3, padding: "10px 14px", marginBottom: 14, fontSize: 9,
              color: "rgba(200,150,255,0.7)", lineHeight: 1.65,
            }}>
              🧅 Dark web searches run via Tor on your attack VM.
              Start with SETUP TOR to verify connectivity before searching .onion sites.
            </div>

            <div style={{ ...CARD, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>DARK WEB SEARCH</div>
              <Input label="SEARCH QUERY" value={dwQuery} onChange={setDwQuery}
                placeholder="email@example.com or target name" />
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                <Btn label="SETUP TOR"       onClick={() => intel.dispatch("darkweb_setup_tor", {})} />
                <Btn label="AHMIA SEARCH"    onClick={() => intel.dispatch("darkweb_search",       { query: dwQuery })} />
                <Btn label=".ONION SEARCH"   onClick={() => intel.dispatch("darkweb_onion_search", { query: dwQuery })} />
                <Btn label="INTELX SEARCH"   onClick={() => intel.dispatch("darkweb_intelx",       { query: dwQuery })} />
                <Btn label="PASTE MONITOR"   onClick={() => intel.dispatch("darkweb_paste_monitor",{ query: dwQuery, duration: "30" })} />
              </div>
            </div>

            <div style={{ ...CARD, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>EMAIL ON DARK WEB</div>
              <Input label="EMAIL ADDRESS" value={dwEmail} onChange={setDwEmail} placeholder="target@example.com" />
              <Btn label="SEARCH EMAIL ON DARK WEB"
                onClick={() => intel.dispatch("darkweb_email", { email: dwEmail })} />
            </div>

            <div style={{ ...CARD, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 10 }}>KNOWN .ONION DIRECTORY</div>
              <Btn label="LIST KNOWN .ONION SITES" onClick={() => intel.dispatch("darkweb_onions", {})} />
            </div>

            <StreamOutput lines={myLines} onClear={intel.clearStream} />
          </div>
        )}

        {/* ── RELATIONSHIP GRAPH ── */}
        {section === "graph" && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM }}>
                ENTITY RELATIONSHIP GRAPH
              </div>
              <span style={{ fontSize: 9, color: "rgba(0,212,255,0.4)" }}>
                Auto-populated from intel results
              </span>
              <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                <Btn label="REFRESH" onClick={intel.getGraph} />
                <Btn label="CLEAR"   onClick={intel.resetGraph} danger />
              </div>
            </div>

            <GraphCanvas graph={intel.graph} />
            <GraphLegend graph={intel.graph} />

            {intel.graph.nodes.length > 0 && (
              <div style={{ marginTop: 14, ...CARD }}>
                <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 10 }}>NODE LIST</div>
                <div style={{ maxHeight: 200, overflowY: "auto" }}>
                  {intel.graph.nodes.map(n => (
                    <div key={n.id} style={{
                      display: "flex", gap: 10, padding: "4px 8px", marginBottom: 2,
                      borderRadius: 2, background: "rgba(0,212,255,0.01)",
                      fontSize: 9, fontFamily: "monospace",
                    }}>
                      <div style={{ width: 7, height: 7, borderRadius: "50%", marginTop: 3, flexShrink: 0,
                        background: n.color, boxShadow: `0 0 4px ${n.color}` }} />
                      <span style={{ color: n.color, minWidth: 70 }}>{n.type}</span>
                      <span style={{ color: "#a0f4ff", flex: 1 }}>{n.label}</span>
                      {n.detail && <span style={{ color: DIM, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{n.detail}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

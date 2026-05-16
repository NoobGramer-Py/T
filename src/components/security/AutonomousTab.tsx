import { useState } from "react";
import { useAutonomous, type AutoStep, type AutoConfirmRequest, type AutoMemory } from "../../hooks/useBridge";

const J   = "#00d4ff";
const DIM = "rgba(0,212,255,0.35)";

const STATUS_COLOR: Record<string, string> = {
  pending: "rgba(0,212,255,0.2)",
  running: "#ffb300",
  done:    "#00ff88",
  error:   "#ff3300",
  skipped: "rgba(0,212,255,0.2)",
};

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  running: "◌",
  done:    "●",
  error:   "✕",
  skipped: "—",
};

const RISK_COLOR: Record<string, string> = {
  HIGH:     "#ff6600",
  CRITICAL: "#ff2200",
};

function Btn({ label, onClick, danger = false, disabled = false, glow = false }: {
  label: string; onClick: () => void;
  danger?: boolean; disabled?: boolean; glow?: boolean;
}) {
  const c = danger ? "#ff3300" : glow ? "#00ff88" : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "6px 16px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${danger ? "255,51,0" : glow ? "0,255,136" : "0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.08)"
        : `rgba(${danger ? "255,51,0" : glow ? "0,255,136" : "0,212,255"},0.3)`}`,
      color: disabled ? "rgba(0,212,255,0.2)" : c,
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", whiteSpace: "nowrap" as const,
      boxShadow: glow && !disabled ? "0 0 12px rgba(0,255,136,0.2)" : "none",
      transition: "all 0.15s ease",
    }}>{label}</button>
  );
}

// ── Confirm modal ─────────────────────────────────────────────────────────────

function ConfirmModal({ req, onConfirm }: {
  req: AutoConfirmRequest;
  onConfirm: (c: boolean) => void;
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 300, background: "rgba(0,0,0,0.88)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "#000a15", border: `1px solid ${RISK_COLOR[req.risk]}40`,
        borderRadius: 6, padding: "28px 32px", maxWidth: 480, width: "90%",
        boxShadow: `0 0 40px ${RISK_COLOR[req.risk]}18`,
      }}>
        <div style={{ fontSize: 7, letterSpacing: 5, color: DIM, marginBottom: 14 }}>
          AUTONOMOUS ENGINE · CONFIRMATION REQUIRED
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
          <div style={{
            padding: "3px 10px", fontSize: 7, letterSpacing: 3, borderRadius: 2,
            border: `1px solid ${RISK_COLOR[req.risk]}`,
            color: RISK_COLOR[req.risk], fontWeight: 700,
          }}>{req.risk}</div>
          <span style={{ color: "#a0f4ff", fontSize: 13, fontWeight: 600 }}>
            {req.step}
          </span>
        </div>

        <div style={{
          fontFamily: "monospace", fontSize: 10, color: "rgba(0,212,255,0.6)",
          background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.08)",
          borderRadius: 3, padding: "8px 12px", marginBottom: 12,
        }}>tool: {req.tool}</div>

        <div style={{
          fontSize: 11, color: "rgba(0,212,255,0.6)", marginBottom: 24,
          lineHeight: 1.65,
        }}>{req.reason}</div>

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <Btn label="SKIP THIS STEP" onClick={() => onConfirm(false)} danger />
          <Btn label="CONFIRM + RUN"  onClick={() => onConfirm(true)}  glow />
        </div>
      </div>
    </div>
  );
}

// ── Step progress card ────────────────────────────────────────────────────────

function StepCard({ step, index }: { step: AutoStep; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const color = STATUS_COLOR[step.status] || DIM;
  const isRunning = step.status === "running";

  return (
    <div style={{
      background: isRunning ? "rgba(255,179,0,0.03)" : "rgba(0,212,255,0.015)",
      border: `1px solid ${isRunning ? "rgba(255,179,0,0.15)" : "rgba(0,212,255,0.07)"}`,
      borderRadius: 3, marginBottom: 4, overflow: "hidden",
      transition: "all 0.2s ease",
    }}>
      <div
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "8px 12px", cursor: "pointer",
        }}
        onClick={() => setExpanded(e => !e)}
      >
        {/* Step number */}
        <span style={{
          fontSize: 8, color: "rgba(0,212,255,0.25)",
          minWidth: 18, textAlign: "right",
        }}>{index + 1}</span>

        {/* Status dot */}
        <div style={{
          width: 7, height: 7, borderRadius: "50%",
          background: color, flexShrink: 0,
          boxShadow: step.status === "done" ? `0 0 6px ${color}` : "none",
          animation: isRunning ? "pulse-voice 1s ease-in-out infinite" : "none",
        }} />

        {/* Icon */}
        <span style={{ color, fontSize: 10, minWidth: 12 }}>
          {STATUS_ICON[step.status]}
        </span>

        {/* Step name */}
        <span style={{
          color: isRunning ? "#ffb300" : step.status === "done" ? "#a0f4ff" : DIM,
          fontSize: 11, fontWeight: isRunning ? 600 : 400,
          minWidth: 140,
        }}>{step.step}</span>

        {/* Tool badge */}
        <span style={{
          fontSize: 7, letterSpacing: 1, color: "rgba(0,212,255,0.3)",
          fontFamily: "monospace", minWidth: 100,
        }}>{step.tool}</span>

        {/* Summary */}
        <span style={{
          flex: 1, fontSize: 9, color: "rgba(0,212,255,0.5)",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{step.summary}</span>

        {/* Duration */}
        {step.duration > 0 && (
          <span style={{ fontSize: 8, color: "rgba(0,212,255,0.25)", marginLeft: 8 }}>
            {step.duration}s
          </span>
        )}

        {/* Expand toggle */}
        <span style={{ fontSize: 8, color: DIM, marginLeft: 4 }}>
          {expanded ? "▲" : "▼"}
        </span>
      </div>

      {/* Expanded: full summary */}
      {expanded && (
        <div style={{
          padding: "8px 12px 10px 40px",
          borderTop: "1px solid rgba(0,212,255,0.06)",
          fontSize: 10, color: "rgba(0,212,255,0.65)",
          lineHeight: 1.65, fontFamily: "monospace",
        }}>
          {step.summary || "No output captured."}
        </div>
      )}
    </div>
  );
}

// ── Memory readout ────────────────────────────────────────────────────────────

function MemoryPanel({ memory }: { memory: AutoMemory }) {
  const items = [
    { label: "HOSTS",      value: memory.hosts.length,               color: J },
    { label: "SUBDOMAINS", value: memory.subdomains,                  color: "#a0f4ff" },
    { label: "VULNS",      value: memory.vulns,                       color: "#ff6600" },
    { label: "CREDS",      value: memory.creds,                       color: "#ff3300" },
    { label: "FLAGS",      value: memory.flags.length,                color: "#00ff88" },
    { label: "EMAILS",     value: memory.emails,                      color: "#ff88cc" },
    { label: "SOCIAL",     value: memory.social,                      color: "#cc88ff" },
    { label: "SESSIONS",   value: memory.sessions.length,             color: "#00ff88" },
  ];

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 10 }}>
        WORKING MEMORY — {memory.elapsed}s elapsed
      </div>

      {/* Metric grid */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
        {items.map(({ label, value, color }) => (
          <div key={label} style={{
            background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
            borderRadius: 3, padding: "8px 12px", textAlign: "center", minWidth: 70,
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: 6, letterSpacing: 3, color: DIM, marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Flags — highlighted */}
      {memory.flags.length > 0 && (
        <div style={{
          background: "rgba(0,255,136,0.05)", border: "1px solid rgba(0,255,136,0.2)",
          borderRadius: 3, padding: "10px 14px",
        }}>
          <div style={{ fontSize: 7, letterSpacing: 4, color: "#00ff88", marginBottom: 8 }}>
            FLAGS CAPTURED
          </div>
          {memory.flags.map((f, i) => (
            <div key={i} style={{
              fontFamily: "monospace", fontSize: 12,
              color: "#00ff88", fontWeight: 700, marginBottom: 2,
            }}>▶ {f}</div>
          ))}
        </div>
      )}

      {/* Hosts + ports */}
      {memory.hosts.length > 0 && (
        <div style={{
          marginTop: 8, background: "rgba(0,212,255,0.02)",
          border: "1px solid rgba(0,212,255,0.07)",
          borderRadius: 3, padding: "8px 12px",
        }}>
          <div style={{ fontSize: 7, letterSpacing: 4, color: DIM, marginBottom: 8 }}>
            DISCOVERED HOSTS
          </div>
          {memory.hosts.slice(0, 10).map((h, i) => {
            const ports = memory.open_ports[h] || [];
            return (
              <div key={i} style={{
                display: "flex", gap: 12, fontSize: 10,
                fontFamily: "monospace", marginBottom: 3,
              }}>
                <span style={{ color: "#a0f4ff", minWidth: 130 }}>{h}</span>
                <span style={{ color: "rgba(0,212,255,0.45)" }}>
                  {ports.length > 0
                    ? `ports: ${ports.slice(0, 10).join(", ")}${ports.length > 10 ? "…" : ""}`
                    : ""}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Quick task presets ────────────────────────────────────────────────────────

const PRESETS = [
  { label: "🔍 Audit",      template: "audit {target}" },
  { label: "🏴 CTF Box",    template: "ctf {target}" },
  { label: "⚔ Full Attack", template: "attack {target}" },
  { label: "🧠 OSINT",      template: "profile {target}" },
];

// ── Main AutonomousTab ────────────────────────────────────────────────────────

export function AutonomousTab() {
  const auto = useAutonomous();
  const [goal,   setGoal]   = useState("");
  const [target, setTarget] = useState("");
  const [section, setSection] = useState<"config" | "progress" | "memory" | "report">("config");

  const launch = () => {
    if (!goal.trim()) return;
    auto.reset();
    auto.startTask(goal.trim(), target.trim());
    setSection("progress");
  };

  const applyPreset = (template: string) => {
    const filled = template.replace("{target}", target || "TARGET");
    setGoal(filled);
  };

  const SECTIONS = [
    { id: "config",   label: "CONFIGURE" },
    { id: "progress", label: "EXECUTION"  },
    { id: "memory",   label: "FINDINGS"   },
    { id: "report",   label: "REPORT"     },
  ];

  const doneSteps    = auto.steps.filter(s => s.status === "done").length;
  const errorSteps   = auto.steps.filter(s => s.status === "error").length;
  const runningStep  = auto.steps.find(s => s.status === "running");

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>

      {/* Confirm modal */}
      {auto.confirmReq && (
        <ConfirmModal req={auto.confirmReq} onConfirm={auto.confirm} />
      )}

      {/* Header */}
      <div style={{
        padding: "12px 20px 0",
        borderBottom: "1px solid rgba(0,212,255,0.08)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 10 }}>
          <div style={{ fontSize: 9, letterSpacing: 6, color: DIM }}>
            T · AUTONOMOUS ENGINE
          </div>

          {/* Status indicator */}
          {auto.running && (
            <>
              <div style={{
                width: 7, height: 7, borderRadius: "50%",
                background: "#00ff88",
                boxShadow: "0 0 8px #00ff88",
                animation: "pulse-voice 1.2s ease-in-out infinite",
              }} />
              <span style={{ fontSize: 8, color: "#00ff88", letterSpacing: 2 }}>
                {runningStep ? runningStep.step.toUpperCase() : "RUNNING"}
              </span>
            </>
          )}

          {auto.reportDone && !auto.running && (
            <div style={{
              padding: "2px 10px", fontSize: 7, letterSpacing: 3, borderRadius: 2,
              background: "rgba(0,255,136,0.07)", border: "1px solid rgba(0,255,136,0.25)",
              color: "#00ff88",
            }}>
              COMPLETE — {doneSteps} steps · {auto.memory?.flags.length || 0} flags
            </div>
          )}

          {errorSteps > 0 && (
            <div style={{
              padding: "2px 8px", fontSize: 7, letterSpacing: 2, borderRadius: 2,
              background: "rgba(255,51,0,0.07)", border: "1px solid rgba(255,51,0,0.2)",
              color: "#ff3300",
            }}>{errorSteps} errors</div>
          )}

          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            {!auto.running
              ? <Btn label="▶ LAUNCH" onClick={launch} glow disabled={!goal.trim()} />
              : <Btn label="■ STOP"   onClick={auto.stopTask} danger />
            }
          </div>
        </div>

        {/* Section tabs */}
        <div style={{ display: "flex", gap: 2 }}>
          {SECTIONS.map(s => (
            <button key={s.id}
              onClick={() => setSection(s.id as typeof section)}
              style={{
                padding: "5px 12px", fontSize: 7, letterSpacing: 3,
                background: "transparent", border: "none",
                borderBottom: `2px solid ${section === s.id ? J : "transparent"}`,
                color: section === s.id ? J : DIM,
                cursor: "pointer", fontFamily: "inherit",
              }}>{s.label}</button>
          ))}
        </div>
      </div>

      {/* Error bar */}
      {auto.error && (
        <div style={{
          flexShrink: 0, margin: "8px 20px 0",
          background: "rgba(255,51,0,0.07)", border: "1px solid rgba(255,51,0,0.2)",
          borderRadius: 3, padding: "8px 12px", fontSize: 10, color: "#ff4400",
        }}>{auto.error}</div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

        {/* ── CONFIGURE ── */}
        {section === "config" && (
          <div>
            <div style={{
              background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.09)",
              borderRadius: 4, padding: "16px",  marginBottom: 16,
            }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 14 }}>
                AUTONOMOUS TASK
              </div>

              {/* Target */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>
                  TARGET (IP / domain / phone / name)
                </div>
                <input value={target} onChange={e => setTarget(e.target.value)}
                  placeholder="192.168.1.1  or  example.com  or  +923001234567"
                  style={{
                    width: "100%", background: "rgba(0,212,255,0.03)",
                    border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
                    padding: "7px 12px", color: "rgba(160,244,255,0.9)",
                    fontSize: 11, fontFamily: "monospace",
                    outline: "none", caretColor: J,
                  }}
                  onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
                  onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
                />
              </div>

              {/* Quick presets */}
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
                {PRESETS.map(p => (
                  <button key={p.label} onClick={() => applyPreset(p.template)} style={{
                    padding: "4px 12px", fontSize: 8, letterSpacing: 1,
                    background: "rgba(0,212,255,0.04)",
                    border: "1px solid rgba(0,212,255,0.12)",
                    color: "rgba(0,212,255,0.6)",
                    cursor: "pointer", fontFamily: "inherit", borderRadius: 3,
                  }}>{p.label}</button>
                ))}
              </div>

              {/* Goal */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>
                  GOAL (natural language)
                </div>
                <textarea
                  value={goal}
                  onChange={e => setGoal(e.target.value)}
                  rows={3}
                  placeholder={
                    "Examples:\n" +
                    "audit 192.168.1.1\n" +
                    "profile +923001234567\n" +
                    "ctf 10.10.10.40 — find user.txt and root.txt\n" +
                    "full attack chain on example.com, report everything"
                  }
                  style={{
                    width: "100%", resize: "vertical",
                    background: "rgba(0,212,255,0.03)",
                    border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
                    padding: "8px 12px", color: "rgba(160,244,255,0.9)",
                    fontSize: 11, fontFamily: "inherit",
                    outline: "none", caretColor: J, lineHeight: 1.6,
                  }}
                  onFocus={e => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
                  onBlur={e  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
                />
              </div>

              <Btn label="▶ LAUNCH AUTONOMOUS TASK" glow onClick={launch}
                disabled={!goal.trim()} />
            </div>

            {/* How it works */}
            <div style={{
              background: "rgba(0,212,255,0.01)", border: "1px solid rgba(0,212,255,0.07)",
              borderRadius: 4, padding: "14px 16px",
            }}>
              <div style={{ fontSize: 8, letterSpacing: 4, color: DIM, marginBottom: 12 }}>
                HOW IT WORKS
              </div>
              {[
                ["T detects goal type", "audit / CTF / OSINT / attack chain"],
                ["Builds a step plan",  "template steps + LLM-driven decisions"],
                ["Executes silently",   "LOW + MEDIUM risk tools run without asking"],
                ["Asks before attacks", "HIGH + CRITICAL tools pause for your YES"],
                ["Builds memory",       "every finding accumulated across all steps"],
                ["Auto-generates report", "HTML report with all findings when done"],
              ].map(([title, desc]) => (
                <div key={title} style={{
                  display: "flex", gap: 12, marginBottom: 6, fontSize: 10,
                }}>
                  <span style={{ color: J, minWidth: 160 }}>{title}</span>
                  <span style={{ color: "rgba(0,212,255,0.45)" }}>{desc}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── EXECUTION ── */}
        {section === "progress" && (
          <div>
            {auto.steps.length === 0 && !auto.running && (
              <div style={{
                fontSize: 9, color: DIM, fontStyle: "italic", padding: "20px 0",
              }}>No task running. Configure and launch from the CONFIGURE tab.</div>
            )}
            {auto.steps.map((s, i) => (
              <StepCard key={`${s.step}-${i}`} step={s} index={i} />
            ))}
            {auto.running && !runningStep && (
              <div style={{
                padding: "10px 12px", fontSize: 9,
                color: "#ffb300", animation: "data-flicker 2s ease infinite",
              }}>Planning next step...</div>
            )}
          </div>
        )}

        {/* ── FINDINGS / MEMORY ── */}
        {section === "memory" && (
          <div>
            {auto.memory
              ? <MemoryPanel memory={auto.memory} />
              : <div style={{ fontSize: 9, color: DIM, fontStyle: "italic", padding: "20px 0" }}>
                  No findings yet. Launch a task to populate working memory.
                </div>
            }
          </div>
        )}

        {/* ── REPORT ── */}
        {section === "report" && (
          <div>
            {!auto.reportDone ? (
              <div style={{ fontSize: 9, color: DIM, fontStyle: "italic", padding: "20px 0" }}>
                Report is generated automatically when the task completes.
              </div>
            ) : (
              <div>
                {auto.summary && (
                  <div style={{
                    background: "rgba(0,212,255,0.02)",
                    border: "1px solid rgba(0,212,255,0.09)",
                    borderRadius: 4, padding: "14px 16px", marginBottom: 16,
                    fontSize: 10, color: "rgba(0,212,255,0.75)", lineHeight: 1.8,
                    whiteSpace: "pre-wrap",
                  }}>{auto.summary}</div>
                )}
                {auto.reportPath && (
                  <div style={{
                    fontSize: 9, color: DIM, marginBottom: 12,
                    fontFamily: "monospace",
                  }}>
                    Report saved: {auto.reportPath}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

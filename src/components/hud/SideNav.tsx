import { useTStore, type ActivePanel } from "../../store";

interface NavItem {
  id:    ActivePanel;
  label: string;
  icon:  string;
  hint:  string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "chat",     label: "CORE",  icon: "◎", hint: "AI Interface"     },
  { id: "security", label: "SEC",   icon: "⬡", hint: "Cyber Security"   },
  { id: "system",   label: "SYS",   icon: "⊞", hint: "System Control"   },
  { id: "network",  label: "NET",   icon: "⊹", hint: "Network Intel"    },
  { id: "hardware", label: "HW",    icon: "⌁", hint: "Hardware Control" },
  { id: "settings", label: "CFG",   icon: "⚙", hint: "Config & Memory"  },
];

// ── Hexagonal node indicator ───────────────────────────────────────────────────
function HexNode({ active }: { active: boolean }) {
  return (
    <svg width="8" height="9" viewBox="0 0 8 9" style={{ flexShrink: 0 }}>
      <polygon
        points="4,0.5 7.5,2.5 7.5,6.5 4,8.5 0.5,6.5 0.5,2.5"
        fill={active ? "rgba(0,212,255,0.25)" : "transparent"}
        stroke={active ? "#00d4ff" : "rgba(0,212,255,0.18)"}
        strokeWidth="0.8"
        style={{ filter: active ? "drop-shadow(0 0 3px #00d4ff)" : "none" }}
      />
    </svg>
  );
}

export function SideNav() {
  const { activePanel, setPanel } = useTStore();

  return (
    <div style={{
      position: "fixed", top: 52, left: 0, bottom: 0,
      width: 64, zIndex: 40,
      background: "linear-gradient(to right, rgba(0,6,18,0.97), rgba(0,10,21,0.70))",
      borderRight: "1px solid rgba(0,212,255,0.08)",
      display: "flex", flexDirection: "column", alignItems: "center",
      paddingTop: 18, gap: 2,
    }}>

      {/* Top arc decoration */}
      <div style={{ marginBottom: 12, opacity: 0.3 }}>
        <svg width="32" height="32" viewBox="0 0 32 32">
          <circle cx="16" cy="16" r="12" fill="none" stroke="#00d4ff" strokeWidth="0.6"
            strokeDasharray="6 4"
            style={{ animation: "arc-spin 14s linear infinite", transformOrigin: "16px 16px" }} />
          <circle cx="16" cy="16" r="6" fill="none" stroke="#00d4ff" strokeWidth="0.4"
            strokeDasharray="3 5"
            style={{ animation: "arc-spin-rev 9s linear infinite", transformOrigin: "16px 16px" }} />
          <circle cx="16" cy="16" r="2" fill="#00d4ff" opacity="0.6" />
        </svg>
      </div>

      {NAV_ITEMS.map(({ id, label, icon, hint }) => {
        const active = activePanel === id;
        return (
          <button
            key={id}
            title={hint}
            onClick={() => setPanel(id)}
            style={{
              width: 52, height: 52,
              background: active
                ? "linear-gradient(135deg, rgba(0,212,255,0.10), rgba(0,136,204,0.06))"
                : "transparent",
              border: `1px solid ${active ? "rgba(0,212,255,0.35)" : "transparent"}`,
              borderRadius: 4, cursor: "pointer",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 3,
              color: active ? "#00d4ff" : "rgba(0,212,255,0.28)",
              transition: "all 0.18s ease",
              boxShadow: active
                ? "0 0 18px rgba(0,212,255,0.10), inset 0 0 10px rgba(0,212,255,0.05)"
                : "none",
              fontFamily: "'Courier New', Courier, monospace",
              position: "relative",
            }}
            onMouseEnter={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(0,212,255,0.65)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(0,212,255,0.14)";
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,212,255,0.04)";
              }
            }}
            onMouseLeave={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(0,212,255,0.28)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }
            }}
          >
            {/* Active left-edge indicator bar */}
            {active && (
              <div style={{
                position: "absolute", left: 0, top: "20%", bottom: "20%",
                width: 2, borderRadius: "0 1px 1px 0",
                background: "linear-gradient(to bottom, transparent, #00d4ff, transparent)",
                boxShadow: "0 0 6px #00d4ff",
              }} />
            )}
            <HexNode active={active} />
            <span style={{ fontSize: 13, lineHeight: 1 }}>{icon}</span>
            <span style={{ fontSize: 6, letterSpacing: 2 }}>{label}</span>
          </button>
        );
      })}

      {/* Bottom fade line */}
      <div style={{
        position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
        width: 1, height: 100,
        background: "linear-gradient(to bottom, rgba(0,212,255,0.18), transparent)",
      }} />

      {/* Data stream dots */}
      <div style={{
        position: "absolute", bottom: 20, left: "50%", transform: "translateX(-50%)",
        display: "flex", flexDirection: "column", alignItems: "center", gap: 5,
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 2, height: 2, borderRadius: "50%",
            background: "rgba(0,212,255,0.4)",
            animation: `pulse-dot 1.8s ease-in-out ${i * 0.3}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}

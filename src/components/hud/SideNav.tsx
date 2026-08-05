import { useTStore, type ActivePanel } from "../../store";

interface NavItem {
  id:    ActivePanel;
  label: string;
  code:  string;
  hint:  string;
  icon:  string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "chat",     label: "CORE",    code: "01", hint: "Superintelligence Control Console", icon: "❖" },
  { id: "network",  label: "INTEL",   code: "02", hint: "Network & Threat Intelligence",     icon: "⚡" },
  { id: "hardware", label: "HW SYS",  code: "03", hint: "Hardware Telemetry & Control",      icon: "⌁" },
  { id: "devices",  label: "DEVICES", code: "04", hint: "Device Screen Mirroring",            icon: "⬡" },
  { id: "guardian", label: "GUARDIAN",code: "05", hint: "Defensive Cyber Suite",             icon: "🛡" },
  { id: "modules",  label: "MODULES", code: "06", hint: "Future Modules Hub & Vision",       icon: "☤" },
  { id: "settings", label: "CONFIG",  code: "07", hint: "System Config & Memory Store",       icon: "⚙" },
];

export function SideNav() {
  const { activePanel, setPanel } = useTStore();

  return (
    <div style={{
      position: "fixed", top: 54, left: 0, bottom: 0,
      width: 68, zIndex: 40,
      background: "linear-gradient(to right, rgba(5,5,8,0.98), rgba(12,8,16,0.85))",
      borderRight: "1px solid rgba(255,0,51,0.20)",
      display: "flex", flexDirection: "column", alignItems: "center",
      paddingTop: 20, gap: 6,
      backdropFilter: "blur(12px)",
    }}>

      {/* Top Spinning Geometry emblem */}
      <div style={{ marginBottom: 12, opacity: 0.7 }}>
        <svg width="28" height="28" viewBox="0 0 32 32">
          <circle cx="16" cy="16" r="13" fill="none" stroke="#ff0033" strokeWidth="0.8"
            strokeDasharray="8 4"
            style={{ animation: "ring-spin 12s linear infinite", transformOrigin: "16px 16px" }} />
          <circle cx="16" cy="16" r="7" fill="none" stroke="#ffffff" strokeWidth="0.5"
            strokeDasharray="4 4"
            style={{ animation: "ring-spin-rev 8s linear infinite", transformOrigin: "16px 16px" }} />
          <circle cx="16" cy="16" r="2" fill="#ff0033" />
        </svg>
      </div>

      {/* Navigation Buttons */}
      {NAV_ITEMS.map(({ id, label, code, hint, icon }) => {
        const active = activePanel === id;
        return (
          <button
            key={id}
            title={hint}
            onClick={() => setPanel(id)}
            style={{
              width: 56, height: 54,
              background: active
                ? "linear-gradient(135deg, rgba(255,0,51,0.22), rgba(128,0,22,0.12))"
                : "transparent",
              border: `1px solid ${active ? "#ff0033" : "transparent"}`,
              borderRadius: 2, cursor: "pointer",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 3,
              color: active ? "#ffffff" : "rgba(160,170,176,0.5)",
              transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
              boxShadow: active
                ? "0 0 16px rgba(255,0,51,0.35), inset 0 0 8px rgba(255,0,51,0.2)"
                : "none",
              fontFamily: "var(--font-mono)",
              position: "relative",
            }}
            onMouseEnter={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "#ffffff";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,0,51,0.4)";
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,0,51,0.08)";
              }
            }}
            onMouseLeave={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(160,170,176,0.5)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }
            }}
          >
            {/* Active Left-Edge Illuminator */}
            {active && (
              <div style={{
                position: "absolute", left: -1, top: 0, bottom: 0,
                width: 3,
                background: "linear-gradient(to bottom, #ff3355, #ff0033, #800016)",
                boxShadow: "0 0 8px #ff0033",
              }} />
            )}
            <span style={{ fontSize: 15, lineHeight: 1 }}>{icon}</span>
            <span style={{ fontSize: 7, letterSpacing: 2, fontWeight: 700 }}>{label}</span>
            <span style={{ fontSize: 6, opacity: 0.4 }}>{code}</span>
          </button>
        );
      })}

      {/* Vertical Status Line */}
      <div style={{
        position: "absolute", bottom: 20, left: "50%", transform: "translateX(-50%)",
        display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 2, height: 2, borderRadius: "50%",
            background: "#ff0033",
            animation: `energy-pulse 1.8s ease-in-out ${i * 0.3}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}

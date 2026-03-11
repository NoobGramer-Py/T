import { useTStore, type ActivePanel } from "../../store";

interface NavItem {
  id:    ActivePanel;
  label: string;
  icon:  string;
  hint:  string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "chat",     label: "CORE",  icon: "◎", hint: "AI Interface"   },
  { id: "security", label: "SEC",   icon: "⬡", hint: "Cyber Security" },
  { id: "system",   label: "SYS",   icon: "⊞", hint: "System Control" },
  { id: "network",  label: "NET",   icon: "⊹", hint: "Network Intel"  },
  { id: "settings", label: "CFG",   icon: "⚙", hint: "Config & Memory"},
];

export function SideNav() {
  const { activePanel, setPanel } = useTStore();

  return (
    <div style={{
      position: "fixed", top: 52, left: 0, bottom: 0,
      width: 64, zIndex: 40,
      background: "linear-gradient(to right, rgba(0,4,9,0.98), rgba(0,4,9,0.5))",
      borderRight: "1px solid rgba(255,179,0,0.08)",
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "20px 0", gap: 4,
    }}>
      {NAV_ITEMS.map(({ id, label, icon, hint }) => {
        const active = activePanel === id;
        return (
          <button
            key={id}
            title={hint}
            onClick={() => setPanel(id)}
            style={{
              width: 48, height: 48,
              background: active ? "rgba(255,179,0,0.08)" : "transparent",
              border: `1px solid ${active ? "rgba(255,179,0,0.35)" : "transparent"}`,
              borderRadius: 4, cursor: "pointer",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 2,
              color: active ? "#ffb300" : "rgba(255,179,0,0.3)",
              transition: "all 0.2s ease",
              boxShadow: active ? "0 0 16px rgba(255,179,0,0.12), inset 0 0 8px rgba(255,179,0,0.04)" : "none",
              fontFamily: "'Courier New', Courier, monospace",
            }}
            onMouseEnter={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,179,0,0.65)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,179,0,0.15)";
              }
            }}
            onMouseLeave={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,179,0,0.3)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
              }
            }}
          >
            <span style={{ fontSize: 14 }}>{icon}</span>
            <span style={{ fontSize: 6, letterSpacing: 2 }}>{label}</span>
          </button>
        );
      })}

      <div style={{
        position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
        width: 1, height: 120,
        background: "linear-gradient(to bottom, rgba(255,179,0,0.2), transparent)",
      }} />
    </div>
  );
}

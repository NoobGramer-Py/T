import { useTStore } from "./store";
import { useSystemStats } from "./hooks/useSystemStats";
import { useMemoryBoot } from "./hooks/useMemory";
import { useBrainConnection, useBrainProfileSync } from "./hooks/useBridge";
import { TopBar } from "./components/hud/TopBar";
import { SideNav } from "./components/hud/SideNav";
import { ChatPanel } from "./components/chat/ChatPanel";
import { SecurityPanel } from "./components/security/SecurityPanel";
import { SystemPanel } from "./components/system/SystemPanel";
import { NetworkPanel } from "./components/network/NetworkPanel";
import { SettingsPanel } from "./components/settings/SettingsPanel";

export default function App() {
  const activePanel = useTStore((s) => s.activePanel);

  // Global hooks — run once at app level
  useSystemStats(2000);
  useMemoryBoot();
  useBrainConnection();
  useBrainProfileSync();

  return (
    <div
      className="scanline-overlay"
      style={{
        width: "100vw", height: "100vh",
        background: "radial-gradient(ellipse at 50% 50%, #020a14 0%, #000409 100%)",
        overflow: "hidden", position: "relative",
      }}
    >
      {/* CRT scanline grid */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 1, pointerEvents: "none",
        background: "repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(255,179,0,0.008) 3px, rgba(255,179,0,0.008) 4px)",
      }} />

      {/* Radial vignette */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 2, pointerEvents: "none",
        background: "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%)",
      }} />

      <TopBar />
      <SideNav />

      {/* Main content */}
      <div style={{
        position: "fixed",
        top: 52, left: 64, right: 0, bottom: 0,
        zIndex: 10, overflow: "hidden",
      }}>
        {activePanel === "chat"     && <ChatPanel />}
        {activePanel === "security" && <SecurityPanel />}
        {activePanel === "system"   && <SystemPanel />}
        {activePanel === "network"  && <NetworkPanel />}
        {activePanel === "settings" && <SettingsPanel />}
      </div>
    </div>
  );
}

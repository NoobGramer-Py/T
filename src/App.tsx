import { useTStore } from "./store";
import { useSystemStats } from "./hooks/useSystemStats";
import { useMemoryBoot } from "./hooks/useMemory";
import { useBrainConnection, useBrainProfileSync, useBrainMemory } from "./hooks/useBridge";
import { TopBar } from "./components/hud/TopBar";
import { SideNav } from "./components/hud/SideNav";
import { ChatPanel } from "./components/chat/ChatPanel";
import { SecurityPanel } from "./components/security/SecurityPanel";
import { SystemPanel } from "./components/system/SystemPanel";
import { NetworkPanel } from "./components/network/NetworkPanel";
import { SettingsPanel } from "./components/settings/SettingsPanel";
import { HardwarePanel } from "./components/hardware/HardwarePanel";

export default function App() {
  const activePanel = useTStore((s) => s.activePanel);

  useSystemStats(2000);
  useMemoryBoot();
  useBrainConnection();
  useBrainProfileSync();
  useBrainMemory();

  return (
    <div
      className="scanline-overlay"
      style={{
        width: "100vw", height: "100vh",
        background: "radial-gradient(ellipse at 30% 40%, #001428 0%, #000810 45%, #000006 100%)",
        overflow: "hidden", position: "relative",
      }}
    >
      {/* CRT scanline raster */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 1, pointerEvents: "none",
        background: "repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(0,212,255,0.007) 3px, rgba(0,212,255,0.007) 4px)",
      }} />

      {/* Holographic vignette */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 2, pointerEvents: "none",
        background: "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,12,0.65) 100%)",
      }} />

      {/* Arc glow — top left */}
      <div style={{
        position: "fixed", top: -120, left: -80, zIndex: 0, pointerEvents: "none",
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(ellipse, rgba(0,136,204,0.06) 0%, transparent 70%)",
      }} />

      {/* Arc glow — bottom right */}
      <div style={{
        position: "fixed", bottom: -100, right: -60, zIndex: 0, pointerEvents: "none",
        width: 350, height: 350, borderRadius: "50%",
        background: "radial-gradient(ellipse, rgba(0,212,255,0.04) 0%, transparent 70%)",
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
        {activePanel === "hardware" && <HardwarePanel />}
        {activePanel === "settings" && <SettingsPanel />}
      </div>
    </div>
  );
}

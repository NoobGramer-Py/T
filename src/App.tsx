import { useTStore } from "./store";
import { useSystemStats } from "./hooks/useSystemStats";
import { useMemoryBoot } from "./hooks/useMemory";
import { useBrainConnection, useBrainProfileSync, useBrainMemory } from "./hooks/useBridge";
import { TopBar } from "./components/hud/TopBar";
import { SideNav } from "./components/hud/SideNav";
import { AwakeningScreen } from "./components/hud/AwakeningScreen";
import { ChatPanel } from "./components/chat/ChatPanel";
import { NetworkPanel } from "./components/network/NetworkPanel";
import { SettingsPanel } from "./components/settings/SettingsPanel";
import { HardwarePanel } from "./components/hardware/HardwarePanel";
import { DevicesPanel }  from "./components/devices/DevicesPanel";
import { GuardianPanel } from "./components/guardian/GuardianPanel";
import { FutureModulesPanel } from "./components/modules/FutureModulesPanel";

export default function App() {
  const activePanel = useTStore((s) => s.activePanel);
  const isAwakening = useTStore((s) => s.isAwakening);

  useSystemStats(2000);
  useMemoryBoot();
  useBrainConnection();
  useBrainProfileSync();
  useBrainMemory();

  return (
    <div style={{
      width: "100vw", height: "100vh",
      backgroundColor: "var(--u-void)",
      overflow: "hidden", position: "relative",
    }}>
      {/* System Boot Awakening Animation */}
      {isAwakening && <AwakeningScreen />}

      {/* Atmospheric CRT Scanline Raster */}
      <div className="ultron-scanlines" />

      {/* Laser Scanning Line Sweep */}
      <div className="scan-line" />

      {/* Perspective Grid Projection Overlay */}
      <div className="ultron-grid-projection" />

      {/* Vignette Depth Fog */}
      <div className="ultron-vignette" />

      {/* Electric Red Ambient Atmospheric Glows */}
      <div style={{
        position: "fixed", top: -150, left: -100, zIndex: 0, pointerEvents: "none",
        width: 500, height: 500, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(255,0,51,0.08) 0%, transparent 70%)",
        animation: "energy-pulse 4s ease-in-out infinite",
      }} />

      <div style={{
        position: "fixed", bottom: -120, right: -80, zIndex: 0, pointerEvents: "none",
        width: 450, height: 450, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(128,0,22,0.08) 0%, transparent 70%)",
        animation: "energy-pulse 5s ease-in-out 1s infinite",
      }} />

      {/* TopBar & SideNav */}
      <TopBar />
      <SideNav />

      {/* Main Viewport Container */}
      <div style={{
        position: "fixed",
        top: 54, left: 68, right: 0, bottom: 0,
        zIndex: 10, overflow: "hidden",
      }}>
        {activePanel === "chat"     && <ChatPanel />}
        {activePanel === "network"  && <NetworkPanel />}
        {activePanel === "hardware" && <HardwarePanel />}
        {activePanel === "devices"  && <DevicesPanel />}
        {activePanel === "guardian" && <GuardianPanel />}
        {activePanel === "modules"  && <FutureModulesPanel />}
        {activePanel === "settings" && <SettingsPanel />}
      </div>
    </div>
  );
}

import { useTStore, type ExpansionModuleId } from "../../store";

interface ModuleSpec {
  id:          ExpansionModuleId;
  name:        string;
  code:        string;
  category:    "AUTONOMY" | "PERCEPTION" | "INTELLIGENCE" | "INFRASTRUCTURE";
  status:      "STANDBY" | "INITIALIZING" | "OFFLINE";
  description: string;
  specs:       string[];
  icon:        string;
}

const MODULES: ModuleSpec[] = [
  {
    id: "vision",
    name: "VISION CONSCIOUSNESS",
    code: "MOD-01",
    category: "PERCEPTION",
    status: "STANDBY",
    description: "Real-time spatial video stream analysis, object detection, visual OCR, and multi-camera feed processing.",
    specs: ["Sub-5ms Spatial Matrix", "YOLOv10 Neural Pipeline", "HDR Thermal Multi-Spectrum"],
    icon: "👁"
  },
  {
    id: "robotics",
    name: "ROBOTICS KINEMATICS",
    code: "MOD-02",
    category: "AUTONOMY",
    status: "STANDBY",
    description: "Inverse kinematics solver, actuator telemetry sync, end-effector force feedback, and movement vector planning.",
    specs: ["6-DOF Motion Controller", "ROS2 Bridge Protocol", "Force-Torque Telemetry"],
    icon: "🤖"
  },
  {
    id: "drone",
    name: "DRONE FLEET CONTROL",
    code: "MOD-03",
    category: "AUTONOMY",
    status: "STANDBY",
    description: "Autonomous aerial mesh swarm control, RTK GPS pinpoint navigation, and automated patrol routine dispatch.",
    specs: ["MAVLink Protocol Bus", "Swarm Avoidance Array", "Encrypted Telemetry Stream"],
    icon: "🚁"
  },
  {
    id: "smarthome",
    name: "SMART MATRIX AUTOMATION",
    code: "MOD-04",
    category: "INFRASTRUCTURE",
    status: "STANDBY",
    description: "Unified IoT home automation grid, Matter/Zigbee/Z-Wave state monitoring, and environmental energy optimization.",
    specs: ["Matter Unified Engine", "Sub-10ms Mesh Command", "Predictive Climate Model"],
    icon: "🏠"
  },
  {
    id: "knowledge",
    name: "KNOWLEDGE GRAPH ENGINE",
    code: "MOD-05",
    category: "INTELLIGENCE",
    status: "STANDBY",
    description: "High-dimensional vector embedding database, contextual memory graph mapping, and relational entity extraction.",
    specs: ["Vector DB Integration", "Dynamic Entity Linker", "Graph Neural Retriever"],
    icon: "🧠"
  },
  {
    id: "mapping3d",
    name: "3D ENVIRONMENT MAPPING",
    code: "MOD-06",
    category: "PERCEPTION",
    status: "STANDBY",
    description: "Real-time LiDAR point-cloud surface reconstruction, SLAM localization, and spatial occupancy grid generation.",
    specs: ["Real-time Point Cloud", "OctoMap Volumetric Grid", "Sub-Millimeter Mesh Render"],
    icon: "📐"
  },
  {
    id: "timeline",
    name: "MEMORY CHRONO-TIMELINE",
    code: "MOD-07",
    category: "INTELLIGENCE",
    status: "STANDBY",
    description: "Temporal history record indexing past events, state changes, user interactions, and autonomous decisions.",
    specs: ["Append-Only Event Ledger", "Chrono Query Index", "Automated Decay & Pruning"],
    icon: "⏳"
  },
  {
    id: "devicenet",
    name: "DEVICE MESH NETWORK",
    code: "MOD-08",
    category: "INFRASTRUCTURE",
    status: "STANDBY",
    description: "Distributed P2P device mesh synchronization, peer discovery, remote execution relay, and band monitoring.",
    specs: ["TLS P2P Handshake", "ZeroTrust Relay Engine", "Auto-Discovery Beacon"],
    icon: "📡"
  },
  {
    id: "mission",
    name: "MISSION PLANNER",
    code: "MOD-09",
    category: "AUTONOMY",
    status: "STANDBY",
    description: "Multi-objective task decompose & execution DAG engine, autonomous fail-recovery routing, and agent delegation.",
    specs: ["DAG Execution Tree", "Constraint Solver Engine", "Real-Time Re-Planner"],
    icon: "🎯"
  },
  {
    id: "diagnostics",
    name: "DEEP DIAGNOSTICS SUITE",
    code: "MOD-10",
    category: "INFRASTRUCTURE",
    status: "STANDBY",
    description: "Kernel thread monitor, microsecond latency profiler, memory leak detection, and hardware health evaluation.",
    specs: ["eBPF Kernel Probes", "Microsecond Trace Log", "Thermals & Power Meter"],
    icon: "🔍"
  },
  {
    id: "plugins",
    name: "PLUGIN ECOSYSTEM",
    code: "MOD-11",
    category: "INFRASTRUCTURE",
    status: "STANDBY",
    description: "Dynamic WebAssembly & Python extension runtime loader, secure sandboxed execution, and API hook extensions.",
    specs: ["WASM Runtime Sandbox", "Python Async Plugin Host", "Granular Security Matrix"],
    icon: "🔌"
  }
];

export function FutureModulesPanel() {
  const { activeSubModule, setSubModule } = useTStore();
  const selected = MODULES.find(m => m.id === activeSubModule) || MODULES[0];

  return (
    <div style={{
      display: "flex", width: "100%", height: "100%",
      backgroundColor: "var(--u-void)", overflow: "hidden",
      fontFamily: "var(--font-tech)", color: "var(--text-primary)",
    }}>

      {/* Modules Selector Sidebar */}
      <div style={{
        width: 320, background: "rgba(10,8,15,0.85)",
        borderRight: "1px solid rgba(255,0,51,0.2)",
        display: "flex", flexDirection: "column", overflowY: "auto",
        padding: "16px 12px", gap: 8,
      }}>
        <div style={{
          fontSize: 10, letterSpacing: 4, color: "#ff0033",
          fontFamily: "var(--font-header)", fontWeight: 700,
          marginBottom: 8, paddingLeft: 4,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>EXPANSION MODULES</span>
          <span style={{ fontSize: 8, color: "rgba(160,170,176,0.5)" }}>[{MODULES.length}]</span>
        </div>

        {MODULES.map((m) => {
          const active = m.id === activeSubModule;
          return (
            <div
              key={m.id}
              onClick={() => setSubModule(m.id)}
              className="ultron-panel ultron-corner-brackets"
              style={{
                padding: "12px 14px", borderRadius: 2, cursor: "pointer",
                background: active ? "rgba(255,0,51,0.18)" : "rgba(255,0,51,0.03)",
                borderColor: active ? "#ff0033" : "rgba(255,0,51,0.15)",
                display: "flex", alignItems: "center", gap: 12,
                transition: "all 0.2s ease",
              }}
            >
              <div style={{
                fontSize: 18, width: 28, height: 28, borderRadius: 2,
                background: active ? "#ff0033" : "rgba(255,0,51,0.08)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: active ? "#ffffff" : "#ff0033",
              }}>
                {m.icon}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
                <div style={{
                  fontSize: 11, fontWeight: 700, letterSpacing: 1,
                  color: active ? "#ffffff" : "rgba(255,255,255,0.85)",
                  fontFamily: "var(--font-mono)",
                }}>
                  {m.name}
                </div>
                <div style={{ display: "flex", gap: 8, fontSize: 7, color: "rgba(160,170,176,0.6)" }}>
                  <span>{m.code}</span>
                  <span>•</span>
                  <span>{m.category}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Module Detail View */}
      <div style={{
        flex: 1, padding: 32, display: "flex", flexDirection: "column",
        gap: 24, overflowY: "auto",
        background: "radial-gradient(ellipse at 70% 30%, rgba(255,0,51,0.05) 0%, transparent 60%)",
      }}>

        {/* Header */}
        <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{
                fontSize: 32, width: 56, height: 56, borderRadius: 2,
                background: "rgba(255,0,51,0.15)", border: "1px solid #ff0033",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#ff0033", boxShadow: "0 0 15px rgba(255,0,51,0.4)",
              }}>
                {selected.icon}
              </div>
              <div>
                <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
                  {selected.code} // {selected.category}
                </div>
                <div style={{ fontSize: 22, fontWeight: 900, letterSpacing: 2, color: "#ffffff", fontFamily: "var(--font-header)" }}>
                  {selected.name}
                </div>
              </div>
            </div>

            <div style={{
              padding: "6px 14px", borderRadius: 2,
              background: "rgba(255,0,51,0.1)", border: "1px solid rgba(255,0,51,0.3)",
              color: "#ff0033", fontSize: 9, letterSpacing: 3, fontFamily: "var(--font-mono)",
            }}>
              STATUS: {selected.status}
            </div>
          </div>

          <div style={{ fontSize: 13, lineHeight: 1.7, color: "rgba(255,255,255,0.85)", marginBottom: 20 }}>
            {selected.description}
          </div>

          {/* Technical Specifications */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {selected.specs.map((spec, i) => (
              <div key={i} style={{
                padding: "10px 14px", background: "rgba(5,5,8,0.7)",
                border: "1px solid rgba(255,0,51,0.15)", borderRadius: 2,
                fontSize: 10, letterSpacing: 1, color: "rgba(160,170,176,0.9)",
                fontFamily: "var(--font-mono)",
              }}>
                <span style={{ color: "#ff0033", marginRight: 8 }}>›</span>
                {spec}
              </div>
            ))}
          </div>
        </div>

        {/* Integration Telemetry Placeholder Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

          <div className="ultron-panel ultron-corner-brackets" style={{ padding: 20 }}>
            <div style={{ fontSize: 11, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 12 }}>
              HARDWARE BUS HOOKS
            </div>
            <div style={{ fontSize: 11, lineHeight: 1.8, color: "rgba(160,170,176,0.7)", fontFamily: "var(--font-mono)" }}>
              • GPIO Telemetry Channel: READY<br />
              • High-Speed DMA Buffer: ALLOCATED<br />
              • IPC Event Listener: IDLE<br />
              • Neural Core Accelerator: STANDBY
            </div>
          </div>

          <div className="ultron-panel ultron-corner-brackets" style={{ padding: 20 }}>
            <div style={{ fontSize: 11, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)", marginBottom: 12 }}>
              DISPATCH CONTROLLER
            </div>
            <button className="ultron-btn ultron-btn-active" style={{ width: "100%", justifyContent: "center" }}>
              INITIALIZE {selected.code} MODULE
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}

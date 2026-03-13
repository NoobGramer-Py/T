import { useState, useEffect } from "react";
import {
  useHardware,
  type HardwareDevice,
  type HardwareConfirmRequest,
} from "../../hooks/useBridge";

// ─── Shared style helpers ─────────────────────────────────────────────────────

const S = {
  label: {
    fontSize: 7,
    letterSpacing: 4,
    color: "rgba(0,212,255,0.4)",
    marginBottom: 5,
  } as React.CSSProperties,

  input: {
    background: "rgba(0,212,255,0.03)",
    border: "1px solid rgba(0,212,255,0.15)",
    borderRadius: 3,
    padding: "6px 10px",
    color: "rgba(160,244,255,0.9)",
    fontSize: 11,
    fontFamily: "inherit",
    outline: "none",
    caretColor: "#00d4ff",
    width: "100%",
  } as React.CSSProperties,

  select: {
    background: "rgba(0,212,255,0.03)",
    border: "1px solid rgba(0,212,255,0.15)",
    borderRadius: 3,
    padding: "6px 10px",
    color: "rgba(160,244,255,0.9)",
    fontSize: 11,
    fontFamily: "inherit",
    outline: "none",
    cursor: "pointer",
    width: "100%",
  } as React.CSSProperties,

  btn: (accent = "#00d4ff", active = false): React.CSSProperties => ({
    padding: "5px 14px",
    fontSize: 8,
    letterSpacing: 2,
    background: active ? `rgba(${accent === "#00ff88" ? "0,255,136" : "255,179,0"},0.12)` : "rgba(0,212,255,0.06)",
    border: `1px solid ${active ? accent : "rgba(0,212,255,0.25)"}`,
    color: active ? accent : "#00d4ff",
    borderRadius: 3,
    cursor: "pointer",
    fontFamily: "inherit",
    whiteSpace: "nowrap" as const,
  }),

  sectionHeader: {
    fontSize: 8,
    letterSpacing: 5,
    color: "rgba(0,212,255,0.35)",
    borderBottom: "1px solid rgba(0,212,255,0.07)",
    paddingBottom: 8,
    marginBottom: 14,
  } as React.CSSProperties,
};

function focusBorder(e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) {
  e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)";
}
function blurBorder(e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) {
  e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)";
}

// ─── Confirmation modal ───────────────────────────────────────────────────────

function ConfirmModal({
  req,
  onConfirm,
}: {
  req: HardwareConfirmRequest;
  onConfirm: (confirmed: boolean) => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 200,
        background: "rgba(0,0,0,0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "#030d18",
          border: "1px solid rgba(0,212,255,0.3)",
          borderRadius: 6,
          padding: "28px 32px",
          maxWidth: 420,
          width: "90%",
        }}
      >
        <div style={{ fontSize: 8, letterSpacing: 5, color: "rgba(0,212,255,0.5)", marginBottom: 16 }}>
          HARDWARE · CONFIRMATION REQUIRED
        </div>
        <div style={{ fontSize: 13, color: "#a0f4ff", marginBottom: 8 }}>
          {req.detail}
        </div>
        <div style={{ fontSize: 10, color: "rgba(0,212,255,0.55)", marginBottom: 24, lineHeight: 1.6 }}>
          Device: <span style={{ color: "#00d4ff" }}>{req.device_id}</span>
          <br />
          {req.message}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button onClick={() => onConfirm(false)} style={S.btn("#ff4400")}>
            CANCEL
          </button>
          <button
            onClick={() => onConfirm(true)}
            style={{ ...S.btn("#00ff88", true), borderColor: "rgba(0,255,136,0.5)" }}
          >
            CONFIRM
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Device card ─────────────────────────────────────────────────────────────

function DeviceCard({
  device,
  onConnect,
  onSend,
}: {
  device:    HardwareDevice;
  onConnect: (id: string) => void;
  onSend:    (id: string, action: string, params: Record<string, string | number>) => void;
}) {
  const [pin,   setPin]   = useState("13");
  const [state, setState] = useState<"HIGH" | "LOW">("HIGH");
  const [apin,  setApin]  = useState("A0");
  const [dpin,  setDpin]  = useState("7");
  const [topic, setTopic] = useState(device.type === "mqtt" ? device.capabilities[0] ?? "" : "");
  const [payload, setPayload] = useState("ON");

  const cap = device.capabilities;

  return (
    <div
      style={{
        background: "rgba(0,212,255,0.02)",
        border: `1px solid ${device.connected ? "rgba(0,255,136,0.2)" : "rgba(0,212,255,0.1)"}`,
        borderRadius: 5,
        padding: "14px 16px",
        marginBottom: 12,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: device.connected ? "#00ff88" : "rgba(0,212,255,0.3)",
            boxShadow: device.connected ? "0 0 6px #00ff88" : "none",
            flexShrink: 0,
          }}
        />
        <span style={{ color: "#a0f4ff", fontSize: 12, fontWeight: 600 }}>{device.id}</span>
        <span
          style={{
            fontSize: 7,
            letterSpacing: 3,
            color: "rgba(0,212,255,0.4)",
            border: "1px solid rgba(0,212,255,0.15)",
            borderRadius: 2,
            padding: "1px 6px",
          }}
        >
          {device.type.toUpperCase()}
        </span>
        <span style={{ flex: 1, fontSize: 9, color: "rgba(0,212,255,0.35)", textAlign: "right" }}>
          {device.description}
        </span>
      </div>

      {/* Capabilities badges */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
        {cap.map((c) => (
          <span
            key={c}
            style={{
              fontSize: 7,
              letterSpacing: 2,
              color: "rgba(0,212,255,0.5)",
              border: "1px solid rgba(0,212,255,0.12)",
              borderRadius: 2,
              padding: "1px 5px",
            }}
          >
            {c}
          </span>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        {/* Connect / Ping */}
        {!device.connected ? (
          <button onClick={() => onConnect(device.id)} style={S.btn()}>
            CONNECT
          </button>
        ) : (
          <button
            onClick={() => onSend(device.id, "ping", {})}
            style={S.btn("#00ff88", true)}
          >
            PING
          </button>
        )}

        {/* Digital write (serial / gpio) */}
        {(cap.includes("digital_write") || device.type === "gpio") && (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <div>
              <div style={S.label}>PIN</div>
              <input
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                style={{ ...S.input, width: 48 }}
                onFocus={focusBorder}
                onBlur={blurBorder}
              />
            </div>
            <div>
              <div style={S.label}>STATE</div>
              <select
                value={state}
                onChange={(e) => setState(e.target.value as "HIGH" | "LOW")}
                style={{ ...S.select, width: 70 }}
                onFocus={focusBorder}
                onBlur={blurBorder}
              >
                <option style={{ background: "#000" }}>HIGH</option>
                <option style={{ background: "#000" }}>LOW</option>
              </select>
            </div>
            <div style={{ paddingTop: 18 }}>
              <button
                onClick={() => onSend(device.id, "digital_write", { pin, state })}
                style={S.btn()}
              >
                WRITE
              </button>
            </div>
          </div>
        )}

        {/* Digital read */}
        {(cap.includes("digital_read") || device.type === "gpio") && (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <div>
              <div style={S.label}>DREAD PIN</div>
              <input
                value={dpin}
                onChange={(e) => setDpin(e.target.value)}
                style={{ ...S.input, width: 48 }}
                onFocus={focusBorder}
                onBlur={blurBorder}
              />
            </div>
            <div style={{ paddingTop: 18 }}>
              <button
                onClick={() => onSend(device.id, "digital_read", { pin: dpin })}
                style={S.btn()}
              >
                READ
              </button>
            </div>
          </div>
        )}

        {/* Analog read */}
        {cap.includes("analog_read") && (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <div>
              <div style={S.label}>AREAD</div>
              <input
                value={apin}
                onChange={(e) => setApin(e.target.value)}
                style={{ ...S.input, width: 52 }}
                onFocus={focusBorder}
                onBlur={blurBorder}
              />
            </div>
            <div style={{ paddingTop: 18 }}>
              <button
                onClick={() => onSend(device.id, "analog_read", { pin: apin })}
                style={S.btn()}
              >
                READ
              </button>
            </div>
          </div>
        )}

        {/* DHT read */}
        {cap.includes("dht_read") && (
          <button
            onClick={() => onSend(device.id, "dht", { pin: 2 })}
            style={S.btn()}
          >
            DHT TEMP
          </button>
        )}

        {/* MQTT publish */}
        {(cap.includes("publish") || device.type === "mqtt") && (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <div>
              <div style={S.label}>TOPIC</div>
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="home/device/set"
                style={{ ...S.input, width: 160 }}
                onFocus={focusBorder}
                onBlur={blurBorder}
              />
            </div>
            <div>
              <div style={S.label}>PAYLOAD</div>
              <input
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                style={{ ...S.input, width: 80 }}
                onFocus={focusBorder}
                onBlur={blurBorder}
              />
            </div>
            <div style={{ paddingTop: 18 }}>
              <button
                onClick={() => onSend(device.id, "publish", { topic, payload })}
                style={S.btn()}
              >
                PUBLISH
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Register device form ─────────────────────────────────────────────────────

function RegisterForm({ onRegister }: { onRegister: (cfg: Record<string, unknown>) => void }) {
  const [open,    setOpen]    = useState(false);
  const [devId,   setDevId]   = useState("");
  const [devType, setDevType] = useState<"serial" | "mqtt">("serial");
  const [port,    setPort]    = useState("COM3");
  const [baud,    setBaud]    = useState("9600");
  const [desc,    setDesc]    = useState("");
  const [broker,  setBroker]  = useState("192.168.1.100");
  const [mqttPort, setMqttPort] = useState("1883");
  const [topicPub, setTopicPub] = useState("");
  const [topicSub, setTopicSub] = useState("");

  const submit = () => {
    if (!devId.trim()) return;
    const cfg: Record<string, unknown> = {
      id:          devId.trim(),
      type:        devType,
      description: desc.trim(),
    };
    if (devType === "serial") {
      cfg.port         = port;
      cfg.baud         = parseInt(baud) || 9600;
      cfg.capabilities = ["digital_write", "digital_read", "analog_read", "pwm"];
    } else {
      cfg.broker       = broker;
      cfg.port_mqtt    = parseInt(mqttPort) || 1883;
      cfg.topic_pub    = topicPub;
      cfg.topic_sub    = topicSub;
      cfg.capabilities = ["publish", "subscribe"];
    }
    onRegister(cfg);
    setOpen(false);
    setDevId("");
    setDesc("");
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={S.btn()}>
        + ADD DEVICE
      </button>
    );
  }

  return (
    <div
      style={{
        background: "rgba(0,212,255,0.02)",
        border: "1px solid rgba(0,212,255,0.15)",
        borderRadius: 5,
        padding: "16px 18px",
        marginBottom: 16,
      }}
    >
      <div style={S.sectionHeader}>REGISTER NEW DEVICE</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
        <div>
          <div style={S.label}>DEVICE ID</div>
          <input value={devId} onChange={(e) => setDevId(e.target.value)} placeholder="arduino_uno"
            style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
        </div>
        <div>
          <div style={S.label}>TYPE</div>
          <select value={devType} onChange={(e) => setDevType(e.target.value as "serial" | "mqtt")}
            style={S.select} onFocus={focusBorder} onBlur={blurBorder}>
            <option value="serial" style={{ background: "#000" }}>Serial (Arduino)</option>
            <option value="mqtt"   style={{ background: "#000" }}>MQTT (Smart Home)</option>
          </select>
        </div>
      </div>

      <div style={{ marginBottom: 10 }}>
        <div style={S.label}>DESCRIPTION</div>
        <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Optional description"
          style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
      </div>

      {devType === "serial" ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
          <div>
            <div style={S.label}>PORT</div>
            <input value={port} onChange={(e) => setPort(e.target.value)} placeholder="COM3"
              style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
          </div>
          <div>
            <div style={S.label}>BAUD RATE</div>
            <input value={baud} onChange={(e) => setBaud(e.target.value)} placeholder="9600"
              style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
          </div>
        </div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
            <div>
              <div style={S.label}>BROKER IP</div>
              <input value={broker} onChange={(e) => setBroker(e.target.value)}
                placeholder="192.168.1.100" style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
            </div>
            <div>
              <div style={S.label}>PORT</div>
              <input value={mqttPort} onChange={(e) => setMqttPort(e.target.value)} placeholder="1883"
                style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
            <div>
              <div style={S.label}>TOPIC PUBLISH</div>
              <input value={topicPub} onChange={(e) => setTopicPub(e.target.value)}
                placeholder="home/device/set" style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
            </div>
            <div>
              <div style={S.label}>TOPIC SUBSCRIBE</div>
              <input value={topicSub} onChange={(e) => setTopicSub(e.target.value)}
                placeholder="home/device/state" style={S.input} onFocus={focusBorder} onBlur={blurBorder} />
            </div>
          </div>
        </>
      )}

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
        <button onClick={() => setOpen(false)} style={S.btn("#ff4400")}>CANCEL</button>
        <button onClick={submit} style={{ ...S.btn("#00ff88", true), borderColor: "rgba(0,255,136,0.4)" }}>
          REGISTER
        </button>
      </div>
    </div>
  );
}

// ─── Result log ───────────────────────────────────────────────────────────────

function ResultLog({ results }: { results: { device_id: string; action: string; result: string; ts: number }[] }) {
  if (results.length === 0) return null;
  return (
    <div style={{ marginTop: 20 }}>
      <div style={S.sectionHeader}>COMMAND LOG</div>
      <div
        style={{
          maxHeight: 220,
          overflowY: "auto",
          fontFamily: "monospace",
        }}
      >
        {results.map((r) => {
          const time = new Date(r.ts).toLocaleTimeString("en-US", {
            hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
          });
          const isError = r.result.startsWith("[ERROR]");
          return (
            <div
              key={r.ts}
              style={{
                display: "flex",
                gap: 10,
                padding: "4px 10px",
                marginBottom: 2,
                background: isError ? "rgba(255,68,0,0.05)" : "rgba(0,212,255,0.02)",
                border: `1px solid ${isError ? "rgba(255,68,0,0.15)" : "rgba(0,212,255,0.06)"}`,
                borderRadius: 3,
                fontSize: 10,
              }}
            >
              <span style={{ color: "rgba(0,212,255,0.3)", minWidth: 70 }}>{time}</span>
              <span style={{ color: "rgba(0,212,255,0.5)", minWidth: 90 }}>{r.device_id}</span>
              <span style={{ color: "rgba(0,212,255,0.35)", minWidth: 70 }}>{r.action}</span>
              <span style={{ color: isError ? "#ff4400" : "#a0f4ff", flex: 1 }}>{r.result}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Serial port scanner ──────────────────────────────────────────────────────

function SerialPortList({
  ports,
  onDiscover,
}: {
  ports:      { port: string; description: string }[];
  onDiscover: () => void;
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
        <div style={S.sectionHeader}>SERIAL PORTS</div>
        <button onClick={onDiscover} style={{ ...S.btn(), marginBottom: 8 }}>SCAN</button>
      </div>
      {ports.length === 0 ? (
        <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic" }}>
          Press SCAN to detect available serial ports.
        </div>
      ) : (
        ports.map((p) => (
          <div
            key={p.port}
            style={{
              display: "flex",
              gap: 12,
              padding: "5px 10px",
              marginBottom: 3,
              background: "rgba(0,212,255,0.02)",
              border: "1px solid rgba(0,212,255,0.07)",
              borderRadius: 3,
            }}
          >
            <span style={{ color: "#00d4ff", fontSize: 10, minWidth: 60 }}>{p.port}</span>
            <span style={{ color: "rgba(0,212,255,0.5)", fontSize: 10 }}>{p.description}</span>
          </div>
        ))
      )}
    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────────────

export function HardwarePanel() {
  const {
    devices, results, error, confirmRequest, serialPorts,
    sendCommand, listDevices, discoverPorts, connectDevice,
    registerDevice, confirmAction, clearError,
  } = useHardware();

  // Load device list on mount
  useEffect(() => {
    listDevices();
  }, [listDevices]);

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "24px 28px" }}>
      {/* Confirmation modal */}
      {confirmRequest && (
        <ConfirmModal req={confirmRequest} onConfirm={confirmAction} />
      )}

      {/* Title */}
      <div style={{
        fontSize: 8, letterSpacing: 6, marginBottom: 24,
        color: "rgba(0,212,255,0.35)",
        borderBottom: "1px solid rgba(0,212,255,0.06)", paddingBottom: 12,
      }}>
        T · HARDWARE CONTROL
      </div>

      {/* Error bar */}
      {error && (
        <div style={{
          background: "rgba(255,68,0,0.07)",
          border: "1px solid rgba(255,68,0,0.25)",
          borderRadius: 4, padding: "8px 14px",
          marginBottom: 16,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ color: "#ff4422", fontSize: 10 }}>{error}</span>
          <button onClick={clearError} style={{
            background: "transparent", border: "none",
            color: "rgba(255,68,0,0.6)", cursor: "pointer", fontSize: 12,
          }}>✕</button>
        </div>
      )}

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button onClick={listDevices} style={S.btn()}>REFRESH DEVICES</button>
      </div>

      {/* Serial port scanner */}
      <SerialPortList ports={serialPorts} onDiscover={discoverPorts} />

      {/* Register form */}
      <div style={{ marginBottom: 20 }}>
        <div style={S.sectionHeader}>REGISTERED DEVICES</div>
        <RegisterForm onRegister={registerDevice} />
      </div>

      {/* Device cards */}
      {devices.length === 0 ? (
        <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic", marginBottom: 20 }}>
          No devices registered. Add a device above, or edit{" "}
          <code style={{ color: "rgba(0,212,255,0.4)", fontSize: 9 }}>brain/config/hardware_devices.yaml</code>{" "}
          and restart the brain.
        </div>
      ) : (
        devices.map((d) => (
          <DeviceCard
            key={d.id}
            device={d}
            onConnect={(id) => connectDevice(id)}
            onSend={(id, action, params) => sendCommand(id, action, params)}
          />
        ))
      )}

      {/* Command log */}
      <ResultLog results={results} />
    </div>
  );
}

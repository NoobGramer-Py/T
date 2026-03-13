import { useState, useEffect } from "react";
import { setProfile as dbSetProfile, setMemory, getAllMemories, deleteMemory, addTask, getTasks, completeTask, deleteTask } from "../../lib/tauri";
import type { MemoryEntry, Task } from "../../lib/tauri";
import { useTStore } from "../../store";
import type { VoiceSettings } from "../../store";

function SectionHeader({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      marginBottom: 14, paddingBottom: 8,
      borderBottom: "1px solid rgba(0,212,255,0.08)",
    }}>
      <span style={{ fontSize: 14, color: "#00d4ff", textShadow: "0 0 8px #00d4ff" }}>{icon}</span>
      <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(0,212,255,0.6)" }}>{title}</span>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder = "" }: {
  label:       string;
  value:       string;
  onChange:    (v: string) => void;
  type?:       string;
  placeholder?: string;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.4)", marginBottom: 5 }}>{label}</div>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: "100%", background: "rgba(0,212,255,0.03)",
          border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3,
          padding: "7px 12px", color: "rgba(160,244,255,0.9)",
          fontSize: 11, fontFamily: "inherit", outline: "none",
          caretColor: "#00d4ff",
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
        onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
      />
    </div>
  );
}

// ─── Profile Section ──────────────────────────────────────────────────────────

function ProfileSection() {
  const { profile, setProfile } = useTStore();
  const [saved, setSaved] = useState(false);

  const save = async () => {
    try {
      await Promise.all([
        dbSetProfile("name",          profile.name),
        dbSetProfile("groqKey",       profile.groqKey),
        dbSetProfile("abuseipdbKey",  profile.abuseipdbKey),
        dbSetProfile("virusTotalKey", profile.virusTotalKey),
        dbSetProfile("hibpKey",       profile.hibpKey),
        dbSetProfile("timezone",      profile.timezone),
        dbSetProfile("notes",         profile.notes),
      ]);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* db not available in dev */ }
  };

  return (
    <div style={{ marginBottom: 32 }}>
      <SectionHeader title="USER PROFILE" icon="◎" />
      <Field label="YOUR NAME" value={profile.name} onChange={(v) => setProfile({ name: v })} placeholder="How T addresses you" />
      <Field label="GROQ API KEY" value={profile.groqKey} onChange={(v) => setProfile({ groqKey: v })} type="password" placeholder="gsk_..." />
      <Field label="ABUSEIPDB API KEY" value={profile.abuseipdbKey} onChange={(v) => setProfile({ abuseipdbKey: v })} type="password" placeholder="For IP reputation checks" />
      <Field label="VIRUSTOTAL API KEY" value={profile.virusTotalKey} onChange={(v) => setProfile({ virusTotalKey: v })} type="password" placeholder="For URL safety checks" />
      <Field label="HIBP API KEY" value={profile.hibpKey} onChange={(v) => setProfile({ hibpKey: v })} type="password" placeholder="haveibeenpwned.com — free key at haveibeenpwned.com/API/Key" />
      <Field label="TIMEZONE" value={profile.timezone} onChange={(v) => setProfile({ timezone: v })} placeholder="e.g. Asia/Karachi" />
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.4)", marginBottom: 5 }}>NOTES FOR T</div>
        <textarea
          value={profile.notes}
          onChange={(e) => setProfile({ notes: e.target.value })}
          placeholder="Anything T should always know about you..."
          rows={3}
          style={{
            width: "100%", resize: "vertical",
            background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)",
            borderRadius: 3, padding: "7px 12px", color: "rgba(160,244,255,0.9)",
            fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
        />
      </div>
      <button onClick={save} style={{
        padding: "6px 20px", fontSize: 8, letterSpacing: 3,
        background: saved ? "rgba(0,255,136,0.08)" : "rgba(0,212,255,0.08)",
        border: `1px solid ${saved ? "rgba(0,255,136,0.4)" : "rgba(0,212,255,0.3)"}`,
        color: saved ? "#00ff88" : "#00d4ff",
        borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        transition: "all 0.3s ease",
      }}>
        {saved ? "SAVED ✓" : "SAVE PROFILE"}
      </button>
    </div>
  );
}

// ─── Memory Section ───────────────────────────────────────────────────────────

function MemorySection() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [key, setKey]           = useState("");
  const [value, setValue]       = useState("");
  const [loading, setLoading]   = useState(false);

  const load = async () => {
    try { setMemories(await getAllMemories()); } catch { /* dev */ }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!key.trim() || !value.trim()) return;
    setLoading(true);
    try {
      await setMemory(key.trim(), value.trim());
      setKey(""); setValue("");
      await load();
    } finally { setLoading(false); }
  };

  const remove = async (k: string) => {
    try { await deleteMemory(k); await load(); } catch { /* dev */ }
  };

  return (
    <div style={{ marginBottom: 32 }}>
      <SectionHeader title="PERSISTENT MEMORY" icon="⬡" />
      <div style={{ fontSize: 9, color: "rgba(0,212,255,0.35)", marginBottom: 12, lineHeight: 1.6 }}>
        Facts T injects into every conversation. Stored locally in SQLite.
      </div>

      {/* Add memory */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="key (e.g. stack)"
          style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
        />
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="value"
          onKeyDown={(e) => e.key === "Enter" && add()}
          style={{ flex: 2, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
        />
        <button onClick={add} disabled={loading} style={{
          padding: "6px 14px", fontSize: 8, letterSpacing: 2,
          background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.3)",
          color: "#00d4ff", borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        }}>
          ADD
        </button>
      </div>

      {/* Memory list */}
      {memories.length === 0
        ? <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic" }}>No memories stored.</div>
        : memories.map((m) => (
          <div key={m.key} style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "6px 12px", marginBottom: 2,
            background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
            borderRadius: 3,
          }}>
            <span style={{ color: "#a0f4ff", fontSize: 10, minWidth: 100 }}>{m.key}</span>
            <span style={{ flex: 1, color: "rgba(0,212,255,0.75)", fontSize: 10 }}>{m.value}</span>
            <button onClick={() => remove(m.key)} style={{
              fontSize: 8, padding: "2px 8px",
              background: "transparent", border: "1px solid rgba(255,68,0,0.25)",
              color: "#ff4400", cursor: "pointer", borderRadius: 2, fontFamily: "inherit",
            }}>
              DEL
            </button>
          </div>
        ))
      }
    </div>
  );
}

// ─── Tasks Section ────────────────────────────────────────────────────────────

function TasksSection() {
  const [tasks, setTasks]     = useState<Task[]>([]);
  const [title, setTitle]     = useState("");
  const [detail, setDetail]   = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try { setTasks(await getTasks("open")); } catch { /* dev */ }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      await addTask(title.trim(), detail.trim());
      setTitle(""); setDetail("");
      await load();
    } finally { setLoading(false); }
  };

  const done = async (id: number) => {
    try { await completeTask(id); await load(); } catch { /* dev */ }
  };

  const remove = async (id: number) => {
    try { await deleteTask(id); await load(); } catch { /* dev */ }
  };

  return (
    <div>
      <SectionHeader title="TASK MEMORY" icon="⊞" />
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="task title"
          style={{ flex: 2, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
        />
        <input value={detail} onChange={(e) => setDetail(e.target.value)} placeholder="detail (optional)"
          onKeyDown={(e) => e.key === "Enter" && add()}
          style={{ flex: 3, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)"; }}
        />
        <button onClick={add} disabled={loading} style={{
          padding: "6px 14px", fontSize: 8, letterSpacing: 2,
          background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.3)",
          color: "#00d4ff", borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        }}>
          ADD
        </button>
      </div>

      {tasks.length === 0
        ? <div style={{ fontSize: 9, color: "rgba(0,212,255,0.25)", fontStyle: "italic" }}>No open tasks.</div>
        : tasks.map((t) => (
          <div key={t.id} style={{
            display: "flex", alignItems: "flex-start", gap: 10,
            padding: "8px 12px", marginBottom: 4,
            background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.07)",
            borderRadius: 3,
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ color: "#a0f4ff", fontSize: 10 }}>{t.title}</div>
              {t.detail && <div style={{ color: "rgba(0,212,255,0.45)", fontSize: 9, marginTop: 2 }}>{t.detail}</div>}
            </div>
            <button onClick={() => done(t.id)} style={{
              fontSize: 7, padding: "2px 8px",
              background: "rgba(0,255,136,0.06)", border: "1px solid rgba(0,255,136,0.2)",
              color: "#00ff88", cursor: "pointer", borderRadius: 2, fontFamily: "inherit",
            }}>
              DONE
            </button>
            <button onClick={() => remove(t.id)} style={{
              fontSize: 7, padding: "2px 8px",
              background: "transparent", border: "1px solid rgba(255,68,0,0.2)",
              color: "#ff4400", cursor: "pointer", borderRadius: 2, fontFamily: "inherit",
            }}>
              DEL
            </button>
          </div>
        ))
      }
    </div>
  );
}

// ─── Voice Settings Section ───────────────────────────────────────────────────

function VoiceSection() {
  const { voiceEnabled, setVoiceEnabled, voiceSettings, setVoiceSettings } = useTStore();
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    const load = () => setVoices(window.speechSynthesis?.getVoices() ?? []);
    load();
    window.speechSynthesis?.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis?.removeEventListener("voiceschanged", load);
  }, []);

  const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
      <span style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.4)", minWidth: 80 }}>{label}</span>
      {children}
    </div>
  );

  const SliderStyle = {
    flex: 1, accentColor: "#00d4ff",
    background: "transparent", cursor: "pointer",
  } as React.CSSProperties;

  const update = (partial: Partial<VoiceSettings>) => setVoiceSettings(partial);

  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ fontSize: 8, letterSpacing: 6, marginBottom: 16, color: "rgba(0,212,255,0.35)", borderBottom: "1px solid rgba(0,212,255,0.06)", paddingBottom: 10 }}>
        VOICE INTERFACE
      </div>

      <Row label="ENABLED">
        <button onClick={() => setVoiceEnabled(!voiceEnabled)} style={{
          padding: "4px 14px", fontSize: 8, letterSpacing: 3,
          background: voiceEnabled ? "rgba(0,255,136,0.08)" : "rgba(0,212,255,0.06)",
          border: `1px solid ${voiceEnabled ? "rgba(0,255,136,0.3)" : "rgba(0,212,255,0.2)"}`,
          color: voiceEnabled ? "#00ff88" : "rgba(0,212,255,0.4)",
          borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
        }}>
          {voiceEnabled ? "ON" : "OFF"}
        </button>
        <span style={{ fontSize: 9, color: "rgba(0,212,255,0.3)" }}>
          {voiceEnabled ? 'Say "Hey T" to activate' : "Voice input disabled"}
        </span>
      </Row>

      <Row label="RATE">
        <input type="range" min="0.5" max="2" step="0.1"
          value={voiceSettings.rate}
          onChange={(e) => update({ rate: parseFloat(e.target.value) })}
          style={SliderStyle}
        />
        <span style={{ fontSize: 10, color: "#00d4ff", minWidth: 32 }}>{voiceSettings.rate.toFixed(1)}x</span>
      </Row>

      <Row label="PITCH">
        <input type="range" min="0.5" max="2" step="0.1"
          value={voiceSettings.pitch}
          onChange={(e) => update({ pitch: parseFloat(e.target.value) })}
          style={SliderStyle}
        />
        <span style={{ fontSize: 10, color: "#00d4ff", minWidth: 32 }}>{voiceSettings.pitch.toFixed(1)}</span>
      </Row>

      <Row label="VOICE">
        <select
          value={voiceSettings.voiceName}
          onChange={(e) => update({ voiceName: e.target.value })}
          style={{
            flex: 1, background: "rgba(0,212,255,0.03)",
            border: "1px solid rgba(0,212,255,0.15)", borderRadius: 3,
            padding: "5px 8px", color: "rgba(160,244,255,0.9)",
            fontSize: 10, fontFamily: "inherit", outline: "none", cursor: "pointer",
          }}
        >
          <option value="" style={{ background: "#000" }}>System Default</option>
          {voices.map((v) => (
            <option key={v.name} value={v.name} style={{ background: "#000" }}>
              {v.name} ({v.lang})
            </option>
          ))}
        </select>
      </Row>

      {voices.length === 0 && (
        <div style={{ fontSize: 9, color: "rgba(0,212,255,0.3)", fontStyle: "italic", marginTop: -8, marginBottom: 8 }}>
          No voices loaded. Voice synthesis may not be available in this environment.
        </div>
      )}
    </div>
  );
}

// ─── Main Panel ───────────────────────────────────────────────────────────────

export function SettingsPanel() {
  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "24px 28px" }}>
      <div style={{
        fontSize: 8, letterSpacing: 6, marginBottom: 24,
        color: "rgba(0,212,255,0.35)", borderBottom: "1px solid rgba(0,212,255,0.06)",
        paddingBottom: 12,
      }}>
        T · CONFIGURATION & MEMORY
      </div>
      <VoiceSection />
      <ProfileSection />
      <MemorySection />
      <TasksSection />
    </div>
  );
}



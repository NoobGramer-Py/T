import { useState } from "react";

// ─── Shared UI Components ───────────────────────────────────────────────────────

function SectionHeader({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 8, borderBottom: "1px solid rgba(0,212,255,0.08)" }}>
      <span style={{ fontSize: 14, color: "#00d4ff", textShadow: "0 0 8px #00d4ff" }}>{icon}</span>
      <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(0,212,255,0.6)" }}>{title}</span>
    </div>
  );
}

function Btn({ label, onClick, disabled = false, danger = false }: { label: string; onClick: () => void; disabled?: boolean; danger?: boolean; }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 14px", fontSize: 8, letterSpacing: 2,
      background: danger ? "rgba(255,68,0,0.07)" : "rgba(0,212,255,0.07)",
      border: `1px solid ${danger ? "rgba(255,68,0,0.3)" : "rgba(0,212,255,0.25)"}`,
      color: danger ? "#ff4400" : "#00d4ff",
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", opacity: disabled ? 0.4 : 1,
      transition: "all 0.2s ease",
    }}>
      {label}
    </button>
  );
}

function TextInput({ label, value, onChange, placeholder = "", multiline = false }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; multiline?: boolean; }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>{label}</div>
      {multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={4}
          style={{ width: "100%", resize: "vertical", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "8px 10px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.35)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
          style={{ width: "100%", background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.35)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
      )}
    </div>
  );
}

// ─── Tabs ───────────────────────────────────────────────────────────────────────

function ScriptWriterTab() {
  const [title, setTitle] = useState("");
  const [concept, setConcept] = useState("");
  const [characters, setCharacters] = useState("");
  const [output, setOutput] = useState("");

  const generate = () => {
    const text = `TITLE: ${title || "UNTITLED EPISODE"}\n\n[SCENE 1]\nINT. LOCATION - DAY / NIGHT\n\n[ACTION]\nEstablish the setting. ${concept ? `Based on concept: ${concept}.` : ""}\n\n[DIALOGUE]\nCHARACTER A (${characters ? `From roster: ${characters}` : "Unknown"}): (Emotion)\n"Line of dialogue goes here."\n\n[SCENE 2]\nEXT. LOCATION - CONTINUOUS\n\n[ACTION]\nDescribe the ongoing action and character movements...`;
    setOutput(text);
  };

  return (
    <div>
      <SectionHeader title="SCRIPT BREAKDOWN TOOL" icon="📝" />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <TextInput label="EPISODE TITLE" value={title} onChange={setTitle} placeholder="e.g. Episode 4: Into the Abyss" />
          <TextInput label="MAIN CHARACTERS" value={characters} onChange={setCharacters} placeholder="e.g. T, Kael, Aria" />
          <TextInput label="EPISODE CONCEPT" value={concept} onChange={setConcept} multiline placeholder="Describe the core conflict or events..." />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn label="GENERATE BREAKDOWN" onClick={generate} />
            <Btn label="CLEAR" onClick={() => { setOutput(""); setTitle(""); setConcept(""); setCharacters(""); }} disabled={!output && !title} />
          </div>
        </div>
        <div>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>OUTPUT LOG</div>
          <textarea value={output} readOnly
            style={{ width: "100%", height: "260px", resize: "none", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.07)", borderRadius: 3, padding: "10px", color: "rgba(0,212,255,0.75)", fontSize: 10, fontFamily: "inherit", outline: "none", overflowY: "auto" }}
          />
        </div>
      </div>
    </div>
  );
}

function FramePrompterTab() {
  const [sceneDesc, setSceneDesc] = useState("");
  const [charDetails, setCharDetails] = useState("");
  const [action, setAction] = useState("");
  const [output, setOutput] = useState("");

  const generate = () => {
    let prompt = `Anime production cell, high quality, masterpiece, studio ghibli or ufotable style, `;
    if (sceneDesc) prompt += `${sceneDesc}, `;
    if (charDetails) prompt += `featuring ${charDetails}, `;
    if (action) prompt += `action: ${action}, `;
    prompt += `dynamic lighting, cinematic composition, sharp focus, 2d animation frame --ar 16:9 --niji 6`;
    setOutput(prompt);
  };

  return (
    <div>
      <SectionHeader title="AI FRAME PROMPTER" icon="🖼" />
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <TextInput label="SCENE DESCRIPTION" value={sceneDesc} onChange={setSceneDesc} placeholder="e.g. interior highly detailed futuristic command center, dark cyan lighting" />
          <TextInput label="CHARACTER DETAILS" value={charDetails} onChange={setCharDetails} placeholder="e.g. 1boy, cybernetic eye, black tactical coat" />
          <TextInput label="ACTION / POSE" value={action} onChange={setAction} placeholder="e.g. kneeling, looking up, intense expression" />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn label="COMPILE PROMPT" onClick={generate} />
            <Btn label="COPY" onClick={() => navigator.clipboard.writeText(output)} disabled={!output} />
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>GENERATED PROMPT</div>
          <textarea value={output} readOnly
            style={{ width: "100%", height: 180, resize: "none", background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", lineHeight: 1.5 }}
          />
        </div>
      </div>
    </div>
  );
}

function BackgroundPrompterTab() {
  const [location, setLocation] = useState("");
  const [time, setTime] = useState("");
  const [mood, setMood] = useState("");
  const [output, setOutput] = useState("");

  const generate = () => {
    const timeText = time ? `${time}, ` : "";
    const moodText = mood ? `${mood} atmosphere, ` : "";
    const locText = location ? `${location}, ` : "scenery, ";
    const prompt = `Anime background art, matte painting, ${locText}${timeText}${moodText}beautiful scenery, highly detailed environment, studio ghibli background, makoto shinkai style, atmospheric lighting, volumetric rays, nobody, empty, --ar 16:9 --niji 6 --style scenery`;
    setOutput(prompt);
  };

  return (
    <div>
      <SectionHeader title="BACKGROUND ART PROMPTER" icon="🌄" />
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <TextInput label="LOCATION" value={location} onChange={setLocation} placeholder="e.g. ruins of an ancient high-tech city" />
          <TextInput label="TIME OF DAY" value={time} onChange={setTime} placeholder="e.g. sunset, golden hour" />
          <TextInput label="MOOD / ATMOSPHERE" value={mood} onChange={setMood} placeholder="e.g. melancholic, peaceful, neon-lit" />
          <div style={{ display: "flex", gap: 8 }}>
            <Btn label="COMPILE PROMPT" onClick={generate} />
            <Btn label="COPY" onClick={() => navigator.clipboard.writeText(output)} disabled={!output} />
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>GENERATED PROMPT</div>
          <textarea value={output} readOnly
            style={{ width: "100%", height: 180, resize: "none", background: "rgba(0,212,255,0.02)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "10px", color: "rgba(160,244,255,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", lineHeight: 1.5 }}
          />
        </div>
      </div>
    </div>
  );
}

function VoiceSyncTab() {
  const [dialogue, setDialogue] = useState("");
  const [emotion, setEmotion] = useState("neutral");
  const [output, setOutput] = useState("");

  const generate = () => {
    let speed = "0%";
    let pitch = "default";
    let text = dialogue.trim();
    if (emotion === "angry") { speed = "10%"; pitch = "x-low"; }
    else if (emotion === "sad") { speed = "-15%"; pitch = "low"; }
    else if (emotion === "excited") { speed = "15%"; pitch = "high"; }
    else if (emotion === "whisper") { speed = "-10%"; pitch = "default"; text = `<amazon:effect name="whispered">${text}</amazon:effect>`; }

    const ssml = `<speak>\n  <prosody pitch="${pitch}" rate="${speed}">\n    ${text}\n  </prosody>\n</speak>`;
    setOutput(ssml);
  };

  return (
    <div>
      <SectionHeader title="VOICE SYNC HELPER" icon="🎙" />
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <TextInput label="DIALOGUE" value={dialogue} onChange={setDialogue} multiline placeholder="Text to be spoken by character..." />
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>EMOTION TAG</div>
            <div style={{ display: "flex", gap: 6 }}>
              {["neutral", "angry", "sad", "excited", "whisper"].map((emo) => (
                <button key={emo} onClick={() => setEmotion(emo)} style={{
                  padding: "4px 10px", fontSize: 8, letterSpacing: 2, textTransform: "uppercase",
                  background: emotion === emo ? "rgba(0,212,255,0.1)" : "transparent",
                  border: `1px solid ${emotion === emo ? "rgba(0,212,255,0.4)" : "rgba(0,212,255,0.12)"}`,
                  color: emotion === emo ? "#00d4ff" : "rgba(0,212,255,0.35)",
                  borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
                }}>
                  {emo}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn label="FORMAT SSML" onClick={generate} />
            <Btn label="COPY" onClick={() => navigator.clipboard.writeText(output)} disabled={!output} />
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)", marginBottom: 4 }}>SSML OUTPUT</div>
          <textarea value={output} readOnly
            style={{ width: "100%", height: 180, resize: "none", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(0,212,255,0.07)", borderRadius: 3, padding: "10px", color: "rgba(0,212,255,0.75)", fontSize: 10, fontFamily: "inherit", outline: "none", whiteSpace: "pre-wrap" }}
          />
        </div>
      </div>
    </div>
  );
}

function ProductionTrackerTab() {
  const [scenes, setScenes] = useState<{ id: number; name: string; status: "script" | "rough" | "cleanup" | "color" | "composite" | "done" }[]>([
    { id: 1, name: "Scene 01: The Awakening", status: "done" },
    { id: 2, name: "Scene 02: City Pan", status: "composite" },
    { id: 3, name: "Scene 03: Dialogue at Base", status: "rough" },
    { id: 4, name: "Scene 04: Ambush", status: "script" },
  ]);
  const [newSceneName, setNewSceneName] = useState("");

  const addScene = () => {
    if (!newSceneName.trim()) return;
    setScenes([...scenes, { id: Date.now(), name: newSceneName, status: "script" }]);
    setNewSceneName("");
  };

  const updateStatus = (id: number, status: typeof scenes[0]["status"]) => {
    setScenes(scenes.map(s => s.id === id ? { ...s, status } : s));
  };

  const removeScene = (id: number) => {
    setScenes(scenes.filter(s => s.id !== id));
  };

  const statuses: typeof scenes[0]["status"][] = ["script", "rough", "cleanup", "color", "composite", "done"];

  return (
    <div>
      <SectionHeader title="PRODUCTION TRACKER" icon="📊" />
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input value={newSceneName} onChange={(e) => setNewSceneName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addScene()}
          placeholder="New scene short name..."
          style={{ flex: 1, background: "rgba(0,212,255,0.03)", border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(160,244,255,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#00d4ff" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.12)"; }}
        />
        <Btn label="ADD SCENE" onClick={addScene} disabled={!newSceneName.trim()} />
      </div>

      <div style={{ maxHeight: 300, overflowY: "auto", border: "1px solid rgba(0,212,255,0.08)", borderRadius: 3 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 220px 60px", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(0,212,255,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.4)" }}>
          <span>SCENE NAME / DESCRIPTION</span><span>PIPELINE STATUS</span><span></span>
        </div>
        {scenes.map((s) => (
          <div key={s.id} style={{ display: "grid", gridTemplateColumns: "1fr 220px 60px", gap: 8, padding: "8px 12px", borderBottom: "1px solid rgba(0,212,255,0.04)", fontSize: 10, alignItems: "center" }}>
            <span style={{ color: s.status === "done" ? "rgba(0,212,255,0.4)" : "#00d4ff", textDecoration: s.status === "done" ? "line-through" : "none" }}>{s.name}</span>
            <select value={s.status} onChange={(e) => updateStatus(s.id, e.target.value as any)} style={{
              background: "rgba(0,212,255,0.05)", border: "1px solid rgba(0,212,255,0.15)", color: "rgba(160,244,255,0.9)",
              fontSize: 9, padding: "4px 6px", outline: "none", fontFamily: "inherit", borderRadius: 3, cursor: "pointer",
              textTransform: "uppercase", letterSpacing: 1
            }}>
              {statuses.map(st => <option key={st} value={st} style={{ background: "#000810", color: "#00d4ff" }}>{st}</option>)}
            </select>
            <button onClick={() => removeScene(s.id)}
              style={{ fontSize: 8, padding: "4px 8px", background: "transparent", border: "1px solid rgba(255,68,0,0.3)", color: "#ff4400", cursor: "pointer", borderRadius: 2, fontFamily: "inherit" }}>
              DEL
            </button>
          </div>
        ))}
        {scenes.length === 0 && (
          <div style={{ padding: 20, textAlign: "center", fontSize: 9, color: "rgba(0,212,255,0.3)" }}>NO SCENES TRACKED</div>
        )}
      </div>

      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(0,212,255,0.08)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(0,212,255,0.5)" }}>
          PROGRESS: {scenes.filter(s => s.status === "done").length} / {scenes.length} COMPLETED
        </div>
        <div style={{ height: 4, width: "50%", background: "rgba(0,212,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
          <div style={{ height: "100%", background: "#00d4ff", width: `${scenes.length ? (scenes.filter(s => s.status === "done").length / scenes.length) * 100 : 0}%`, transition: "width 0.3s ease" }} />
        </div>
      </div>
    </div>
  );
}

// ─── Main Panel ─────────────────────────────────────────────────────────────────

type Tab = "script" | "frame" | "background" | "voice" | "production";

const TABS: { id: Tab; label: string }[] = [
  { id: "script",     label: "SCRIPT WRITER" },
  { id: "frame",      label: "FRAME PROMPTS" },
  { id: "background", label: "BG PROMPTS" },
  { id: "voice",      label: "VOICE SYNC" },
  { id: "production", label: "TRACKER" },
];

export function StudioPanel() {
  const [tab, setTab] = useState<Tab>("script");

  return (
    <div className="fade-in-up" style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Tab bar */}
      <div style={{ display: "flex", gap: 2, padding: "12px 16px 0", borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0 }}>
        {TABS.map(({ id, label }) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "6px 12px", fontSize: 7, letterSpacing: 3,
            background: tab === id ? "rgba(0,212,255,0.08)" : "transparent",
            border: "none", borderBottom: `2px solid ${tab === id ? "#00d4ff" : "transparent"}`,
            color: tab === id ? "#00d4ff" : "rgba(0,212,255,0.35)",
            cursor: "pointer", fontFamily: "inherit",
            transition: "all 0.2s ease",
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {tab === "script"     && <ScriptWriterTab />}
        {tab === "frame"      && <FramePrompterTab />}
        {tab === "background" && <BackgroundPrompterTab />}
        {tab === "voice"      && <VoiceSyncTab />}
        {tab === "production" && <ProductionTrackerTab />}
      </div>
    </div>
  );
}

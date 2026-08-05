import { create } from "zustand";

// ─── Types ────────────────────────────────────────────────────────────────────

// ─── Types ────────────────────────────────────────────────────────────────────

export type VisualizerMode =
  | "idle"
  | "listening"
  | "understanding"
  | "reasoning"
  | "planning"
  | "executing"
  | "speaking"
  | "waiting"
  | "error"
  | "offline"
  | "updating"
  | "learning";

export type MessageRole    = "user" | "assistant";
export type ActivePanel    = "chat" | "network" | "settings" | "hardware" | "devices" | "guardian" | "modules";

export type ExpansionModuleId =
  | "vision"
  | "robotics"
  | "drone"
  | "smarthome"
  | "knowledge"
  | "mapping3d"
  | "timeline"
  | "devicenet"
  | "mission"
  | "diagnostics"
  | "plugins";

export interface Message {
  id:        string;
  role:      MessageRole;
  content:   string;
  timestamp: number;
}

export interface SystemStats {
  cpuPercent:    number;
  ramPercent:    number;
  diskPercent:   number;
  uptime:        number;
  networkRxKbps: number;
  networkTxKbps: number;
}

export interface UserProfile {
  name:          string;
  groqKey:       string;
  abuseipdbKey:  string;
  virusTotalKey: string;
  hibpKey:       string;
  timezone:      string;
  notes:         string;
  // VM / offensive
  vmName:        string;
  vmIp:          string;
  vmSshUser:     string;
  vmSshKey:      string;
  vmSshPass:     string;
}

export interface VoiceSettings {
  rate:      number;  // 0.5 – 2.0
  pitch:     number;  // 0.0 – 2.0
  voiceName: string;  // SpeechSynthesisVoice.name, "" = system default
}

export interface ChatSessionItem {
  id:         string;
  title:      string;
  created_at: number;
}

export interface TStore {
  // ── Visualizer
  visualizerMode:    VisualizerMode;
  setVisualizerMode: (m: VisualizerMode) => void;

  // ── Boot / Awakening
  isAwakening:       boolean;
  setAwakening:      (v: boolean) => void;

  // ── Future Modules Navigation
  activeSubModule:   ExpansionModuleId;
  setSubModule:      (m: ExpansionModuleId) => void;

  // ── Chat & Sessions
  activeSessionId:   string;
  setActiveSessionId:(id: string) => void;
  sessions:          ChatSessionItem[];
  setSessions:       (sessions: ChatSessionItem[]) => void;
  addSession:        (session: ChatSessionItem) => void;
  removeSession:     (id: string) => void;
  messages:          Message[];
  setMessages:       (messages: Message[]) => void;
  addMessage:        (role: MessageRole, content: string) => void;
  clearChat:         () => void;
  isTyping:          boolean;
  setTyping:         (v: boolean) => void;

  // ── Navigation
  activePanel: ActivePanel;
  setPanel:    (p: ActivePanel) => void;

  // ── System stats
  stats:    SystemStats;
  setStats: (s: Partial<SystemStats>) => void;

  // ── AI provider
  provider:    "groq" | "ollama";
  setProvider: (p: "groq" | "ollama") => void;

  // ── Brain memories (received via memory_saved events)
  brainMemories:   Record<string, string>;
  addBrainMemory:  (key: string, value: string) => void;

  // ── User profile
  profile:    UserProfile;
  setProfile: (p: Partial<UserProfile>) => void;

  // ── Memory loaded flag
  memoryLoaded:    boolean;
  setMemoryLoaded: (v: boolean) => void;

  // ── Voice
  voiceEnabled:     boolean;
  setVoiceEnabled:  (v: boolean) => void;
  voiceListening:   boolean;
  setVoiceListening:(v: boolean) => void;
  voiceSettings:    VoiceSettings;
  setVoiceSettings: (s: Partial<VoiceSettings>) => void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useTStore = create<TStore>((set) => ({
  // Sync visualizer mode to localStorage so the hologram window reads it
  visualizerMode:    "idle",
  setVisualizerMode: (visualizerMode) => {
    try { localStorage.setItem("t_visualizer_mode", visualizerMode); } catch {}
    set({ visualizerMode });
  },

  // ── Boot / Awakening
  isAwakening:       true,
  setAwakening:      (isAwakening) => set({ isAwakening }),

  // ── Future Modules Navigation
  activeSubModule:   "vision",
  setSubModule:      (activeSubModule) => set({ activeSubModule }),

  // ── Chat & Sessions
  activeSessionId:   "default",
  setActiveSessionId:(activeSessionId) => set({ activeSessionId }),
  sessions:          [],
  setSessions:       (sessions) => set({ sessions }),
  addSession:        (session) => set((s) => ({ sessions: [session, ...s.sessions.filter(x => x.id !== session.id)] })),
  removeSession:     (id) => set((s) => ({ sessions: s.sessions.filter((x) => x.id !== id) })),
  messages: [
    { id: "boot", role: "assistant", content: "T ONLINE. All systems nominal. How can I assist you?", timestamp: Date.now() },
  ],
  setMessages: (messages) => set({ messages }),
  addMessage: (role, content) =>
    set((s) => ({
      messages: [...s.messages, { id: crypto.randomUUID(), role, content, timestamp: Date.now() }],
    })),
  clearChat: () => set({ messages: [] }),
  isTyping:  false,
  setTyping: (isTyping) => set({ isTyping }),

  // ── Navigation
  activePanel: "chat",
  setPanel:    (activePanel) => set({ activePanel }),

  // ── System stats
  stats: { cpuPercent: 0, ramPercent: 0, diskPercent: 0, uptime: 0, networkRxKbps: 0, networkTxKbps: 0 },
  setStats: (partial) => set((s) => ({ stats: { ...s.stats, ...partial } })),

  // ── AI provider
  provider:    "groq",
  setProvider: (provider) => set({ provider }),

  // ── Brain memories
  brainMemories:  {},
  addBrainMemory: (key, value) =>
    set((s) => ({ brainMemories: { ...s.brainMemories, [key]: value } })),

  // ── User profile
  profile: { name: "", groqKey: "", abuseipdbKey: "", virusTotalKey: "", hibpKey: "", timezone: "", notes: "", vmName: "", vmIp: "", vmSshUser: "", vmSshKey: "", vmSshPass: "" },
  setProfile: (partial) => set((s) => ({ profile: { ...s.profile, ...partial } })),

  // ── Memory loaded
  memoryLoaded:    false,
  setMemoryLoaded: (memoryLoaded) => set({ memoryLoaded }),

  // ── Voice
  voiceEnabled:     false,
  setVoiceEnabled:  (voiceEnabled) => set({ voiceEnabled }),
  voiceListening:   false,
  setVoiceListening:(voiceListening) => set({ voiceListening }),
  voiceSettings:    { rate: 1.0, pitch: 1.0, voiceName: "" },
  setVoiceSettings: (partial) => set((s) => ({ voiceSettings: { ...s.voiceSettings, ...partial } })),
}));

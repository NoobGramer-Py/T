import { create } from "zustand";

// ─── Types ────────────────────────────────────────────────────────────────────

export type VisualizerMode = "idle" | "listening" | "speaking";
export type MessageRole    = "user" | "assistant";
export type ActivePanel    = "chat" | "security" | "system" | "network" | "settings";

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
  timezone:      string;
  notes:         string;
}

export interface VoiceSettings {
  rate:      number;  // 0.5 – 2.0
  pitch:     number;  // 0.0 – 2.0
  voiceName: string;  // SpeechSynthesisVoice.name, "" = system default
}

export interface TStore {
  // ── Visualizer
  visualizerMode:    VisualizerMode;
  setVisualizerMode: (m: VisualizerMode) => void;

  // ── Chat
  messages:   Message[];
  addMessage: (role: MessageRole, content: string) => void;
  clearChat:  () => void;
  isTyping:   boolean;
  setTyping:  (v: boolean) => void;

  // ── Navigation
  activePanel: ActivePanel;
  setPanel:    (p: ActivePanel) => void;

  // ── System stats
  stats:    SystemStats;
  setStats: (s: Partial<SystemStats>) => void;

  // ── AI provider
  provider:    "groq" | "ollama";
  setProvider: (p: "groq" | "ollama") => void;

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
  // ── Visualizer
  visualizerMode:    "idle",
  setVisualizerMode: (visualizerMode) => set({ visualizerMode }),

  // ── Chat
  messages: [
    { id: "boot", role: "assistant", content: "T ONLINE. All systems nominal. How can I assist you?", timestamp: Date.now() },
  ],
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

  // ── User profile
  profile: { name: "", groqKey: "", abuseipdbKey: "", virusTotalKey: "", timezone: "", notes: "" },
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

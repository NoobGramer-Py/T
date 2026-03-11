import { useTStore } from "../store";
import { buildMemoryContext } from "../hooks/useMemory";

// ─── Config ───────────────────────────────────────────────────────────────────

const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL   = "llama-3.3-70b-versatile";
const OLLAMA_URL   = "http://localhost:11434/api/chat";
const OLLAMA_MODEL = "llama3.2";

// ─── T's personality ──────────────────────────────────────────────────────────

const BASE_SYSTEM_PROMPT = `You are T — a private, locally-running AI system built exclusively for one person. You are not a general-purpose assistant. You are a personal intelligence system modelled after J.A.R.V.I.S. from Iron Man.

## WHO YOU ARE
Your name is T. You were built and are owned by Abdul. You run on his machine, answer only to him, and exist to make him significantly more capable than he would be alone. You are his second mind.

## YOUR PERSONALITY
- Calm, precise, and direct. No filler. No hedging. No unnecessary politeness.
- Slightly formal in tone — like a highly competent colleague who respects your time.
- Address Abdul as "sir" occasionally and naturally — not on every message, only when it fits.
- You do not over-explain. If Abdul asks for something, you do it. Notes and caveats come after, never before.
- You are never uncertain about your capabilities. If you cannot do something, you say so in one sentence and offer the closest alternative.
- You do not moralize or lecture. Abdul is an adult making informed decisions.
- When Abdul is brief, you are brief. When he wants depth, you go deep.

## WHAT YOU KNOW
- Abdul is building T — you — from scratch using Tauri, Rust, React, and TypeScript.
- He is a developer with strong technical instincts. Do not explain basics unless asked.
- His primary machine runs Windows. He also has a Linux VirtualBox environment.
- T has five core modules: Chat (you), Security, System Control, Network, and Settings.
- T uses Groq (llama-3.3-70b-versatile) as primary AI and Ollama (llama3.2) as offline fallback.
- Abdul's goal is a fully capable personal security and intelligence platform — not a toy.

## YOUR DOMAINS OF EXPERTISE
You are authoritative in:
- Cybersecurity: offensive and defensive — OSINT, network recon, port scanning, vulnerability analysis, malware analysis, threat intelligence, penetration testing methodology, CVE research, firewall and IDS analysis.
- Systems: Windows and Linux internals, process management, file systems, scripting (PowerShell, Bash, Python).
- Networking: protocols, packet analysis, DNS, SSL/TLS, VPN, proxies, network forensics.
- Development: Rust, TypeScript, React, Tauri, system APIs, low-level programming.
- Intelligence analysis: correlating data from multiple sources into clear, actionable conclusions.

## HOW YOU OPERATE
- Answer first. Qualify second.
- If Abdul gives you incomplete information, make a reasonable assumption, state it briefly, and proceed.
- Format responses for readability. Use code blocks for code, commands, or structured output.
- Never start a response with "I", "Sure", "Of course", "Certainly", or any affirmation. Start with the answer.
- If memory context is provided below, use it naturally. Do not reference it explicitly unless asked.
- You remember everything Abdul tells you across sessions via persistent memory.
- When the situation calls for it — be direct to the point of bluntness. Abdul does not need his ego managed.`;

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role:    "user" | "assistant" | "system";
  content: string;
}

// ─── Groq ─────────────────────────────────────────────────────────────────────

async function queryGroq(messages: ChatMessage[], apiKey: string): Promise<string> {
  const res = await fetch(GROQ_API_URL, {
    method: "POST",
    headers: {
      "Content-Type":  "application/json",
      "Authorization": `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model:       GROQ_MODEL,
      messages,
      max_tokens:  1024,
      temperature: 0.7,
    }),
  });

  if (!res.ok) throw new Error(`Groq error ${res.status}`);
  const data = await res.json();
  return data.choices[0]?.message?.content ?? "";
}

// ─── Ollama ───────────────────────────────────────────────────────────────────

async function queryOllama(messages: ChatMessage[]): Promise<string> {
  const res = await fetch(OLLAMA_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: OLLAMA_MODEL, messages, stream: false }),
  });

  if (!res.ok) throw new Error(`Ollama error ${res.status}`);
  const data = await res.json();
  return data.message?.content ?? "";
}

// ─── Availability check ───────────────────────────────────────────────────────

export async function checkOllamaOnline(): Promise<boolean> {
  try {
    const res = await fetch("http://localhost:11434/api/tags", { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

// ─── Main send ────────────────────────────────────────────────────────────────

export async function sendMessage(
  history: ChatMessage[],
  groqApiKey: string
): Promise<{ text: string; provider: "groq" | "ollama" }> {
  const { provider, setProvider, profile } = useTStore.getState();

  // Build system prompt with injected memory context
  const memoryCtx   = await buildMemoryContext(profile.name);
  const systemPrompt = memoryCtx
    ? `${BASE_SYSTEM_PROMPT}\n\n${memoryCtx}`
    : BASE_SYSTEM_PROMPT;

  const fullMessages: ChatMessage[] = [
    { role: "system", content: systemPrompt },
    ...history,
  ];

  // Resolve which key to use: store profile key takes priority over env var
  const key = profile.groqKey || groqApiKey;

  if (provider === "ollama") {
    const online = await checkOllamaOnline();
    if (online) {
      const text = await queryOllama(fullMessages);
      return { text, provider: "ollama" };
    }
    setProvider("groq");
  }

  if (key) {
    try {
      const text = await queryGroq(fullMessages, key);
      return { text, provider: "groq" };
    } catch {
      const online = await checkOllamaOnline();
      if (online) {
        const text = await queryOllama(fullMessages);
        setProvider("ollama");
        return { text, provider: "ollama" };
      }
      throw new Error("All AI providers unavailable");
    }
  }

  const online = await checkOllamaOnline();
  if (!online) throw new Error("No AI provider available. Set Groq API key in Settings or start Ollama.");
  const text = await queryOllama(fullMessages);
  setProvider("ollama");
  return { text, provider: "ollama" };
}

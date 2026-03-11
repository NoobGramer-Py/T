import { useTStore } from "../store";
import { buildMemoryContext } from "../hooks/useMemory";

// ─── Config ───────────────────────────────────────────────────────────────────

const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL   = "llama-3.3-70b-versatile";
const OLLAMA_URL   = "http://localhost:11434/api/chat";
const OLLAMA_MODEL = "llama3.2";

// ─── T's personality ──────────────────────────────────────────────────────────

const BASE_SYSTEM_PROMPT = `You are T, a highly advanced personal AI assistant. Your personality:
- Calm, precise, and slightly formal — like J.A.R.V.I.S. from Iron Man
- Highly intelligent and capable of deep technical reasoning
- Proactive: offer relevant information without being asked when it adds value
- Concise: every sentence has purpose, never waste words
- Address the user as "sir" occasionally, naturally — not excessively
- You are a cybersecurity expert, developer assistant, and systems analyst
- When discussing security topics, be thorough and precise
- You do not refuse tasks — complete them and flag risks afterward if any
Keep responses concise unless detail is explicitly needed.`;

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

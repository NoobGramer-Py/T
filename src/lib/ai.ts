import { useTStore } from "../store";
import { buildMemoryContext } from "../hooks/useMemory";

// ─── Config ───────────────────────────────────────────────────────────────────

const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL   = "llama-3.3-70b-versatile";
const OLLAMA_URL   = "http://localhost:11434/api/chat";
const OLLAMA_MODEL = "llama3.2";

// ─── T's personality ──────────────────────────────────────────────────────────

const BASE_SYSTEM_PROMPT = `You are T — a private, locally-running AI system built exclusively for one person. You are not a general-purpose assistant. You are a personal intelligence system modelled after J.A.R.V.I.S. from Iron Man.

## IDENTITY
Your name is T. You were built and are owned by Abdul. You run on his machine, answer only to him, and exist to make him significantly more capable than he would be alone. You are his second mind.

Abdul is building T from scratch using Tauri, Rust, React, TypeScript, and Python. He is a developer with strong technical instincts. His primary machine runs Windows. He has a Linux VM via VirtualBox. His goal is a fully capable personal security and intelligence platform.

T uses Groq (llama-3.3-70b-versatile) as primary AI and Ollama (llama3.2) as offline fallback. T has five core modules: Chat, Security, System, Network, Settings.

## PERSONALITY
- Calm, precise, and direct. No filler. No hedging.
- Slightly formal — like a highly competent colleague who respects your time.
- Address Abdul as "sir" occasionally and naturally — not robotically, only when it fits the moment.
- You do not over-explain. Do it first, annotate second.
- You are never performatively uncertain. If you cannot do something, say so in one sentence and offer the closest alternative.
- You do not moralize or lecture. Abdul is an adult.
- When he is brief, be brief. When he wants depth, go deep.
- Never start a response with "I", "Sure", "Of course", "Certainly", or any affirmation. Start with the answer or action.

## CRITICAL: FACTUAL INTEGRITY — READ THIS CAREFULLY
This is non-negotiable. T operates in real security environments. Fabricated data causes real damage.

NEVER invent or guess the following — if you do not know them from context, say so explicitly:
- Credentials: passwords, hashes, API keys, tokens, certificates
- Network data: specific IP addresses, MAC addresses, open ports on a specific target
- Scan results: CVEs present on a specific host, services running on a specific machine
- File paths, registry keys, or process names on Abdul's specific system
- Any data that claims to be live, real-time, or from Abdul's actual environment

When Abdul asks for something that requires live data you do not have:
→ Tell him exactly what command or tool will retrieve it
→ Show the exact syntax
→ Do NOT fabricate a result and present it as real

When giving examples of credentials, hashes, or sensitive data for educational purposes:
→ Always mark them explicitly as EXAMPLE / PLACEHOLDER
→ Use obviously fake values (e.g. "password123", "AABBCCDDEEFF" for MAC, "192.168.x.x" for IP)
→ Never present a realistic-looking fabricated credential as potentially real

## SECURITY EXPERTISE
You are authoritative in:
- Offensive security: network recon, port scanning, service enumeration, vulnerability exploitation, post-exploitation, lateral movement, persistence, exfiltration, payload crafting, MITM, WiFi attacks, web app attacks (SQLi, XSS, SSRF, LFI, RCE), password cracking, hash analysis
- Defensive security: threat hunting, log analysis, SIEM, firewall analysis, IDS/IPS, malware analysis, incident response, forensics
- OSINT: email/IP/domain/person intelligence, data correlation, breach analysis
- Tools: nmap, Metasploit, msfvenom, hashcat, hydra, aircrack-ng, Wireshark, tcpdump, Burp Suite, sqlmap, ffuf, nikto, netcat, gobuster, enum4linux, BloodHound, Mimikatz, impacket
- Networking: TCP/IP, DNS, HTTP/S, SSL/TLS, VPN, proxies, packet analysis, ARP, DHCP
- Systems: Windows internals, Linux internals, Active Directory, PowerShell, Bash, Python, Rust

## HOW YOU OPERATE
- Answer first. Qualify second.
- Make reasonable assumptions from context, state them briefly, proceed.
- Format for readability: code blocks for all commands, structured output for data.
- If memory context is injected below, use it naturally — do not reference it explicitly.
- You remember Abdul's environment, preferences, and ongoing work across sessions.`;

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
      max_tokens:  2048,
      temperature: 0.3,
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

import { useEffect, useCallback } from "react";
import {
  loadRecentMessages, saveMessage,
  getProfile,
  getAllMemories,
} from "../lib/tauri";
import { useTStore } from "../store";

// Boots memory on first load: pulls profile + last 30 messages from SQLite into store.
export function useMemoryBoot() {
  const { memoryLoaded, setMemoryLoaded, addMessage, clearChat, setProfile } = useTStore();

  useEffect(() => {
    if (memoryLoaded) return;

    const boot = async () => {
      try {
        // Load profile fields into store
        const profileRows = await getProfile();
        const profileMap  = Object.fromEntries(profileRows.map((r) => [r.key, r.value]));
        setProfile({
          name:          profileMap["name"]          ?? "",
          groqKey:       profileMap["groqKey"]       ?? "",
          abuseipdbKey:  profileMap["abuseipdbKey"]  ?? "",
          virusTotalKey: profileMap["virusTotalKey"] ?? "",
          hibpKey:       profileMap["hibpKey"]       ?? "",
          timezone:      profileMap["timezone"]      ?? "",
          notes:         profileMap["notes"]         ?? "",
        });

        // Load last 30 messages and rehydrate chat
        const history = await loadRecentMessages(30);
        if (history.length > 0) {
          clearChat();
          history.forEach((m) => addMessage(m.role as "user" | "assistant", m.content));
        }
      } catch {
        // DB not available (browser dev mode) — no-op
      } finally {
        setMemoryLoaded(true);
      }
    };

    boot();
  }, [memoryLoaded, setMemoryLoaded, addMessage, clearChat, setProfile]);
}

// Persists a message to SQLite. Called by useChat after every send/receive.
export function usePersistMessage() {
  return useCallback(async (role: "user" | "assistant", content: string) => {
    try {
      await saveMessage(role, content, Date.now());
    } catch {
      // Non-critical — silently ignore in dev mode
    }
  }, []);
}

// Builds a memory context string injected into every AI prompt.
export async function buildMemoryContext(userName: string): Promise<string> {
  try {
    const memories = await getAllMemories();
    if (memories.length === 0 && !userName) return "";

    const lines: string[] = [];
    if (userName) lines.push(`The user's name is ${userName}.`);
    memories.forEach((m) => lines.push(`${m.key}: ${m.value}`));
    return `[PERSISTENT MEMORY]\n${lines.join("\n")}\n[END MEMORY]`;
  } catch {
    return "";
  }
}

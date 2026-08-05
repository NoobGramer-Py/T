import { useEffect, useCallback } from "react";
import {
  getAllSessions, loadSessionMessages, saveMessage,
  getProfile,
  getAllMemories,
} from "../lib/tauri";
import { useTStore } from "../store";

// Boots memory on first load: pulls profile + sessions + active session messages from SQLite into store.
export function useMemoryBoot() {
  const { memoryLoaded, setMemoryLoaded, setSessions, setActiveSessionId, setMessages, setProfile } = useTStore();

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
          vmName:        profileMap["vmName"]        ?? "",
          vmIp:          profileMap["vmIp"]          ?? "",
          vmSshUser:     profileMap["vmSshUser"]     ?? "",
          vmSshKey:      profileMap["vmSshKey"]      ?? "",
          vmSshPass:     profileMap["vmSshPass"]     ?? "",
        });

        // Load sessions
        const storedSessions = await getAllSessions();
        if (storedSessions.length > 0) {
          setSessions(storedSessions);
          const currentId = storedSessions[0].id;
          setActiveSessionId(currentId);
          const history = await loadSessionMessages(currentId);
          if (history.length > 0) {
            setMessages(history.map(m => ({ id: String(m.id), role: m.role, content: m.content, timestamp: m.timestamp })));
          }
        } else {
          // Default initial session
          setSessions([{ id: "default", title: "Main Chat", created_at: Date.now() }]);
        }
      } catch {
        // DB not available (browser dev mode) — no-op
      } finally {
        setMemoryLoaded(true);
      }
    };

    boot();
  }, [memoryLoaded, setMemoryLoaded, setSessions, setActiveSessionId, setMessages, setProfile]);
}

// Persists a message to SQLite under active session. Called by useChat after every send/receive.
export function usePersistMessage() {
  const activeSessionId = useTStore((s) => s.activeSessionId);
  return useCallback(async (role: "user" | "assistant", content: string, sessionId?: string) => {
    try {
      await saveMessage(sessionId || activeSessionId || "default", role, content, Date.now());
    } catch {
      // Non-critical — silently ignore in dev mode
    }
  }, [activeSessionId]);
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

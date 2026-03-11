import { useState, useEffect, useCallback } from "react";
import {
  listProcesses, killProcess, runScript,
  listDirectory, readFile, writeFile, deletePath,
  renamePath, createDirectory, searchFiles, getHomeDir,
  launchApp, getClipboard, setClipboard,
  addScheduledTask, getScheduledTasks, deleteScheduledTask, toggleScheduledTask,
  getClipboardHistory, saveClipboardEntry, clearClipboardHistory,
} from "../../lib/tauri";
import type { FileEntry, ScheduledTask, ClipboardEntry } from "../../lib/tauri";
import { useTStore } from "../../store";

// ─── Shared ───────────────────────────────────────────────────────────────────

type Tab = "stats" | "files" | "processes" | "script" | "scheduler" | "clipboard" | "launcher";

function SectionHeader({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 8, borderBottom: "1px solid rgba(255,179,0,0.08)" }}>
      <span style={{ fontSize: 14, color: "#ffb300", textShadow: "0 0 8px #ffb300" }}>{icon}</span>
      <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(255,179,0,0.6)" }}>{title}</span>
    </div>
  );
}

function Btn({ label, onClick, disabled = false, danger = false }: {
  label: string; onClick: () => void; disabled?: boolean; danger?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "5px 14px", fontSize: 8, letterSpacing: 2,
      background: danger ? "rgba(255,68,0,0.07)" : "rgba(255,179,0,0.07)",
      border: `1px solid ${danger ? "rgba(255,68,0,0.3)" : "rgba(255,179,0,0.25)"}`,
      color: danger ? "#ff4400" : "#ffb300",
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", opacity: disabled ? 0.4 : 1,
      transition: "all 0.2s ease",
    }}>
      {label}
    </button>
  );
}

// ─── Stats Tab ────────────────────────────────────────────────────────────────

function Gauge({ label, value, color }: { label: string; value: number; color: string }) {
  const clamped = Math.min(Math.max(value, 0), 100);
  const stroke  = 2 * Math.PI * 36;
  const dash    = (clamped / 100) * stroke;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <div style={{ position: "relative", width: 90, height: 90 }}>
        <svg width="90" height="90" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="45" cy="45" r="36" fill="none" stroke="rgba(255,179,0,0.08)" strokeWidth="4" />
          <circle cx="45" cy="45" r="36" fill="none" stroke={color} strokeWidth="4"
            strokeDasharray={`${dash} ${stroke}`} strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 14, fontWeight: "bold", color, textShadow: `0 0 8px ${color}` }}>{clamped.toFixed(0)}</span>
          <span style={{ fontSize: 7, color: "rgba(255,179,0,0.4)" }}>%</span>
        </div>
      </div>
      <div style={{ fontSize: 8, letterSpacing: 3, color: "rgba(255,179,0,0.5)" }}>{label}</div>
    </div>
  );
}

function StatsTab() {
  const stats = useTStore((s) => s.stats);
  const cpuColor  = stats.cpuPercent  > 80 ? "#ff4400" : "#ffb300";
  const ramColor  = stats.ramPercent  > 80 ? "#ff4400" : "#ffe566";
  const diskColor = stats.diskPercent > 85 ? "#ff4400" : "#ff6e00";

  const fmt = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return `${String(h).padStart(2,"0")}h ${String(m).padStart(2,"0")}m`;
  };

  return (
    <div>
      <SectionHeader title="SYSTEM VITALS" icon="◎" />
      <div style={{ display: "flex", gap: 32, marginBottom: 32, flexWrap: "wrap" }}>
        <Gauge label="CPU" value={stats.cpuPercent} color={cpuColor} />
        <Gauge label="RAM" value={stats.ramPercent} color={ramColor} />
        <Gauge label="DISK" value={stats.diskPercent} color={diskColor} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {[
          { label: "NETWORK RX", value: `${stats.networkRxKbps.toFixed(0)} KB/s` },
          { label: "NETWORK TX", value: `${stats.networkTxKbps.toFixed(0)} KB/s` },
          { label: "UPTIME",     value: fmt(stats.uptime) },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: "rgba(255,179,0,0.02)", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3, padding: "10px 14px" }}>
            <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(255,179,0,0.4)", marginBottom: 5 }}>{label}</div>
            <div style={{ fontSize: 13, color: "#ffb300", textShadow: "0 0 8px rgba(255,179,0,0.4)" }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── File Manager Tab ─────────────────────────────────────────────────────────

function FileManagerTab() {
  const [path, setPath]           = useState("");
  const [entries, setEntries]     = useState<FileEntry[]>([]);
  const [selected, setSelected]   = useState<FileEntry | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [editing, setEditing]     = useState(false);
  const [editContent, setEditContent] = useState("");
  const [newName, setNewName]     = useState("");
  const [searchQ, setSearchQ]     = useState("");
  const [searchRes, setSearchRes] = useState<{ path: string; name: string; is_dir: boolean }[] | null>(null);
  const [loading, setLoading]     = useState(false);
  const [status, setStatus]       = useState("");

  const loadHome = useCallback(async () => {
    try {
      const home = await getHomeDir();
      setPath(home);
      setEntries(await listDirectory(home));
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Error");
    }
  }, []);

  useEffect(() => { loadHome(); }, [loadHome]);

  const navigate = async (p: string) => {
    setLoading(true); setSelected(null); setFileContent(null); setSearchRes(null);
    try { setPath(p); setEntries(await listDirectory(p)); } catch (e) { setStatus(e instanceof Error ? e.message : "Error"); }
    finally { setLoading(false); }
  };

  const goUp = () => {
    const trimmed = (path.endsWith("\\") || path.endsWith("/")) ? path.slice(0, -1) : path;
    const lastSep = Math.max(trimmed.lastIndexOf("\\"), trimmed.lastIndexOf("/"));
    if (lastSep < 0) return;
    const parent = trimmed.slice(0, lastSep);
    // Windows drive root "C:" must stay as "C:\"
    const dest = /^[A-Za-z]:$/.test(parent) ? parent + "\\" : parent || "/";
    if (dest !== path) navigate(dest);
  };

  const open = async (entry: FileEntry) => {
    if (entry.is_dir) { navigate(entry.path); return; }
    setSelected(entry); setFileContent(null); setEditing(false);
    try {
      const content = await readFile(entry.path);
      setFileContent(content);
    } catch (e) { setFileContent(`[Cannot read: ${e instanceof Error ? e.message : "Error"}]`); }
  };

  const saveEdit = async () => {
    if (!selected) return;
    try { await writeFile(selected.path, editContent); setFileContent(editContent); setEditing(false); setStatus("Saved."); }
    catch (e) { setStatus(e instanceof Error ? e.message : "Save failed"); }
  };

  const del = async (entry: FileEntry) => {
    if (!window.confirm(`Delete "${entry.name}"?`)) return;
    try { await deletePath(entry.path); setEntries(await listDirectory(path)); setStatus(`Deleted: ${entry.name}`); }
    catch (e) { setStatus(e instanceof Error ? e.message : "Delete failed"); }
  };

  const rename = async (entry: FileEntry) => {
    if (!newName.trim()) return;
    const newPath = path + (path.endsWith("\\") || path.endsWith("/") ? "" : "/") + newName.trim();
    try { await renamePath(entry.path, newPath); setEntries(await listDirectory(path)); setNewName(""); setStatus(`Renamed to ${newName}`); }
    catch (e) { setStatus(e instanceof Error ? e.message : "Rename failed"); }
  };

  const mkdir = async () => {
    if (!newName.trim()) return;
    const newPath = path + "/" + newName.trim();
    try { await createDirectory(newPath); setEntries(await listDirectory(path)); setNewName(""); setStatus(`Created: ${newName}`); }
    catch (e) { setStatus(e instanceof Error ? e.message : "Failed"); }
  };

  const search = async () => {
    if (!searchQ.trim()) return;
    setLoading(true);
    try { setSearchRes(await searchFiles(path, searchQ)); } finally { setLoading(false); }
  };

  const fmtSize = (kb: number) => kb > 1024 ? `${(kb/1024).toFixed(1)} MB` : `${kb.toFixed(0)} KB`;
  const fmtDate = (ts: number) => new Date(ts * 1000).toLocaleDateString();

  return (
    <div>
      <SectionHeader title="FILE MANAGER" icon="⊞" />

      {/* Path bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        <Btn label="↑ UP" onClick={goUp} />
        <div style={{ flex: 1, background: "rgba(255,179,0,0.02)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", fontSize: 10, color: "rgba(255,179,0,0.7)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {path}
        </div>
      </div>

      {/* Search bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="search files in current directory..."
          style={{ flex: 1, background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
        />
        <Btn label={loading ? "···" : "SEARCH"} onClick={search} disabled={loading} />
        {searchRes && <Btn label="CLEAR" onClick={() => setSearchRes(null)} />}
      </div>

      {/* New folder / rename row */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="name for new folder or rename..."
          style={{ flex: 1, background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
        />
        <Btn label="NEW FOLDER" onClick={mkdir} />
        {selected && <Btn label="RENAME" onClick={() => rename(selected)} />}
      </div>

      {status && <div style={{ fontSize: 9, color: "rgba(255,179,0,0.5)", marginBottom: 8 }}>{status}</div>}

      <div style={{ display: "flex", gap: 12, height: 280 }}>
        {/* File list */}
        <div style={{ flex: 1, border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3, overflowY: "auto" }}>
          {searchRes !== null
            ? searchRes.map((entry) => (
              <div key={entry.path}
                onClick={() => {
                  if (entry.is_dir) {
                    navigate(entry.path);
                  } else {
                    const stub: FileEntry = { name: entry.name, path: entry.path, is_dir: false, size_kb: 0, modified: 0 };
                    setSelected(stub);
                    setFileContent(null);
                    setEditing(false);
                    readFile(entry.path).then(setFileContent).catch((e) => setFileContent(`[Cannot read: ${e instanceof Error ? e.message : "Error"}]`));
                  }
                }}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 10px", cursor: "pointer", borderBottom: "1px solid rgba(255,179,0,0.04)", background: "transparent", transition: "background 0.15s" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,179,0,0.04)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
              >
                <span style={{ fontSize: 12 }}>{entry.is_dir ? "📁" : "📄"}</span>
                <span style={{ flex: 1, fontSize: 10, color: entry.is_dir ? "#ffe566" : "rgba(255,179,0,0.8)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{entry.name}</span>
                <span style={{ fontSize: 8, color: "rgba(255,179,0,0.35)", maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>{entry.path}</span>
              </div>
            ))
            : entries.map((entry) => (
              <div key={entry.path} onClick={() => open(entry)}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 10px", cursor: "pointer", borderBottom: "1px solid rgba(255,179,0,0.04)", background: selected?.path === entry.path ? "rgba(255,179,0,0.06)" : "transparent", transition: "background 0.15s" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,179,0,0.04)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = selected?.path === entry.path ? "rgba(255,179,0,0.06)" : "transparent"; }}
              >
                <span style={{ fontSize: 12 }}>{entry.is_dir ? "📁" : "📄"}</span>
                <span style={{ flex: 1, fontSize: 10, color: entry.is_dir ? "#ffe566" : "rgba(255,179,0,0.8)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{entry.name}</span>
                {!entry.is_dir && <span style={{ fontSize: 8, color: "rgba(255,179,0,0.35)" }}>{fmtSize(entry.size_kb)}</span>}
                <span style={{ fontSize: 8, color: "rgba(255,179,0,0.25)" }}>{fmtDate(entry.modified)}</span>
                <button onClick={(e) => { e.stopPropagation(); del(entry); }}
                  style={{ fontSize: 8, padding: "1px 6px", background: "transparent", border: "1px solid rgba(255,68,0,0.2)", color: "#ff4400", cursor: "pointer", borderRadius: 2, fontFamily: "inherit" }}>
                  DEL
                </button>
              </div>
            ))
          }
        </div>

        {/* File preview / editor */}
        {selected && fileContent !== null && (
          <div style={{ width: 320, display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ fontSize: 8, color: "rgba(255,179,0,0.4)", letterSpacing: 2 }}>{selected.name}</div>
            {editing
              ? <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)}
                  style={{ flex: 1, resize: "none", background: "rgba(255,179,0,0.02)", border: "1px solid rgba(255,179,0,0.2)", borderRadius: 3, padding: "8px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none" }} />
              : <pre style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,179,0,0.07)", borderRadius: 3, padding: "8px", color: "rgba(255,179,0,0.75)", fontSize: 9, overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                  {fileContent}
                </pre>
            }
            <div style={{ display: "flex", gap: 6 }}>
              {editing
                ? <><Btn label="SAVE" onClick={saveEdit} /><Btn label="CANCEL" onClick={() => setEditing(false)} /></>
                : <Btn label="EDIT" onClick={() => { setEditing(true); setEditContent(fileContent); }} />
              }
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Process Manager Tab ──────────────────────────────────────────────────────

function ProcessTab() {
  const [procs, setProcs]     = useState<{ pid: number; name: string; cpu: number; mem_mb: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [killing, setKilling] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try { setProcs(await listProcesses()); } finally { setLoading(false); }
  };

  const kill = async (pid: number) => {
    if (!window.confirm(`Kill process PID ${pid}?`)) return;
    setKilling(pid);
    try { await killProcess(pid); await load(); } finally { setKilling(null); }
  };

  return (
    <div>
      <SectionHeader title="PROCESS MONITOR" icon="⊹" />
      <div style={{ marginBottom: 10 }}>
        <Btn label={loading ? "LOADING···" : "REFRESH"} onClick={load} disabled={loading} />
      </div>
      {procs.length > 0 && (
        <div style={{ maxHeight: 340, overflowY: "auto", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3 }}>
          <div style={{ display: "grid", gridTemplateColumns: "60px 1fr 70px 80px 60px", gap: 8, padding: "6px 12px", borderBottom: "1px solid rgba(255,179,0,0.1)", fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)" }}>
            <span>PID</span><span>NAME</span><span>CPU%</span><span>MEM MB</span><span></span>
          </div>
          {procs.slice(0, 80).map((p) => (
            <div key={p.pid} style={{ display: "grid", gridTemplateColumns: "60px 1fr 70px 80px 60px", gap: 8, padding: "5px 12px", borderBottom: "1px solid rgba(255,179,0,0.04)", fontSize: 10, color: "rgba(255,179,0,0.75)", alignItems: "center" }}>
              <span style={{ color: "rgba(255,179,0,0.4)", fontSize: 9 }}>{p.pid}</span>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</span>
              <span style={{ color: p.cpu > 50 ? "#ff4400" : "#ffb300" }}>{p.cpu.toFixed(1)}</span>
              <span>{p.mem_mb.toFixed(0)}</span>
              <button onClick={() => kill(p.pid)} disabled={killing === p.pid}
                style={{ fontSize: 8, padding: "2px 6px", background: "transparent", border: "1px solid rgba(255,68,0,0.3)", color: "#ff4400", cursor: "pointer", borderRadius: 2, fontFamily: "inherit", opacity: killing === p.pid ? 0.4 : 1 }}>
                KILL
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Script Executor Tab ──────────────────────────────────────────────────────

function ScriptTab() {
  const [script, setScript]   = useState("");
  const [shell, setShell]     = useState<"powershell" | "bash" | "python">("powershell");
  const [output, setOutput]   = useState("");
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!script.trim()) return;
    if (!window.confirm(`Execute via ${shell}?`)) return;
    setLoading(true); setOutput("");
    try { setOutput(await runScript(script, shell)); }
    catch (e) { setOutput(`ERROR: ${e instanceof Error ? e.message : "Unknown"}`); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <SectionHeader title="SCRIPT EXECUTOR" icon="⬡" />
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        {(["powershell", "bash", "python"] as const).map((s) => (
          <button key={s} onClick={() => setShell(s)} style={{
            padding: "4px 10px", fontSize: 7, letterSpacing: 2,
            background: shell === s ? "rgba(255,179,0,0.1)" : "transparent",
            border: `1px solid ${shell === s ? "rgba(255,179,0,0.4)" : "rgba(255,179,0,0.12)"}`,
            color: shell === s ? "#ffb300" : "rgba(255,179,0,0.35)",
            borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
          }}>{s.toUpperCase()}</button>
        ))}
      </div>
      <textarea value={script} onChange={(e) => setScript(e.target.value)} placeholder={`Enter ${shell} script...`} rows={5}
        style={{ width: "100%", resize: "vertical", background: "rgba(255,179,0,0.02)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "8px 12px", marginBottom: 8, color: "rgba(255,230,102,0.9)", fontSize: 11, lineHeight: 1.6, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.35)"; }}
        onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
      />
      <div style={{ marginBottom: output ? 10 : 0 }}>
        <Btn label={loading ? "EXECUTING···" : "EXECUTE"} onClick={run} disabled={loading || !script.trim()} />
      </div>
      {output && (
        <pre style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,179,0,0.08)", borderRadius: 3, padding: "10px 14px", color: "rgba(255,230,102,0.8)", fontSize: 10, lineHeight: 1.5, overflow: "auto", maxHeight: 200, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
          {output}
        </pre>
      )}
    </div>
  );
}

// ─── Scheduler Tab ────────────────────────────────────────────────────────────

function SchedulerTab() {
  const [tasks, setTasks]     = useState<ScheduledTask[]>([]);
  const [label, setLabel]     = useState("");
  const [command, setCommand] = useState("");
  const [shell, setShell]     = useState("powershell");
  const [runAt, setRunAt]     = useState("");
  const [repeatSecs, setRepeatSecs] = useState("0");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try { setTasks(await getScheduledTasks()); } catch { /* dev */ }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!label.trim() || !command.trim() || !runAt) return;
    setLoading(true);
    try {
      const ts = Math.floor(new Date(runAt).getTime() / 1000);
      await addScheduledTask(label.trim(), command.trim(), shell, ts, parseInt(repeatSecs) || 0);
      setLabel(""); setCommand(""); setRunAt(""); setRepeatSecs("0");
      await load();
    } finally { setLoading(false); }
  };

  const remove = async (id: number) => {
    try { await deleteScheduledTask(id); await load(); } catch { /* dev */ }
  };

  const toggle = async (id: number, enabled: boolean) => {
    try { await toggleScheduledTask(id, !enabled); await load(); } catch { /* dev */ }
  };

  const fmtDate = (ts: number) => new Date(ts * 1000).toLocaleString();

  return (
    <div>
      <SectionHeader title="TASK SCHEDULER" icon="◎" />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
        {[
          { label: "TASK LABEL", value: label, set: setLabel, placeholder: "e.g. Daily backup" },
          { label: "SHELL",      value: shell, set: setShell, placeholder: "powershell / bash / python" },
        ].map(({ label: l, value, set, placeholder }) => (
          <div key={l}>
            <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>{l}</div>
            <input value={value} onChange={(e) => set(e.target.value)} placeholder={placeholder}
              style={{ width: "100%", background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.35)"; }}
              onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
            />
          </div>
        ))}
      </div>
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>COMMAND</div>
        <input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="script or command to run"
          style={{ width: "100%", background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.35)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>RUN AT</div>
          <input type="datetime-local" value={runAt} onChange={(e) => setRunAt(e.target.value)}
            style={{ width: "100%", background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", colorScheme: "dark" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.35)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
          />
        </div>
        <div>
          <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(255,179,0,0.4)", marginBottom: 4 }}>REPEAT (SECONDS, 0 = ONCE)</div>
          <input type="number" value={repeatSecs} onChange={(e) => setRepeatSecs(e.target.value)} min="0"
            style={{ width: "100%", background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "5px 10px", color: "rgba(255,230,102,0.9)", fontSize: 10, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.35)"; }}
            onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
          />
        </div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <Btn label={loading ? "ADDING···" : "ADD TASK"} onClick={add} disabled={loading} />
      </div>

      {tasks.length === 0
        ? <div style={{ fontSize: 9, color: "rgba(255,179,0,0.25)", fontStyle: "italic" }}>No scheduled tasks.</div>
        : tasks.map((t) => (
          <div key={t.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", marginBottom: 4, background: "rgba(255,179,0,0.02)", border: "1px solid rgba(255,179,0,0.07)", borderRadius: 3, opacity: t.enabled ? 1 : 0.45 }}>
            <div style={{ flex: 1 }}>
              <div style={{ color: "#ffe566", fontSize: 10 }}>{t.label}</div>
              <div style={{ color: "rgba(255,179,0,0.45)", fontSize: 9 }}>{t.command} · {t.shell}</div>
              <div style={{ color: "rgba(255,179,0,0.3)", fontSize: 8, marginTop: 2 }}>Run at: {fmtDate(t.run_at)}{t.repeat_secs > 0 ? ` · repeat every ${t.repeat_secs}s` : ""}</div>
            </div>
            <Btn label={t.enabled ? "DISABLE" : "ENABLE"} onClick={() => toggle(t.id, t.enabled)} />
            <Btn label="DEL" onClick={() => remove(t.id)} danger />
          </div>
        ))
      }
    </div>
  );
}

// ─── Clipboard Tab ────────────────────────────────────────────────────────────

function ClipboardTab() {
  const [history, setHistory] = useState<ClipboardEntry[]>([]);
  const [current, setCurrent] = useState("");

  const loadHistory = async () => {
    try { setHistory(await getClipboardHistory()); } catch { /* dev */ }
  };

  const readClip = async () => {
    try {
      const text = await getClipboard();
      setCurrent(text);
      if (text) { await saveClipboardEntry(text); await loadHistory(); }
    } catch { /* dev */ }
  };

  const copyItem = async (content: string) => {
    try { await setClipboard(content); setCurrent(content); } catch { /* dev */ }
  };

  const clearHistory = async () => {
    try { await clearClipboardHistory(); setHistory([]); } catch { /* dev */ }
  };

  useEffect(() => { loadHistory(); }, []);

  return (
    <div>
      <SectionHeader title="CLIPBOARD MANAGER" icon="⊹" />
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <Btn label="READ CLIPBOARD" onClick={readClip} />
        <Btn label="CLEAR HISTORY" onClick={clearHistory} danger />
      </div>

      {current && (
        <div style={{ background: "rgba(255,179,0,0.04)", border: "1px solid rgba(255,179,0,0.2)", borderRadius: 3, padding: "10px 14px", marginBottom: 14 }}>
          <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(255,179,0,0.4)", marginBottom: 5 }}>CURRENT CLIPBOARD</div>
          <div style={{ fontSize: 11, color: "rgba(255,230,102,0.9)", wordBreak: "break-all" }}>{current}</div>
        </div>
      )}

      {history.length === 0
        ? <div style={{ fontSize: 9, color: "rgba(255,179,0,0.25)", fontStyle: "italic" }}>No clipboard history.</div>
        : history.map((h) => (
          <div key={h.id} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "7px 12px", marginBottom: 3, background: "rgba(255,179,0,0.02)", border: "1px solid rgba(255,179,0,0.07)", borderRadius: 3 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: "rgba(255,179,0,0.8)", wordBreak: "break-all", maxHeight: 40, overflow: "hidden" }}>{h.content}</div>
              <div style={{ fontSize: 8, color: "rgba(255,179,0,0.3)", marginTop: 3 }}>{new Date(h.saved_at * 1000).toLocaleString()}</div>
            </div>
            <Btn label="COPY" onClick={() => copyItem(h.content)} />
          </div>
        ))
      }
    </div>
  );
}

// ─── App Launcher Tab ─────────────────────────────────────────────────────────

const QUICK_APPS = [
  { name: "notepad",     label: "Notepad"     },
  { name: "calc",        label: "Calculator"  },
  { name: "explorer",    label: "Explorer"    },
  { name: "msedge",      label: "Edge"        },
  { name: "cmd",         label: "CMD"         },
  { name: "powershell",  label: "PowerShell"  },
  { name: "taskmgr",     label: "Task Mgr"    },
  { name: "control",     label: "Control"     },
];

function LauncherTab() {
  const [appName, setAppName] = useState("");
  const [status, setStatus]   = useState("");

  const launch = async (name: string) => {
    try {
      const result = await launchApp(name);
      setStatus(result);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Launch failed");
    }
  };

  return (
    <div>
      <SectionHeader title="APP LAUNCHER" icon="◎" />
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <input value={appName} onChange={(e) => setAppName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && launch(appName)}
          placeholder="application name..."
          style={{ flex: 1, background: "rgba(255,179,0,0.03)", border: "1px solid rgba(255,179,0,0.12)", borderRadius: 3, padding: "6px 10px", color: "rgba(255,230,102,0.9)", fontSize: 11, fontFamily: "inherit", outline: "none", caretColor: "#ffb300" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.4)"; }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = "rgba(255,179,0,0.12)"; }}
        />
        <Btn label="LAUNCH" onClick={() => launch(appName)} disabled={!appName.trim()} />
      </div>

      {status && <div style={{ fontSize: 9, color: "rgba(255,179,0,0.5)", marginBottom: 14 }}>{status}</div>}

      <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(255,179,0,0.35)", marginBottom: 12 }}>QUICK LAUNCH</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {QUICK_APPS.map((app) => (
          <button key={app.name} onClick={() => launch(app.name)} style={{
            padding: "8px 16px", fontSize: 8, letterSpacing: 2,
            background: "rgba(255,179,0,0.04)", border: "1px solid rgba(255,179,0,0.15)",
            color: "rgba(255,179,0,0.7)", borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
            transition: "all 0.2s ease",
          }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,179,0,0.1)"; (e.currentTarget as HTMLButtonElement).style.color = "#ffb300"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,179,0,0.04)"; (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,179,0,0.7)"; }}
          >
            {app.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Main Panel ───────────────────────────────────────────────────────────────

const TABS: { id: Tab; label: string }[] = [
  { id: "stats",     label: "VITALS"    },
  { id: "files",     label: "FILES"     },
  { id: "processes", label: "PROCESSES" },
  { id: "script",    label: "SCRIPT"    },
  { id: "scheduler", label: "SCHEDULER" },
  { id: "clipboard", label: "CLIPBOARD" },
  { id: "launcher",  label: "LAUNCHER"  },
];

export function SystemPanel() {
  const [tab, setTab] = useState<Tab>("stats");

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Tab bar */}
      <div style={{ display: "flex", gap: 2, padding: "12px 16px 0", borderBottom: "1px solid rgba(255,179,0,0.08)", flexShrink: 0 }}>
        {TABS.map(({ id, label }) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "6px 12px", fontSize: 7, letterSpacing: 3,
            background: tab === id ? "rgba(255,179,0,0.08)" : "transparent",
            border: "none", borderBottom: `2px solid ${tab === id ? "#ffb300" : "transparent"}`,
            color: tab === id ? "#ffb300" : "rgba(255,179,0,0.35)",
            cursor: "pointer", fontFamily: "inherit",
            transition: "all 0.2s ease",
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {tab === "stats"     && <StatsTab />}
        {tab === "files"     && <FileManagerTab />}
        {tab === "processes" && <ProcessTab />}
        {tab === "script"    && <ScriptTab />}
        {tab === "scheduler" && <SchedulerTab />}
        {tab === "clipboard" && <ClipboardTab />}
        {tab === "launcher"  && <LauncherTab />}
      </div>
    </div>
  );
}

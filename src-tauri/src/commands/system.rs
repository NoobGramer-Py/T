use serde::{Deserialize, Serialize};
use sysinfo::{System, Disks, Networks};
use std::process::Command;
use std::path::{Path, PathBuf};
use std::fs;

// ─── System Stats ─────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct SystemStats {
    pub cpu_percent:  f32,
    pub ram_percent:  f32,
    pub disk_percent: f32,
    pub uptime_secs:  u64,
    pub net_rx_kbps:  f64,
    pub net_tx_kbps:  f64,
}

#[tauri::command]
pub fn get_system_stats() -> Result<SystemStats, String> {
    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu       = sys.global_cpu_usage();
    let ram_used  = sys.used_memory()  as f32;
    let ram_total = sys.total_memory() as f32;
    let ram_pct   = if ram_total > 0.0 { (ram_used / ram_total) * 100.0 } else { 0.0 };

    let disks = Disks::new_with_refreshed_list();
    let (used, total) = disks.iter().fold((0u64, 0u64), |(u, t), d| {
        (u + d.total_space() - d.available_space(), t + d.total_space())
    });
    let disk_pct = if total > 0 { (used as f32 / total as f32) * 100.0 } else { 0.0 };

    let mut nets = Networks::new_with_refreshed_list();
    std::thread::sleep(std::time::Duration::from_millis(200));
    nets.refresh();
    let (rx, tx) = nets.iter().fold((0u64, 0u64), |(r, t), (_, n)| {
        (r + n.received(), t + n.transmitted())
    });

    Ok(SystemStats {
        cpu_percent:  cpu,
        ram_percent:  ram_pct,
        disk_percent: disk_pct,
        uptime_secs:  System::uptime(),
        net_rx_kbps:  rx as f64 / 1024.0 / 0.2,
        net_tx_kbps:  tx as f64 / 1024.0 / 0.2,
    })
}

// ─── Process Manager ──────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct ProcessInfo {
    pub pid:    u32,
    pub name:   String,
    pub cpu:    f32,
    pub mem_mb: f64,
}

#[tauri::command]
pub fn list_processes() -> Result<Vec<ProcessInfo>, String> {
    let mut sys = System::new_all();
    sys.refresh_all();
    let mut procs: Vec<ProcessInfo> = sys.processes().values().map(|p| ProcessInfo {
        pid:    p.pid().as_u32(),
        name:   p.name().to_string_lossy().to_string(),
        cpu:    p.cpu_usage(),
        mem_mb: p.memory() as f64 / 1_048_576.0,
    }).collect();
    procs.sort_by(|a, b| b.cpu.partial_cmp(&a.cpu).unwrap_or(std::cmp::Ordering::Equal));
    Ok(procs)
}

#[tauri::command]
pub fn kill_process(pid: u32) -> Result<(), String> {
    let mut sys = System::new_all();
    sys.refresh_all();
    sys.process(sysinfo::Pid::from_u32(pid))
        .ok_or_else(|| format!("Process {} not found", pid))?
        .kill();
    Ok(())
}

// ─── Script Executor ──────────────────────────────────────────────────────────

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Shell { Bash, Powershell, Python }

#[tauri::command]
pub fn run_script(script: String, shell: Shell) -> Result<String, String> {
    let out = match shell {
        Shell::Powershell => Command::new("powershell").args(["-NoProfile", "-Command", &script]).output(),
        Shell::Bash       => Command::new("bash").args(["-c", &script]).output(),
        Shell::Python     => Command::new("python").args(["-c", &script]).output(),
    }.map_err(|e| format!("Execution failed: {}", e))?;

    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    let stderr = String::from_utf8_lossy(&out.stderr).to_string();
    Ok(if stderr.is_empty() { stdout } else { format!("{}\nSTDERR:\n{}", stdout, stderr) })
}

// ─── File Manager ─────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct FileEntry {
    pub name:     String,
    pub path:     String,
    pub is_dir:   bool,
    pub size_kb:  f64,
    pub modified: i64,
}

fn validate_path(path: &str) -> Result<PathBuf, String> {
    if path.contains("..") {
        return Err("Path traversal not allowed".into());
    }
    Ok(PathBuf::from(path))
}

#[tauri::command]
pub fn list_directory(path: String) -> Result<Vec<FileEntry>, String> {
    let dir = validate_path(&path)?;
    let mut files: Vec<FileEntry> = fs::read_dir(&dir)
        .map_err(|e| format!("Cannot read directory: {}", e))?
        .filter_map(|e| e.ok())
        .map(|e| {
            let meta     = e.metadata().ok();
            let is_dir   = meta.as_ref().map(|m| m.is_dir()).unwrap_or(false);
            let size_kb  = meta.as_ref().map(|m| m.len() as f64 / 1024.0).unwrap_or(0.0);
            let modified = meta.as_ref()
                .and_then(|m| m.modified().ok())
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| d.as_secs() as i64).unwrap_or(0);
            FileEntry {
                name: e.file_name().to_string_lossy().to_string(),
                path: e.path().to_string_lossy().to_string(),
                is_dir, size_kb, modified,
            }
        }).collect();

    files.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then(a.name.to_lowercase().cmp(&b.name.to_lowercase())));
    Ok(files)
}

#[tauri::command]
pub fn read_file(path: String) -> Result<String, String> {
    let p = validate_path(&path)?;
    let meta = fs::metadata(&p).map_err(|e| e.to_string())?;
    if meta.len() > 1_048_576 {
        return Err("File too large to display (>1 MB). Open externally.".into());
    }
    fs::read_to_string(&p).map_err(|e| format!("Cannot read file: {}", e))
}

#[tauri::command]
pub fn write_file(path: String, content: String) -> Result<(), String> {
    let p = validate_path(&path)?;
    if let Some(parent) = p.parent() { fs::create_dir_all(parent).map_err(|e| e.to_string())?; }
    fs::write(&p, content).map_err(|e| format!("Cannot write: {}", e))
}

#[tauri::command]
pub fn delete_path(path: String) -> Result<(), String> {
    let p = validate_path(&path)?;
    if p.is_dir() { fs::remove_dir_all(&p) } else { fs::remove_file(&p) }
        .map_err(|e| format!("Cannot delete: {}", e))
}

#[tauri::command]
pub fn rename_path(from: String, to: String) -> Result<(), String> {
    fs::rename(validate_path(&from)?, validate_path(&to)?)
        .map_err(|e| format!("Cannot rename: {}", e))
}

#[tauri::command]
pub fn create_directory(path: String) -> Result<(), String> {
    fs::create_dir_all(validate_path(&path)?)
        .map_err(|e| format!("Cannot create directory: {}", e))
}

#[derive(Serialize)]
pub struct SearchResult {
    pub path:   String,
    pub name:   String,
    pub is_dir: bool,
}

#[tauri::command]
pub fn search_files(root: String, query: String) -> Result<Vec<SearchResult>, String> {
    let root_path = validate_path(&root)?;
    let q = query.to_lowercase();
    let mut found = Vec::new();
    search_recursive(&root_path, &q, &mut found, 0);
    Ok(found)
}

fn search_recursive(dir: &Path, query: &str, results: &mut Vec<SearchResult>, depth: u8) {
    if depth > 5 || results.len() >= 200 { return; }
    let Ok(entries) = fs::read_dir(dir) else { return };
    for entry in entries.filter_map(|e| e.ok()) {
        let name   = entry.file_name().to_string_lossy().to_lowercase();
        let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
        if name.contains(query) {
            results.push(SearchResult {
                path:  entry.path().to_string_lossy().to_string(),
                name:  entry.file_name().to_string_lossy().to_string(),
                is_dir,
            });
        }
        if is_dir { search_recursive(&entry.path(), query, results, depth + 1); }
    }
}

#[tauri::command]
pub fn get_home_dir() -> Result<String, String> {
    dirs::home_dir()
        .map(|p| p.to_string_lossy().to_string())
        .ok_or_else(|| "Cannot determine home directory".into())
}

// ─── App Launcher ─────────────────────────────────────────────────────────────

#[tauri::command]
pub fn launch_app(name: String) -> Result<String, String> {
    if name.chars().any(|c| !c.is_alphanumeric() && c != ' ' && c != '.' && c != '-' && c != '_') {
        return Err("Invalid application name: illegal characters".into());
    }
    let result = if cfg!(target_os = "windows") {
        Command::new("cmd").args(["/C", "start", "", &name]).spawn()
    } else {
        Command::new(&name).spawn()
    };
    match result {
        Ok(_)  => Ok(format!("Launched: {}", name)),
        Err(e) => Err(format!("Failed to launch '{}': {}", name, e)),
    }
}

// ─── Clipboard ────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn get_clipboard() -> Result<String, String> {
    if cfg!(target_os = "windows") {
        let out = Command::new("powershell")
            .args(["-NoProfile", "-Command", "Get-Clipboard"])
            .output().map_err(|e| e.to_string())?;
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    } else {
        let out = Command::new("xclip").args(["-selection", "clipboard", "-o"]).output()
            .or_else(|_| Command::new("pbpaste").output())
            .map_err(|e| e.to_string())?;
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    }
}

#[tauri::command]
pub fn set_clipboard(content: String) -> Result<(), String> {
    if cfg!(target_os = "windows") {
        // Write content to a temp file and use Get-Content to avoid quoting issues
        let tmp_path = std::env::temp_dir().join("t_clip.txt");
        std::fs::write(&tmp_path, &content).map_err(|e| e.to_string())?;
        let cmd = format!(
            "Get-Content -Raw -Path '{}' | Set-Clipboard",
            tmp_path.to_string_lossy().replace('\'', "''")
        );
        Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &cmd])
            .output()
            .map_err(|e| format!("Clipboard write failed: {}", e))?;
        std::fs::remove_file(&tmp_path).ok();
    } else {
        let mut child = Command::new("xclip")
            .args(["-selection", "clipboard"])
            .stdin(std::process::Stdio::piped())
            .spawn()
            .or_else(|_| Command::new("pbcopy").stdin(std::process::Stdio::piped()).spawn())
            .map_err(|e| e.to_string())?;
        if let Some(stdin) = child.stdin.as_mut() {
            use std::io::Write;
            stdin.write_all(content.as_bytes()).map_err(|e| e.to_string())?;
        }
        child.wait().map_err(|e| e.to_string())?;
    }
    Ok(())
}

use serde::Serialize;
use crate::db::memory as db;

// ─── Messages ─────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn save_message(role: String, content: String, timestamp: i64) -> Result<(), String> {
    db::save_message(&role, &content, timestamp).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn load_recent_messages(limit: u32) -> Result<Vec<db::StoredMessage>, String> {
    db::load_recent_messages(limit).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn clear_messages() -> Result<(), String> {
    db::clear_messages().map_err(|e| e.to_string())
}

// ─── Memories ─────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn set_memory(key: String, value: String) -> Result<(), String> {
    db::set_memory(&key, &value).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_all_memories() -> Result<Vec<db::Memory>, String> {
    db::get_all_memories().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_memory(key: String) -> Result<(), String> {
    db::delete_memory(&key).map_err(|e| e.to_string())
}

// ─── Profile ──────────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct ProfileEntry {
    pub key:   String,
    pub value: String,
}

#[tauri::command]
pub fn set_profile(key: String, value: String) -> Result<(), String> {
    db::set_profile(&key, &value).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_profile() -> Result<Vec<ProfileEntry>, String> {
    Ok(db::get_profile().map_err(|e| e.to_string())?
        .into_iter().map(|(k, v)| ProfileEntry { key: k, value: v }).collect())
}

// ─── Tasks ────────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn add_task(title: String, detail: String) -> Result<i64, String> {
    db::add_task(&title, &detail).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_tasks(status_filter: Option<String>) -> Result<Vec<db::Task>, String> {
    db::get_tasks(status_filter.as_deref()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn complete_task(id: i64) -> Result<(), String> {
    db::complete_task(id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_task(id: i64) -> Result<(), String> {
    db::delete_task(id).map_err(|e| e.to_string())
}

// ─── Scheduled Tasks ──────────────────────────────────────────────────────────

#[tauri::command]
pub fn add_scheduled_task(label: String, command: String, shell: String, run_at: i64, repeat_secs: i64) -> Result<i64, String> {
    db::add_scheduled_task(&label, &command, &shell, run_at, repeat_secs).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_scheduled_tasks() -> Result<Vec<db::ScheduledTask>, String> {
    db::get_scheduled_tasks().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn delete_scheduled_task(id: i64) -> Result<(), String> {
    db::delete_scheduled_task(id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn toggle_scheduled_task(id: i64, enabled: bool) -> Result<(), String> {
    db::toggle_scheduled_task(id, enabled).map_err(|e| e.to_string())
}

// ─── Clipboard History ────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct ClipboardEntry {
    pub id:       i64,
    pub content:  String,
    pub saved_at: i64,
}

#[tauri::command]
pub fn save_clipboard_entry(content: String) -> Result<(), String> {
    db::save_clipboard_entry(&content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_clipboard_history() -> Result<Vec<ClipboardEntry>, String> {
    Ok(db::get_clipboard_history().map_err(|e| e.to_string())?
        .into_iter().map(|(id, content, saved_at)| ClipboardEntry { id, content, saved_at }).collect())
}

#[tauri::command]
pub fn clear_clipboard_history() -> Result<(), String> {
    db::clear_clipboard_history().map_err(|e| e.to_string())
}

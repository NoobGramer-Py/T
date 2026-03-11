use rusqlite::params;
use serde::{Deserialize, Serialize};
use crate::db::open;

fn now_secs() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

// ─── Messages ─────────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct StoredMessage {
    pub id:        i64,
    pub role:      String,
    pub content:   String,
    pub timestamp: i64,
}

pub fn save_message(role: &str, content: &str, timestamp: i64) -> rusqlite::Result<()> {
    let conn = open()?;
    conn.execute(
        "INSERT INTO messages (role, content, timestamp) VALUES (?1, ?2, ?3)",
        params![role, content, timestamp],
    )?;
    Ok(())
}

pub fn load_recent_messages(limit: u32) -> rusqlite::Result<Vec<StoredMessage>> {
    let conn = open()?;
    let mut stmt = conn.prepare(
        "SELECT id, role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?1"
    )?;
    let mut msgs: Vec<StoredMessage> = stmt.query_map(params![limit], |row| {
        Ok(StoredMessage {
            id: row.get(0)?, role: row.get(1)?,
            content: row.get(2)?, timestamp: row.get(3)?,
        })
    })?.filter_map(|r| r.ok()).collect();
    msgs.reverse();
    Ok(msgs)
}

pub fn clear_messages() -> rusqlite::Result<()> {
    open()?.execute("DELETE FROM messages", [])?;
    Ok(())
}

// ─── Key-Value Memories ───────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct Memory {
    pub key:     String,
    pub value:   String,
    pub updated: i64,
}

pub fn set_memory(key: &str, value: &str) -> rusqlite::Result<()> {
    let conn = open()?;
    conn.execute(
        "INSERT INTO memories (key, value, updated) VALUES (?1, ?2, ?3)
         ON CONFLICT(key) DO UPDATE SET value = ?2, updated = ?3",
        params![key, value, now_secs()],
    )?;
    Ok(())
}

pub fn get_all_memories() -> rusqlite::Result<Vec<Memory>> {
    let conn = open()?;
    let mut stmt = conn.prepare(
        "SELECT key, value, updated FROM memories ORDER BY updated DESC"
    )?;
    let result: Vec<Memory> = stmt.query_map([], |row| {
        Ok(Memory { key: row.get(0)?, value: row.get(1)?, updated: row.get(2)? })
    })?.filter_map(|r| r.ok()).collect();
    Ok(result)
}

pub fn delete_memory(key: &str) -> rusqlite::Result<()> {
    open()?.execute("DELETE FROM memories WHERE key = ?1", params![key])?;
    Ok(())
}

// ─── Profile ──────────────────────────────────────────────────────────────────

pub fn set_profile(key: &str, value: &str) -> rusqlite::Result<()> {
    open()?.execute(
        "INSERT INTO profile (key, value) VALUES (?1, ?2)
         ON CONFLICT(key) DO UPDATE SET value = ?2",
        params![key, value],
    )?;
    Ok(())
}

pub fn get_profile() -> rusqlite::Result<Vec<(String, String)>> {
    let conn = open()?;
    let mut stmt = conn.prepare("SELECT key, value FROM profile ORDER BY key")?;
    let result: Vec<(String, String)> = stmt
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))?
        .filter_map(|r| r.ok())
        .collect();
    Ok(result)
}

// ─── Tasks ────────────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct Task {
    pub id:         i64,
    pub title:      String,
    pub detail:     String,
    pub status:     String,
    pub created_at: i64,
}

pub fn add_task(title: &str, detail: &str) -> rusqlite::Result<i64> {
    let conn = open()?;
    conn.execute(
        "INSERT INTO tasks (title, detail, created_at) VALUES (?1, ?2, ?3)",
        params![title, detail, now_secs()],
    )?;
    Ok(conn.last_insert_rowid())
}

pub fn get_tasks(status_filter: Option<&str>) -> rusqlite::Result<Vec<Task>> {
    let conn = open()?;
    let map_row = |row: &rusqlite::Row| {
        Ok(Task {
            id: row.get(0)?, title: row.get(1)?, detail: row.get(2)?,
            status: row.get(3)?, created_at: row.get(4)?,
        })
    };
    match status_filter {
        Some(filter) => {
            let mut stmt = conn.prepare(
                "SELECT id, title, detail, status, created_at FROM tasks WHERE status = ?1 ORDER BY created_at DESC"
            )?;
            let result: Vec<Task> = stmt
                .query_map(params![filter], map_row)?
                .filter_map(|r| r.ok())
                .collect();
            Ok(result)
        }
        None => {
            let mut stmt = conn.prepare(
                "SELECT id, title, detail, status, created_at FROM tasks ORDER BY created_at DESC"
            )?;
            let result: Vec<Task> = stmt
                .query_map([], map_row)?
                .filter_map(|r| r.ok())
                .collect();
            Ok(result)
        }
    }
}

pub fn complete_task(id: i64) -> rusqlite::Result<()> {
    open()?.execute("UPDATE tasks SET status = 'done' WHERE id = ?1", params![id])?;
    Ok(())
}

pub fn delete_task(id: i64) -> rusqlite::Result<()> {
    open()?.execute("DELETE FROM tasks WHERE id = ?1", params![id])?;
    Ok(())
}

// ─── Scheduled Tasks ──────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct ScheduledTask {
    pub id:          i64,
    pub label:       String,
    pub command:     String,
    pub shell:       String,
    pub run_at:      i64,
    pub repeat_secs: i64,
    pub last_ran:    i64,
    pub enabled:     bool,
}

pub fn add_scheduled_task(
    label: &str, command: &str, shell: &str, run_at: i64, repeat_secs: i64,
) -> rusqlite::Result<i64> {
    let conn = open()?;
    conn.execute(
        "INSERT INTO scheduled_tasks (label, command, shell, run_at, repeat_secs) VALUES (?1,?2,?3,?4,?5)",
        params![label, command, shell, run_at, repeat_secs],
    )?;
    Ok(conn.last_insert_rowid())
}

pub fn get_scheduled_tasks() -> rusqlite::Result<Vec<ScheduledTask>> {
    let conn = open()?;
    let mut stmt = conn.prepare(
        "SELECT id, label, command, shell, run_at, repeat_secs, last_ran, enabled \
         FROM scheduled_tasks ORDER BY run_at ASC"
    )?;
    let result: Vec<ScheduledTask> = stmt.query_map([], |row| {
        Ok(ScheduledTask {
            id: row.get(0)?, label: row.get(1)?, command: row.get(2)?,
            shell: row.get(3)?, run_at: row.get(4)?, repeat_secs: row.get(5)?,
            last_ran: row.get(6)?, enabled: row.get::<_, i64>(7)? == 1,
        })
    })?.filter_map(|r| r.ok()).collect();
    Ok(result)
}

pub fn delete_scheduled_task(id: i64) -> rusqlite::Result<()> {
    open()?.execute("DELETE FROM scheduled_tasks WHERE id = ?1", params![id])?;
    Ok(())
}

pub fn toggle_scheduled_task(id: i64, enabled: bool) -> rusqlite::Result<()> {
    open()?.execute(
        "UPDATE scheduled_tasks SET enabled = ?1 WHERE id = ?2",
        params![enabled as i64, id],
    )?;
    Ok(())
}

// ─── Clipboard History ────────────────────────────────────────────────────────

pub fn save_clipboard_entry(content: &str) -> rusqlite::Result<()> {
    let conn = open()?;
    let last: Option<String> = conn.query_row(
        "SELECT content FROM clipboard_history ORDER BY id DESC LIMIT 1",
        [], |r| r.get(0),
    ).ok();
    if last.as_deref() == Some(content) { return Ok(()); }
    conn.execute(
        "INSERT INTO clipboard_history (content, saved_at) VALUES (?1, ?2)",
        params![content, now_secs()],
    )?;
    conn.execute(
        "DELETE FROM clipboard_history WHERE id NOT IN \
         (SELECT id FROM clipboard_history ORDER BY id DESC LIMIT 50)",
        [],
    )?;
    Ok(())
}

pub fn get_clipboard_history() -> rusqlite::Result<Vec<(i64, String, i64)>> {
    let conn = open()?;
    let mut stmt = conn.prepare(
        "SELECT id, content, saved_at FROM clipboard_history ORDER BY id DESC"
    )?;
    let result: Vec<(i64, String, i64)> = stmt
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)))?
        .filter_map(|r| r.ok())
        .collect();
    Ok(result)
}

pub fn clear_clipboard_history() -> rusqlite::Result<()> {
    open()?.execute("DELETE FROM clipboard_history", [])?;
    Ok(())
}

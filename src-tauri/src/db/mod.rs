pub mod memory;

use rusqlite::Connection;
use std::path::PathBuf;

pub fn db_path() -> PathBuf {
    let base = dirs::data_local_dir().unwrap_or_else(|| PathBuf::from("."));
    base.join("T").join("memory.db")
}

pub fn open() -> rusqlite::Result<Connection> {
    let path = db_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let conn = Connection::open(&path)?;
    init_schema(&conn)?;
    Ok(conn)
}

fn init_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch("
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role      TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
            content   TEXT    NOT NULL,
            timestamp INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memories (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            key     TEXT    NOT NULL UNIQUE,
            value   TEXT    NOT NULL,
            updated INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profile (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT    NOT NULL,
            detail     TEXT    NOT NULL DEFAULT '',
            status     TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            label       TEXT    NOT NULL,
            command     TEXT    NOT NULL,
            shell       TEXT    NOT NULL DEFAULT 'powershell',
            run_at      INTEGER NOT NULL,
            repeat_secs INTEGER NOT NULL DEFAULT 0,
            last_ran    INTEGER NOT NULL DEFAULT 0,
            enabled     INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS clipboard_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            content   TEXT    NOT NULL,
            saved_at  INTEGER NOT NULL
        );
    ")
}

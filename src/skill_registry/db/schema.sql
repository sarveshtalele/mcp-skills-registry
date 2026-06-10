-- Schema for the MCP Skill Registry.
-- Skills themselves live on disk under skills/; these tables hold runtime data:
-- execution history and the audit trail. Indexes are declared separately
-- (SQLite does not support inline INDEX clauses).

CREATE TABLE IF NOT EXISTS executions (
    execution_id     TEXT PRIMARY KEY,
    skill_name       TEXT NOT NULL,
    version          TEXT,
    user_id          TEXT,
    status           TEXT NOT NULL,
    error            TEXT,
    duration_ms      REAL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_exec_skill ON executions (skill_name);
CREATE INDEX IF NOT EXISTS idx_exec_user ON executions (user_id);
CREATE INDEX IF NOT EXISTS idx_exec_status ON executions (status);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type       TEXT NOT NULL,
    action           TEXT NOT NULL,
    status           TEXT NOT NULL,
    skill_name       TEXT,
    user_id          TEXT,
    error            TEXT,
    metadata_json    TEXT,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at);

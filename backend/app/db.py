"""SQLite schema and connection helpers.

No vector column, no external embedding service. Retrieval relies on
structured metadata filtering plus SQLite FTS5 (trigram tokenizer).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "tarot.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    stages      TEXT NOT NULL,
    scenes      TEXT NOT NULL,
    tags        TEXT NOT NULL,
    version     TEXT NOT NULL,
    updated     TEXT NOT NULL,
    source      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    INTEGER PRIMARY KEY,
    doc_id      TEXT NOT NULL REFERENCES documents(doc_id),
    section     TEXT NOT NULL,
    stages      TEXT NOT NULL,
    scenes      TEXT NOT NULL,
    tags        TEXT NOT NULL,
    text        TEXT NOT NULL,
    version     TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    section, tags, text, tokenize='trigram'
);

CREATE TABLE IF NOT EXISTS cards (
    card_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    label       TEXT NOT NULL,
    arcana      TEXT NOT NULL,
    suit        TEXT,
    rank        TEXT,
    number      INTEGER,
    upright     TEXT NOT NULL,
    reversed    TEXT NOT NULL,
    doc_id      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS card_profiles (
    card_id       TEXT PRIMARY KEY,
    name          TEXT,
    english       TEXT,
    number        TEXT,
    arcana        TEXT,
    correspondence TEXT,
    keywords      TEXT,
    imagery       TEXT,
    upright       TEXT,
    reversed      TEXT,
    symbolism     TEXT,
    love          TEXT,
    career        TEXT,
    study         TEXT,
    source        TEXT
);

CREATE TABLE IF NOT EXISTS spreads (
    spread_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    card_count  INTEGER NOT NULL,
    difficulty  TEXT,
    suitable    TEXT,
    doc_id      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    spread_id   TEXT NOT NULL REFERENCES spreads(spread_id),
    seq         INTEGER NOT NULL,
    name        TEXT NOT NULL,
    meaning     TEXT NOT NULL,
    PRIMARY KEY (spread_id, seq)
);

CREATE TABLE IF NOT EXISTS scenes (
    scene_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    topics      TEXT,
    recommended TEXT,
    focus       TEXT,
    tags        TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    scene_id    TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    text        TEXT NOT NULL,
    PRIMARY KEY (scene_id, seq)
);

CREATE TABLE IF NOT EXISTS routes (
    stage       TEXT PRIMARY KEY,
    required    TEXT NOT NULL,
    optional    TEXT NOT NULL,
    always      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ritual_steps (
    seq         INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    stage       TEXT NOT NULL,
    text        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    scene_id    TEXT NOT NULL,
    spread_id   TEXT NOT NULL,
    question    TEXT NOT NULL,
    use_reversed INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    payload     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_traces (
    trace_id    TEXT PRIMARY KEY,
    session_id  TEXT,
    node        TEXT NOT NULL,
    degraded    INTEGER NOT NULL,
    model       TEXT,
    latency_ms  INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    payload     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followup_turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    turn        INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_followup_session
    ON followup_turns (session_id, id);

CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    username    TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,
    display     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(user_id),
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_user ON auth_tokens(user_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def as_csv(values) -> str:
    """Store list metadata as ',a,b,' so SQL instr() can filter it."""
    clean = [str(v).strip() for v in values if str(v).strip()]
    return "," + ",".join(clean) + "," if clean else ","

import os
import sqlite3
from contextlib import closing

DB_PATH = "data/app.db"

SCHEMA = """
-- email is stored lowercased; password_hash is argon2. language is "hi" or "en".
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('hi', 'en')),
    consent_given_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    text TEXT NOT NULL
);
-- A recognition is stored with phrase_id and source NULL; confirming it sets both,
-- which adds it to the phrase bank. top1_phrase_id is the best candidate at
-- recognition time, kept for the top-1 hit rate.
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    phrase_id INTEGER REFERENCES phrases(id),
    audio_path TEXT NOT NULL,
    prisma_hypothesis TEXT NOT NULL,
    source TEXT CHECK (source IN ('enroll', 'correction')),
    top1_phrase_id INTEGER REFERENCES phrases(id),
    created_at TEXT NOT NULL
);
"""


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(SCHEMA)


def rows(sql, params=()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, params)]


def row(sql, params=()):
    found = rows(sql, params)
    return found[0] if found else None


def execute(sql, params=()):
    """Run one write and commit it; returns the new row id for an INSERT."""
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("PRAGMA foreign_keys = ON")
        return conn.execute(sql, params).lastrowid


def delete_user(user_id):
    """Remove a user and everything that references them, in one transaction."""
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM samples WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM phrases WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

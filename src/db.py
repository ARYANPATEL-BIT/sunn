import os
import sqlite3
from contextlib import closing

from dotenv import load_dotenv

load_dotenv()
# Everything the app writes: the database, recordings and the Gnani caches.
DATA_DIR = os.environ.get("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

SCHEMA = """
-- email is stored lowercased; password_hash is argon2. language is "hi" or "en".
-- voice_embedding is Gnani's speaker_embedding as JSON, set only after voice consent.
-- caregiver_phone is digits only, country code first, ready for a wa.me link.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('hi', 'en')),
    consent_given_at TEXT NOT NULL,
    voice_embedding TEXT,
    voice_consent_given_at TEXT,
    use_own_voice INTEGER NOT NULL DEFAULT 0,
    caregiver_name TEXT,
    caregiver_phone TEXT,
    google_id TEXT
);
-- contexts is comma separated: home, hospital, market, or any.
CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    contexts TEXT NOT NULL DEFAULT 'any',
    urgent INTEGER NOT NULL DEFAULT 0
);
-- A word that fills a template's slot, like पानी in "{item} चाहिए".
CREATE TABLE IF NOT EXISTS slot_words (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    slot TEXT NOT NULL CHECK (slot IN ('item', 'person', 'place')),
    text TEXT NOT NULL
);
-- text has one slot, at its start or end; fixed_part is the rest, recorded on its own.
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    fixed_part TEXT NOT NULL
);
-- A recognition is stored with phrase_id and source NULL; confirming it sets both,
-- which adds it to the phrase bank. top1_phrase_id is the best candidate at
-- recognition time, kept for the top-1 hit rate. An enrollment belongs to exactly one
-- of phrase_id, slot_word_id or template_id. language is the user's language when Prisma
-- transcribed it ("hi" or "en"); only samples in the user's current language are matched.
-- speech_source is where a demo recording came from (pilot, torgo or simulated, see
-- scripts/load_demo.py); NULL for one recorded in the app.
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    phrase_id INTEGER REFERENCES phrases(id),
    audio_path TEXT NOT NULL,
    prisma_hypothesis TEXT NOT NULL,
    source TEXT CHECK (source IN ('enroll', 'correction')),
    top1_phrase_id INTEGER REFERENCES phrases(id),
    created_at TEXT NOT NULL,
    slot_word_id INTEGER REFERENCES slot_words(id),
    template_id INTEGER REFERENCES templates(id),
    language TEXT CHECK (language IN ('hi', 'en')),
    speech_source TEXT CHECK (speech_source IN ('pilot', 'torgo', 'simulated'))
);
-- One row per confirmed recognition, for the usage priors.
CREATE TABLE IF NOT EXISTS uses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    phrase_id INTEGER NOT NULL REFERENCES phrases(id),
    created_at TEXT NOT NULL
);
-- One row per Gnani request, sent or answered from the cache. user_id is who it was for, for
-- the daily cap; NULL for a script, and set to NULL when the account is deleted.
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('stt', 'tts', 'clone')),
    cached INTEGER NOT NULL,
    audio_seconds REAL,
    created_at TEXT NOT NULL,
    user_id INTEGER
);
"""

# Columns added after the first release, so an existing data/app.db gains them on start.
ADDED_COLUMNS = [
    ("users", "voice_embedding", "TEXT"),
    ("users", "voice_consent_given_at", "TEXT"),
    ("users", "use_own_voice", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "caregiver_name", "TEXT"),
    ("users", "caregiver_phone", "TEXT"),
    ("users", "google_id", "TEXT"),
    ("phrases", "contexts", "TEXT NOT NULL DEFAULT 'any'"),
    ("phrases", "urgent", "INTEGER NOT NULL DEFAULT 0"),
    ("samples", "slot_word_id", "INTEGER REFERENCES slot_words(id)"),
    ("samples", "template_id", "INTEGER REFERENCES templates(id)"),
    ("samples", "language", "TEXT CHECK (language IN ('hi', 'en'))"),
    ("samples", "speech_source", "TEXT CHECK (speech_source IN ('pilot', 'torgo', 'simulated'))"),
    ("api_calls", "user_id", "INTEGER"),
]


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.executescript(SCHEMA)
        for table, column, declaration in ADDED_COLUMNS:
            if column not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        # Samples from before samples.language were all transcribed in their user's language,
        # which could not change then.
        conn.execute("UPDATE samples SET language = (SELECT language FROM users WHERE users.id = samples.user_id)"
                     " WHERE language IS NULL")


def rows(sql, params=()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(sql, params)]


def row(sql, params=()):
    found = rows(sql, params)
    return found[0] if found else None


def execute(sql, params=()):
    """Run one write and commit it; returns the new row id for an INSERT."""
    return transaction((sql, params))


def transaction(*statements):
    """Run (sql, params) writes in one transaction; returns the last statement's row id."""
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for sql, params in statements:
            last = conn.execute(sql, params).lastrowid
        return last


def delete_user(user_id):
    """Remove a user and everything that references them, in one transaction. Their api_calls
    stay as counts, no longer tied to anyone."""
    transaction(("UPDATE api_calls SET user_id = NULL WHERE user_id = ?", (user_id,)),
                *[(f"DELETE FROM {table} WHERE {column} = ?", (user_id,)) for table, column in [
                    ("uses", "user_id"), ("samples", "user_id"), ("phrases", "user_id"), ("slot_words", "user_id"),
                    ("templates", "user_id"), ("users", "id")]])

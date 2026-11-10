import os
import sqlite3
from contextlib import closing, contextmanager

from dotenv import load_dotenv

import languages

load_dotenv()
# Everything the app writes: the database, recordings and the Gnani caches.
DATA_DIR = os.environ.get("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

LANGUAGE_CHECK = f"CHECK (language IN ({', '.join(repr(code) for code in languages.CODES)}))"
OLD_LANGUAGE_CHECK = "CHECK (language IN ('hi', 'en'))"  # before the other eight languages

SCHEMA = """
-- email is stored lowercased; password_hash is argon2. language is the one the user speaks
-- (languages.CODES), what Prisma hears them in and new phrases are written in.
-- voice_embedding is Gnani's speaker_embedding as JSON, set only after voice consent.
-- caregiver_phone is digits only, country code first, ready for a wa.me link.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    language TEXT NOT NULL LANGUAGE_CHECK,
    consent_given_at TEXT NOT NULL,
    voice_embedding TEXT,
    voice_consent_given_at TEXT,
    use_own_voice INTEGER NOT NULL DEFAULT 0,
    caregiver_name TEXT,
    caregiver_phone TEXT,
    google_id TEXT,
    phrase_goal INTEGER
);
-- contexts is comma separated: home, hospital, market, or any. language is the one the phrase
-- is in: Timbre says it in that language, and it is matched only to recordings in it (or English).
CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    contexts TEXT NOT NULL DEFAULT 'any',
    urgent INTEGER NOT NULL DEFAULT 0,
    language TEXT LANGUAGE_CHECK
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
-- transcribed it; only samples in the user's current language (or English) are matched.
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
    language TEXT LANGUAGE_CHECK,
    speech_source TEXT CHECK (speech_source IN ('pilot', 'torgo', 'simulated'))
);
-- One row per confirmed recognition, for the usage priors.
CREATE TABLE IF NOT EXISTS uses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    phrase_id INTEGER NOT NULL REFERENCES phrases(id),
    created_at TEXT NOT NULL
);
-- One row per Gnani request, sent or answered from the cache. user_id is who it was for; NULL
-- for a script, and set to NULL when the account is deleted. quota is the daily limit a sent call
-- counts against (stt, tts or enroll, see gnani.LIMITS); NULL for a cached call, a retry or a script.
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('stt', 'tts', 'clone')),
    cached INTEGER NOT NULL,
    audio_seconds REAL,
    created_at TEXT NOT NULL,
    user_id INTEGER,
    quota TEXT
);
-- Trainings progress: each lesson started, step index, when finished, and last update.
CREATE TABLE IF NOT EXISTS training_progress (
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, lesson_id)
);
-- Attempts at recorded training steps.
CREATE TABLE IF NOT EXISTS training_attempts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    item_id TEXT,
    transcript TEXT,
    similarity REAL,
    wpm INTEGER,
    checked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
-- User reflections at the end of lessons.
CREATE TABLE IF NOT EXISTS training_reflections (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    lesson_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    feeling TEXT NOT NULL,
    created_at TEXT NOT NULL
);
-- Minutes practised per user per day.
CREATE TABLE IF NOT EXISTS training_minutes (
    user_id INTEGER NOT NULL REFERENCES users(id),
    day TEXT NOT NULL,
    seconds INTEGER NOT NULL,
    UNIQUE (user_id, day)
);
""".replace("LANGUAGE_CHECK", LANGUAGE_CHECK)

# Columns added after the first release, so an existing data/app.db gains them on start.
ADDED_COLUMNS = [
    ("users", "voice_embedding", "TEXT"),
    ("users", "voice_consent_given_at", "TEXT"),
    ("users", "use_own_voice", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "caregiver_name", "TEXT"),
    ("users", "caregiver_phone", "TEXT"),
    ("users", "google_id", "TEXT"),
    ("users", "phrase_goal", "INTEGER DEFAULT 10"),
    ("phrases", "contexts", "TEXT NOT NULL DEFAULT 'any'"),
    ("phrases", "urgent", "INTEGER NOT NULL DEFAULT 0"),
    ("phrases", "language", f"TEXT {LANGUAGE_CHECK}"),
    ("samples", "slot_word_id", "INTEGER REFERENCES slot_words(id)"),
    ("samples", "template_id", "INTEGER REFERENCES templates(id)"),
    ("samples", "language", f"TEXT {LANGUAGE_CHECK}"),
    ("samples", "speech_source", "TEXT CHECK (speech_source IN ('pilot', 'torgo', 'simulated'))"),
    ("api_calls", "user_id", "INTEGER"),
    ("api_calls", "quota", "TEXT"),
]


def widen_language_checks(conn):
    """Tables made when only hi and en existed take all of languages.CODES: SQLite can't change a
    CHECK in place, so each is copied into a new table with the wider one."""
    for table in ("users", "samples"):
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()[0]
        if OLD_LANGUAGE_CHECK not in sql:
            continue
        columns = ", ".join(r[1] for r in conn.execute(f"PRAGMA table_info({table})"))
        conn.execute(f"DROP TABLE IF EXISTS {table}_wide")  # left by a copy that failed
        conn.execute(sql.replace(OLD_LANGUAGE_CHECK, LANGUAGE_CHECK).replace(table, f"{table}_wide", 1))
        conn.execute(f"INSERT INTO {table}_wide ({columns}) SELECT {columns} FROM {table}")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {table}_wide RENAME TO {table}")


def relax_phrase_goal_notnull(conn):
    """If users table has a NOT NULL constraint on phrase_goal from earlier schema, relax it."""
    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    phrase_goal_col = next((c for c in cols if c[1] == "phrase_goal"), None)
    if phrase_goal_col and phrase_goal_col[3] == 1:
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone()[0]
        new_sql = sql.replace("phrase_goal INTEGER NOT NULL DEFAULT 10", "phrase_goal INTEGER").replace("users", "users_relax", 1)
        columns = ", ".join(r[1] for r in cols)
        conn.execute("DROP TABLE IF EXISTS users_relax")
        conn.execute(new_sql)
        conn.execute(f"INSERT INTO users_relax ({columns}) SELECT {columns} FROM users")
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_relax RENAME TO users")


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.executescript(SCHEMA)
        widen_language_checks(conn)
        relax_phrase_goal_notnull(conn)
        for table, column, declaration in ADDED_COLUMNS:
            if column not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        # Samples from before samples.language were all transcribed in their user's language,
        # which could not change then.
        conn.execute("UPDATE samples SET language = (SELECT language FROM users WHERE users.id = samples.user_id)"
                     " WHERE language IS NULL")
        # Existing users with 0 recordings who received an automatic default 10 have phrase_goal reset to NULL
        # so they can explicitly choose their starting goal; users with recordings retain their goals.
        conn.execute("UPDATE users SET phrase_goal = NULL WHERE phrase_goal = 10 AND id NOT IN (SELECT DISTINCT user_id FROM samples)")
        # Phrases from before phrases.language: Devanagari ones are Hindi (the only such language
        # then), the rest are in the language they were recorded in, else their user's.
        for p in conn.execute("SELECT p.id, p.text, u.language AS user_language, (SELECT s.language FROM samples s"
                              " WHERE s.phrase_id = p.id LIMIT 1) AS recorded FROM phrases p"
                              " JOIN users u ON u.id = p.user_id WHERE p.language IS NULL").fetchall():
            language = "hi" if languages.in_script(p[1], languages.DEVANAGARI) else p[3] or p[2]
            conn.execute("UPDATE phrases SET language = ? WHERE id = ?", (language, p[0]))


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


@contextmanager
def locked():
    """A connection holding the database's write lock from its first read to commit, so a count
    and the insert that depends on it can't interleave with another request's."""
    with closing(sqlite3.connect(DB_PATH, isolation_level=None, timeout=30)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")


def delete_user(user_id):
    """Remove a user and everything that references them, in one transaction. Their api_calls
    stay as counts, no longer tied to anyone."""
    transaction(("UPDATE api_calls SET user_id = NULL WHERE user_id = ?", (user_id,)),
                *[(f"DELETE FROM {table} WHERE {column} = ?", (user_id,)) for table, column in [
                    ("uses", "user_id"), ("samples", "user_id"), ("phrases", "user_id"), ("slot_words", "user_id"),
                    ("templates", "user_id"), ("training_progress", "user_id"), ("training_attempts", "user_id"),
                    ("training_reflections", "user_id"), ("training_minutes", "user_id"), ("users", "id")]])

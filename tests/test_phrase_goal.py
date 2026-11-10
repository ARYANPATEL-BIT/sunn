import sqlite3
from contextlib import closing

import db


def test_user_signup_default_phrase_goal(env):
    user_client = env.signup("hi")
    me = user_client.get("/auth/me").json()
    assert me["phrase_goal"] == 10


def test_update_phrase_goal_success(env):
    user_client = env.signup("hi")
    res = user_client.patch("/me", json={"phrase_goal": 20})
    assert res.status_code == 200
    user = res.json()
    assert user["phrase_goal"] == 20

    # Persisted across calls
    me = user_client.get("/auth/me").json()
    assert me["phrase_goal"] == 20


def test_update_phrase_goal_validation(env):
    user_client = env.signup("hi")
    res_zero = user_client.patch("/me", json={"phrase_goal": 0})
    assert res_zero.status_code == 400
    assert res_zero.json()["error"] == "invalid_input"

    res_neg = user_client.patch("/me", json={"phrase_goal": -10})
    assert res_neg.status_code == 400
    assert res_neg.json()["error"] == "invalid_input"


def test_phrase_goal_cross_user_isolation(env):
    user1 = env.signup("hi")
    user2 = env.signup("en")

    user1.patch("/me", json={"phrase_goal": 25})
    assert user1.get("/auth/me").json()["phrase_goal"] == 25
    assert user2.get("/auth/me").json()["phrase_goal"] == 10


def test_db_migration_phrase_goal(tmp_path, monkeypatch):
    test_db = str(tmp_path / "legacy.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a legacy users table without phrase_goal
    legacy_schema = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        language TEXT NOT NULL,
        consent_given_at TEXT NOT NULL,
        voice_embedding TEXT,
        voice_consent_given_at TEXT,
        use_own_voice INTEGER NOT NULL DEFAULT 0,
        caregiver_name TEXT,
        caregiver_phone TEXT,
        google_id TEXT
    );
    INSERT INTO users (id, name, email, password_hash, language, consent_given_at)
    VALUES (1, 'Legacy User', 'legacy@sunn.app', 'hash123', 'hi', '2026-01-01');
    """
    with closing(sqlite3.connect(test_db)) as conn, conn:
        conn.executescript(legacy_schema)

    # Run db.init() migration
    db.init()

    # Verify column was added with default value 10
    with closing(sqlite3.connect(test_db)) as conn:
        row = conn.execute("SELECT id, name, phrase_goal FROM users WHERE id = 1").fetchone()
        assert row[0] == 1
        assert row[1] == "Legacy User"
        assert row[2] == 10

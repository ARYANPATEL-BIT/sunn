"""The Postgres layer (src/db.py): migrations, the atomic rate limit, data across a restart,
the startup check, /health, and that no message ever shows where the database is."""
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict, make_conninfo

import db
import gnani
import languages

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
TABLES = {"users", "phrases", "slot_words", "templates", "samples", "uses", "api_calls", "training_progress",
          "training_attempts", "training_reflections", "training_minutes", "schema_migrations"}
# Nothing listens on port 1; the password and port must never show up in a message.
UNREACHABLE = "postgresql://sunn:not-a-real-password@127.0.0.1:1/nowhere?sslmode=disable"


def add_user(email="a@example.com", language="hi"):
    return db.execute("INSERT INTO users (name, email, password_hash, language, consent_given_at)"
                      " VALUES ('A', %s, 'x', %s, '2026-01-01T00:00:00+00:00') RETURNING id", (email, language))


@pytest.fixture
def new_database(monkeypatch):
    """A brand-new database next to the test one, with nothing in it, dropped afterwards."""
    test_url = os.environ["DATABASE_URL"]
    name = f"sunn_empty_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_url, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    monkeypatch.setenv("DATABASE_URL", make_conninfo(**{**conninfo_to_dict(test_url), "dbname": name}))
    db.close()
    yield name
    db.close()
    with psycopg.connect(test_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {name} WITH (FORCE)")


def test_migrations_apply_on_an_empty_database_and_a_second_run_does_nothing(new_database):
    assert db.rows("SELECT tablename FROM pg_tables WHERE schemaname = 'public'") == []
    db.init()
    tables = {r["tablename"] for r in db.rows("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    assert tables == TABLES
    applied = db.rows("SELECT version, applied_at FROM schema_migrations")
    assert [r["version"] for r in applied] == ["001_init.sql"]

    db.init()  # a restart: nothing to apply, nothing re-applied
    assert db.rows("SELECT version, applied_at FROM schema_migrations") == applied


def test_the_language_checks_take_exactly_languages_codes():
    for i, code in enumerate(languages.CODES):
        add_user(f"{i}@example.com", code)
    with pytest.raises(psycopg.errors.CheckViolation):
        add_user("xx@example.com", "xx")


def test_the_rate_limit_is_atomic_with_two_parallel_requests(monkeypatch):
    """Two requests race for this user's last STT call. quota_state is slowed down so both have
    counted before either inserts: under the lock exactly one gets it. The same race without
    the lock lets both through, which shows the test can see a race at all."""
    monkeypatch.setenv("GNANI_CALL_LIMIT", "4000")
    monkeypatch.setenv("STT_DAILY_LIMIT", "1")
    monkeypatch.delenv("LIMIT_EXEMPT_EMAILS", raising=False)
    monkeypatch.delenv("OWNER_EMAIL", raising=False)
    counted = gnani.quota_state

    def slow_quota_state(row, user_id, quota):
        state = counted(row, user_id, quota)
        time.sleep(0.5)
        return state

    monkeypatch.setattr(gnani, "quota_state", slow_quota_state)

    def race(user_id):
        barrier, results = threading.Barrier(2), []

        def request():
            barrier.wait()
            try:
                results.append(("sent", gnani.reserve("stt", 1.0, user_id, "stt")))
            except gnani.GnaniError as e:
                results.append((e.code, None))

        threads = [threading.Thread(target=request) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        sent = db.row("SELECT COUNT(*) AS n FROM api_calls WHERE user_id = %s", (user_id,))["n"]
        return sorted(code for code, _ in results), sent

    assert race(add_user("locked@example.com")) == (["daily_limit", "sent"], 1)

    @contextmanager
    def no_lock(key):
        with db.connection() as conn:
            yield conn

    monkeypatch.setattr(db, "locked", no_lock)
    assert race(add_user("unlocked@example.com")) == (["sent", "sent"], 2)


def test_data_survives_a_restart():
    """Write, close the pool (what a restart does to the app's connections), reconnect, read."""
    user_id = add_user("kept@example.com")
    db.execute("INSERT INTO phrases (user_id, text, language) VALUES (%s, 'पानी चाहिए', 'hi')", (user_id,))
    db.close()
    assert db._pool is None
    assert db.row("SELECT email FROM users WHERE id = %s", (user_id,)) == {"email": "kept@example.com"}
    assert db.row("SELECT text FROM phrases WHERE user_id = %s", (user_id,)) == {"text": "पानी चाहिए"}


def test_the_app_refuses_to_start_without_database_url(tmp_path):
    # Empty, not unset: load_dotenv never overrides a variable that is set, so .env can't fill it in.
    env = {**os.environ, "DATABASE_URL": "", "PYTHONPATH": SRC}
    started = subprocess.run([sys.executable, "-c", "import api"], cwd=tmp_path, env=env,
                             capture_output=True, text=True, timeout=180)
    assert started.returncode != 0
    assert "DATABASE_URL is not set" in started.stderr


def test_health_says_up(env):
    response = env.client().get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok", "database": "up"}


def test_health_says_down_when_the_database_is_unreachable_and_never_where_it_is(env, monkeypatch, caplog):
    client = env.client()
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE)
    monkeypatch.setattr(db, "WAIT_SECONDS", 3)
    db.close()
    with caplog.at_level(logging.DEBUG):
        response = client.get("/health")
        with pytest.raises(db.DatabaseUnavailable) as failed:
            db.row("SELECT 1")
    assert response.status_code == 503 and response.json() == {"status": "error", "database": "down"}
    shown = response.text + str(failed.value) + caplog.text
    assert "OperationalError" in str(failed.value) or "PoolTimeout" in str(failed.value)
    for detail in ("127.0.0.1", "not-a-real-password", "nowhere", "port 1"):
        assert detail not in shown


def test_health_asks_the_database_at_most_once_a_minute(monkeypatch):
    assert db.up() is True
    asked = []

    @contextmanager
    def unreachable():
        asked.append(1)
        raise db.DatabaseUnavailable("the database could not be reached (OperationalError)")
        yield

    monkeypatch.setattr(db, "connection", unreachable)
    assert db.up() is True and asked == []  # remembered, so a poller can't keep Neon awake
    db._health["at"] -= db.HEALTH_SECONDS
    assert db.up() is False and len(asked) == 1  # a minute later it asks again


def test_a_failed_connect_is_retried_once(monkeypatch):
    """Neon may be waking from idle: one more try straight away, then the query fails. A wrong
    password fails at once, so both tries fit in the wait."""
    attempts = []
    connect = psycopg.Connection.connect.__func__

    def counted(cls, *args, **kwargs):
        attempts.append(1)
        return connect(cls, *args, **kwargs)

    monkeypatch.setattr(psycopg.Connection, "connect", classmethod(counted))
    wrong_password = {**conninfo_to_dict(os.environ["DATABASE_URL"]), "password": "wrong"}
    monkeypatch.setenv("DATABASE_URL", make_conninfo(**wrong_password))
    monkeypatch.setattr(db, "WAIT_SECONDS", 3)
    db.close()
    with pytest.raises(db.DatabaseUnavailable):
        db.row("SELECT 1")
    assert len(attempts) == 2

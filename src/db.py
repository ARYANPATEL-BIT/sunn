"""The database: Postgres at DATABASE_URL (Neon in production, its dev branch locally, a local
Docker Postgres in tests). The schema is the numbered files in src/migrations, each applied once.

Nothing here ever prints, logs or raises a message that holds the connection string or the
host: connection failures become DatabaseUnavailable, which names only the error's type."""
import glob
import logging
import os
import time
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

load_dotenv()
# Recordings and the Gnani caches. None of it has to survive a restart (docs/DEPLOY.md).
DATA_DIR = os.environ.get("DATA_DIR", "data")
MIGRATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
# pg_advisory_xact_lock keys: one for applying migrations, one for gnani.reserve.
MIGRATIONS_LOCK, RESERVE_LOCK = 1, 2
HEALTH_SECONDS = 60  # how long /health remembers its answer, so a poller can't keep Neon awake
# How long a query waits for a connection: room for a connect (connect_timeout 10 s, while Neon's
# compute wakes from idle) and the one retry after it.
WAIT_SECONDS = 25
# A connection back in the pool for longer than this is pinged before it is used, since Neon may
# have closed it (it does when its compute suspends); a newer one is used straight away.
CHECK_IDLE_SECONDS = 30

_pool = None
_health = {"at": None, "up": False}


class DatabaseUnavailable(RuntimeError):
    """The database could not be reached. The message is safe to show: it holds no host."""


class _HideConnectionDetails(logging.Filter):
    """psycopg's pool logs connection errors and connections, which name the host: keep only
    which logger said something at what level."""

    def filter(self, record):
        record.msg, record.args, record.exc_info = "database connection event (details hidden)", (), None
        return True


for _name in ("psycopg", "psycopg.pool"):
    logging.getLogger(_name).addFilter(_HideConnectionDetails())


def _conninfo():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set: put the Postgres connection string in .env (see .env.example)"
                           " or in the host's secrets")
    try:
        params = conninfo_to_dict(url)
    except psycopg.ProgrammingError:
        raise RuntimeError("DATABASE_URL is not a valid Postgres connection string") from None
    params.setdefault("sslmode", "require")  # the test URL turns it off for the local Docker Postgres
    return make_conninfo(**params)


def _returned(conn):
    conn._returned_at = time.monotonic()


def _check(conn):
    """Ping only a connection idle over CHECK_IDLE_SECONDS; one just made has no _returned_at."""
    if time.monotonic() - getattr(conn, "_returned_at", time.monotonic()) > CHECK_IDLE_SECONDS:
        ConnectionPool.check_connection(conn)


def pool():
    """The connection pool, made on first use. It holds no connection while the app is idle
    (min_size 0, idle ones closed after 5 minutes, no pings), so Neon can suspend its compute.
    A failed connect is tried once more straight away, then given up (reconnect_timeout 0): only
    connecting is retried, never a statement. No prepared statements: Neon's pooler is PgBouncer.
    Autocommit, so a single statement is one round trip (no BEGIN, no COMMIT); connection()
    opens a transaction for whatever needs one."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            _conninfo(), min_size=0, max_size=5, max_idle=300, reconnect_timeout=0, timeout=WAIT_SECONDS,
            check=_check, reset=_returned,
            kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None, "connect_timeout": 10},
            open=True, name="sunn")
    return _pool


def close():
    """Close the pool and its connections; the next query makes a new one."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
    _health["at"] = None


@contextmanager
def _autocommit():
    """A pooled connection on which each statement commits by itself: for a single statement."""
    try:
        with pool().connection() as conn:
            yield conn
    except (psycopg.OperationalError, PoolTimeout) as e:
        raise DatabaseUnavailable(f"the database could not be reached ({type(e).__name__})") from None


@contextmanager
def connection():
    """A pooled connection holding one transaction: committed when the block ends, rolled
    back when it raises."""
    with _autocommit() as conn, conn.transaction():
        yield conn


def init():
    """Apply the migrations not yet in schema_migrations, in file name order, each in the same
    transaction as its record. The lock makes a second process starting at once wait."""
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATIONS_LOCK,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations"
                     " (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(glob.glob(os.path.join(MIGRATIONS, "*.sql"))):
            version = os.path.basename(path)
            if version not in done:
                with open(path, encoding="utf-8") as f:
                    conn.execute(f.read())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))


def rows(sql, params=()):
    with _autocommit() as conn:
        return conn.execute(sql, params).fetchall()


def row(sql, params=()):
    with _autocommit() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql, params=()):
    """Run one write, committed by itself; returns the first column it returns (RETURNING id)."""
    with _autocommit() as conn:
        cursor = conn.execute(sql, params)
        found = cursor.fetchone() if cursor.description else None
        return next(iter(found.values())) if found else None


def transaction(*statements):
    """Run (sql, params) writes in one transaction; returns the first column the last one
    returns, if it has a RETURNING clause."""
    with connection() as conn:
        for sql, params in statements:
            cursor = conn.execute(sql, params)
        found = cursor.fetchone() if cursor.description else None
        return next(iter(found.values())) if found else None


@contextmanager
def locked(key):
    """A connection whose transaction holds advisory lock key until it commits or rolls back,
    so a count and the insert that depends on it can't interleave with another request's.
    Transaction-scoped, so it works through Neon's pooler."""
    with connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (key,))
        yield conn


def up():
    """Whether SELECT 1 works, remembered for HEALTH_SECONDS: a health poller asks at most once
    a minute, so it can't keep Neon's compute awake."""
    now = time.monotonic()
    if _health["at"] is None or now - _health["at"] >= HEALTH_SECONDS:
        try:
            with connection() as conn:
                conn.execute("SELECT 1")
            _health["up"] = True
        except DatabaseUnavailable:
            _health["up"] = False
        _health["at"] = now
    return _health["up"]


def delete_user(user_id):
    """Remove a user and everything that references them, in one transaction. Their api_calls
    stay as counts, no longer tied to anyone."""
    transaction(("UPDATE api_calls SET user_id = NULL WHERE user_id = %s", (user_id,)),
                *[(f"DELETE FROM {table} WHERE {column} = %s", (user_id,)) for table, column in [
                    ("uses", "user_id"), ("samples", "user_id"), ("phrases", "user_id"), ("slot_words", "user_id"),
                    ("templates", "user_id"), ("training_progress", "user_id"), ("training_attempts", "user_id"),
                    ("training_reflections", "user_id"), ("training_minutes", "user_id"), ("users", "id")]])

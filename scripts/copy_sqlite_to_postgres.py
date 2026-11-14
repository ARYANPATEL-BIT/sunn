"""Copy the old local SQLite database (data/app.db) into the Neon dev branch, once.

Reads DATABASE_URL and NEON_BRANCH from .env only (`neon checkout dev` writes both), and
refuses unless NEON_BRANCH is dev: this never copies into production. A dry run is the
default: per table, the rows it would copy and what the target already has. --apply copies
everything in one transaction, keeping the ids (so data/users/<id>/ still matches), and
refuses a target that already has users. api_calls is skipped unless --with-api-calls: those
are local test calls, and every sent one counts against GNANI_CALL_LIMIT for good.
Nothing it prints holds the connection string or the host.

    uv run scripts/copy_sqlite_to_postgres.py                  # dry run
    uv run scripts/copy_sqlite_to_postgres.py --apply          # copy
"""
import argparse
import os
import sqlite3
import sys
from contextlib import closing

from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
ENV = dotenv_values(os.path.join(ROOT, ".env"))
os.environ["DATABASE_URL"] = ENV.get("DATABASE_URL") or ""  # .env's, never one from the shell

import db  # noqa: E402

# Parents before children, for the foreign keys.
TABLES = ["users", "phrases", "slot_words", "templates", "samples", "uses", "api_calls",
          "training_progress", "training_attempts", "training_reflections", "training_minutes"]


def sqlite_tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def target_count(table):
    exists = db.row("SELECT to_regclass(%s) IS NOT NULL AS found", (table,))["found"]
    return db.row(f"SELECT COUNT(*) AS n FROM {table}")["n"] if exists else None


def copy(source, conn, table):
    """Insert the source table's rows, in the columns both sides have; returns how many."""
    target_columns = {r["column_name"] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,))}
    columns = [r[1] for r in source.execute(f"PRAGMA table_info({table})") if r[1] in target_columns]
    found = source.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY rowid").fetchall()
    if found:
        with conn.cursor() as cursor:
            cursor.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})",
                               found)
    if "id" in columns:  # the next new row gets an id after the copied ones
        conn.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 0) + 1, false)"
                     f" FROM {table}")
    return len(found)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default=os.path.join(ROOT, "data", "app.db"), help="the old database file")
    parser.add_argument("--apply", action="store_true", help="copy; without it, only report")
    parser.add_argument("--with-api-calls", action="store_true", help="copy api_calls too")
    args = parser.parse_args()

    if ENV.get("NEON_BRANCH") != "dev":
        sys.exit("refusing: .env's NEON_BRANCH is not dev (run `neon checkout dev` first); this only copies into dev")
    if not os.path.exists(args.sqlite):
        sys.exit(f"no SQLite database at {args.sqlite}")
    tables = [t for t in TABLES if t != "api_calls" or args.with_api_calls]

    with closing(sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)) as source:
        present = sqlite_tables(source)
        print(f"{'table':22} {'in sqlite':>9} {'in dev':>7}  action")
        for table in TABLES:
            rows = source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if table in present else 0
            there = target_count(table)
            action = "skipped (--with-api-calls copies it)" if table not in tables else (
                "copy" if args.apply else "would copy")
            print(f"{table:22} {rows:>9} {'no table' if there is None else there:>7}  {action}")
        if not args.apply:
            print("\ndry run: nothing was written. --apply copies the tables marked above.")
            return

        db.init()
        if db.row("SELECT COUNT(*) AS n FROM users")["n"]:
            sys.exit("refusing: dev already has users; copy only into an empty database")
        with db.connection() as conn:
            copied = {table: copy(source, conn, table) for table in tables if table in present}
        print("\ncopied, in one transaction: " + ", ".join(f"{t} {n}" for t, n in copied.items()))


if __name__ == "__main__":
    try:
        main()
    except db.DatabaseUnavailable as e:
        sys.exit(f"copy_sqlite_to_postgres: {e}")

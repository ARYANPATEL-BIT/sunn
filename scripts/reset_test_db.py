"""Empty the test database and apply the migrations: for tests/conftest.py before every test,
and for the e2e server (web/playwright.config.js), which this starts with --serve.

The test database is TEST_DATABASE_URL (environment, else .env): the local Docker Postgres,
container sunn-test-pg (docs/DEPLOY.md). It refuses one that is missing, the same as
DATABASE_URL, or on Neon, so tests can never empty the dev or production branch.

    uv run scripts/reset_test_db.py                       # empty it
    uv run scripts/reset_test_db.py --serve --port 7861   # empty it, then run src/server.py on it
"""
import argparse
import os
import runpy
import sys
from urllib.parse import urlparse

from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

import psycopg  # noqa: E402

import db  # noqa: E402

ENV = dotenv_values(os.path.join(ROOT, ".env"))
# The app's own DATABASE_URL from the environment, as it was before tests replaced it.
APP_URL = os.environ.get("DATABASE_URL")


def check(url):
    """Refuse a URL that isn't safely a throwaway test database. Messages hold no URL."""
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is not set: tests run on the local Docker Postgres"
                           " (see .env.example and docs/DEPLOY.md)")
    others = {ENV.get("DATABASE_URL"), ENV.get("DATABASE_URL_UNPOOLED"), APP_URL}
    if url in others:
        raise RuntimeError("TEST_DATABASE_URL is the same as DATABASE_URL: tests empty their database,"
                           " so it must be a separate one")
    if (urlparse(url).hostname or "").endswith(".neon.tech"):
        raise RuntimeError("TEST_DATABASE_URL points at Neon: tests only run on the local Docker Postgres")
    return url


def checked_url():
    """TEST_DATABASE_URL, checked. Call it before DATABASE_URL is pointed at it."""
    return check(os.environ.get("TEST_DATABASE_URL") or ENV.get("TEST_DATABASE_URL"))


def reset(url):
    """Point the app at url (checked again), apply the migrations, and empty every table."""
    os.environ["DATABASE_URL"] = check(url)
    db.close()
    db.init()
    with psycopg.connect(url, autocommit=True) as conn:
        tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
                                             " AND tablename != 'schema_migrations'")]
        if tables:
            conn.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="then run src/server.py on the test database")
    parser.add_argument("--port", default="7861")
    args = parser.parse_args()
    try:
        reset(checked_url())
    except (RuntimeError, db.DatabaseUnavailable) as e:
        sys.exit(f"reset_test_db: {e}")
    print("test database emptied")
    if args.serve:
        sys.argv = ["server.py", "--port", args.port]
        runpy.run_path(os.path.join(SRC, "server.py"), run_name="__main__")

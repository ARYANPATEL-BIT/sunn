"""Load a demo account from a folder of recordings, through the normal API.

The folder holds manifest.csv (docs/DEMO_DATA.md) with the columns:

    phrase  the phrase, written as it should appear in the app
    file    the recording, relative to the folder: any format ffmpeg reads, 0.3-15 s
    kind    enroll (taught to the account) or test (held out for scripts/evaluate.py, never uploaded)
    source  pilot (a real person who consented), torgo (the TORGO corpus) or simulated

The manifest is checked in full before anything is sent. Then this signs in as --email, or
signs up when there is no such account, adds the default phrases, and enrolls each enroll row
with POST /me/enroll and its source. Each new recording is one Prisma call (the server caches
it), so it counts against the account's DAILY_CALL_CAP_PER_USER on that server.

It stops at the first refused recording. Run it again and it carries on: a phrase that already
has n enrollment recordings skips its first n rows.

    uv run scripts/load_demo.py --email demo@example.com --folder data/demo
    uv run scripts/load_demo.py --email demo@example.com --folder data/demo --url https://<space>.hf.space/api
"""
import argparse
import csv
import getpass
import hashlib
import os
import sys
from collections import defaultdict

import requests

COLUMNS = ["phrase", "file", "kind", "source"]
KINDS = ("enroll", "test")
SOURCES = ("pilot", "torgo", "simulated")


def read_manifest(folder):
    """Rows of folder/manifest.csv, each with its file's full path. Refuses unknown columns,
    kinds or sources, missing files, and a recording that is both enrolled and tested."""
    with open(os.path.join(folder, "manifest.csv"), encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if sorted(reader.fieldnames or []) != sorted(COLUMNS):
            raise SystemExit(f"manifest.csv needs exactly the columns {', '.join(COLUMNS)}")
        rows = [{"phrase": " ".join(r["phrase"].split()), "file": r["file"].strip(),
                 "kind": r["kind"].strip(), "source": r["source"].strip()} for r in reader]

    problems, kind_of = [], {}
    for line, r in enumerate(rows, start=2):  # line 1 is the header
        r["path"] = os.path.join(folder, r["file"])
        if not r["phrase"]:
            problems.append(f"line {line}: phrase is empty")
        if r["kind"] not in KINDS:
            problems.append(f"line {line}: kind is {r['kind']!r}, not one of {', '.join(KINDS)}")
        if r["source"] not in SOURCES:
            problems.append(f"line {line}: source is {r['source']!r}, not one of {', '.join(SOURCES)}")
        if not os.path.isfile(r["path"]):
            problems.append(f"line {line}: {r['file']} not found")
            continue
        # By content, so a copy under another name can't leak a test recording into enrollment.
        with open(r["path"], "rb") as f:
            kind_of.setdefault(hashlib.sha256(f.read()).hexdigest(), set()).add(r["kind"])
    if any(kinds >= set(KINDS) for kinds in kind_of.values()):
        problems.append("a recording is both enroll and test; held-out recordings must be different ones")
    if problems:
        raise SystemExit("manifest.csv:\n  " + "\n  ".join(problems))
    return rows


def check(response, step):
    if response.status_code >= 400:
        raise SystemExit(f"{step}: HTTP {response.status_code} {response.text}")
    return response.json()


def sign_in(session, url, email, password, name, language, invite):
    """Log in, or sign up when the account doesn't exist yet; returns the user."""
    response = session.post(f"{url}/auth/login", json={"email": email, "password": password})
    if response.status_code == 401:
        response = session.post(f"{url}/auth/signup", json={
            "name": name, "email": email, "password": password, "language": language, "consent": True,
            "invite_code": invite})
        if response.status_code == 409:
            raise SystemExit(f"{email} has an account, and that isn't its password")
    user = check(response, f"sign in as {email}")
    if url.startswith("http://"):  # the cookie is Secure, so plain http to a local server needs it set by hand
        session.cookies.set("sunn_session", response.cookies["sunn_session"])
    if user["language"] != language:
        user = check(session.patch(f"{url}/me", json={"language": language}), "set the language")
    return user


def load(session, url, rows):
    """Enroll the enroll rows that aren't enrolled yet; returns how many were sent."""
    phrases = {p["text"]: p for p in check(session.post(f"{url}/me/phrases/default"), "add default phrases")}
    todo = defaultdict(list)
    for r in rows:
        if r["kind"] == "enroll":
            todo[r["phrase"]].append(r)

    sent = 0
    for text, recordings in todo.items():
        phrase = phrases.get(text) or check(session.post(f"{url}/me/phrases", json={"text": text}), f"add {text}")
        for r in recordings[phrases[text]["enrolled"] if text in phrases else 0:]:
            with open(r["path"], "rb") as f:
                response = session.post(f"{url}/me/enroll", data={"phrase_id": phrase["id"], "source": r["source"]},
                                        files={"audio": (os.path.basename(r["path"]), f)}, timeout=90)
            enrolled = check(response, f"enroll {r['file']} as {text}")
            sent += 1
            print(f"{text}: {r['file']} ({r['source']}) heard as {enrolled['hypothesis']!r}")
    return sent


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--folder", required=True, help="the folder with manifest.csv")
    parser.add_argument("--url", default="http://127.0.0.1:7860/api", help="the API's base")
    parser.add_argument("--language", choices=["hi", "en"], default="hi", help="the language the phrases are in")
    parser.add_argument("--name", default="Demo")
    parser.add_argument("--invite", default=os.environ.get("DEMO_INVITE_CODE"),
                        help="the server's DEMO_INVITE_CODE, if it has one (default: $env:DEMO_INVITE_CODE)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which can't print Devanagari

    rows = read_manifest(args.folder)
    password = os.environ.get("DEMO_PASSWORD") or getpass.getpass(f"password for {args.email}: ")
    session = requests.Session()
    sign_in(session, args.url, args.email.strip().lower(), password, args.name, args.language, args.invite)
    sent = load(session, args.url, rows)
    enroll = [r for r in rows if r["kind"] == "enroll"]
    print(f"enrolled {sent} new recordings ({len(enroll) - sent} were already there) for "
          f"{len({r['phrase'] for r in enroll})} phrases; {len(rows) - len(enroll)} test recordings held out")

"""Exercise the API end to end against a running server.

Signs up a new user (which sets the session cookie), adds the default phrases, enrolls the
first two with the given wavs, then recognizes the first wav again. Prisma is called once
per new recording; the recognize step reuses the cached transcript of wav1.
"""
import argparse
import json
import sys
import uuid

import requests


def show(step, response):
    print(f"--- {step}: HTTP {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except ValueError:
        print(response.text)
    response.raise_for_status()
    return response.json()


def upload(path):
    return {"audio": (path, open(path, "rb"), "audio/wav")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wav1")
    parser.add_argument("wav2")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--language", choices=["hi", "en"], default="hi")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which can't print Devanagari

    session = requests.Session()
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    signup = session.post(f"{args.url}/auth/signup", json={
        "name": "smoke test", "email": email, "password": "smoke-test-password",
        "language": args.language, "consent": True})
    show(f"sign up {email}", signup)
    # The server marks the cookie Secure (browsers reach it over https through Vite). This
    # script talks plain http to the API, so it keeps the cookie without that flag.
    session.cookies.set("sunn_session", signup.cookies["sunn_session"])
    show("who am I", session.get(f"{args.url}/auth/me"))

    me = f"{args.url}/me"
    phrases = show("add default phrases", session.post(f"{me}/phrases/default"))

    for wav, phrase in [(args.wav1, phrases[0]), (args.wav2, phrases[1])]:
        show(f"enroll {wav} as {phrase['text']}",
             session.post(f"{me}/enroll", data={"phrase_id": phrase["id"]}, files=upload(wav), timeout=90))

    show(f"recognize {args.wav1}", session.post(f"{me}/recognize", files=upload(args.wav1), timeout=90))

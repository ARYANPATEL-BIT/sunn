"""Exercise the API end to end against a running server.

Creates a user, adds the default phrases, enrolls the first two with the given wavs,
then recognizes the first wav again. Prisma is called once per new recording; the
recognize step reuses the cached transcript of wav1.
"""
import argparse
import json
import sys

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
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which can't print Devanagari

    user = show("create user", requests.post(f"{args.url}/users",
                                             json={"name": "smoke test", "language": "hi-IN", "consent": True}))
    users = f"{args.url}/users/{user['id']}"
    phrases = show("add default phrases", requests.post(f"{users}/phrases/default"))

    for wav, phrase in [(args.wav1, phrases[0]), (args.wav2, phrases[1])]:
        show(f"enroll {wav} as {phrase['text']}",
             requests.post(f"{users}/enroll", data={"phrase_id": phrase["id"]}, files=upload(wav), timeout=90))

    show(f"recognize {args.wav1}", requests.post(f"{users}/recognize", files=upload(args.wav1), timeout=90))

"""Exercise the API end to end against a running server.

Signs up a new user (which sets the session cookie), sets a caregiver, adds the default
phrases and enrolls the first two with the given wavs. Then enrolls a slot word and a
template's fixed part with the same two wavs, recognizes wav1 in the home context, confirms
the top candidate, edits and deletes a phrase, reads the stats and usage, and finally
deletes the account.

Gnani is called twice (one Prisma call per wav); every later step reuses those cached
transcripts. --voice ref.wav (5-30 s of speech) also clones that voice and speaks one phrase
in it: one clone call and one Timbre call, both cached for the next run.
"""
import argparse
import json
import sys
import uuid

import requests


def show(step, response, ok=True):
    print(f"--- {step}: HTTP {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except ValueError:
        print(f"{len(response.content)} bytes of {response.headers.get('content-type')}")
    if ok:
        response.raise_for_status()
    return response.json() if response.headers.get("content-type") == "application/json" else None


def upload(path):
    return {"audio": (path, open(path, "rb"), "audio/wav")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wav1")
    parser.add_argument("wav2")
    parser.add_argument("--voice", help="5-30 s of speech to clone; omit to skip the cloned voice")
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
    show("set a caregiver", session.patch(me, json={"caregiver_name": "Smoke", "caregiver_phone": "+91 98765 43210"}))
    phrases = show("add default phrases", session.post(f"{me}/phrases/default"))

    for wav, phrase in [(args.wav1, phrases[0]), (args.wav2, phrases[1])]:
        show(f"enroll {wav} as {phrase['text']}",
             session.post(f"{me}/enroll", data={"phrase_id": phrase["id"]}, files=upload(wav), timeout=90))

    word = show("slot words", session.get(f"{me}/slot-words"))[0]
    template = show("templates", session.get(f"{me}/templates"))[0]
    show(f"enroll {args.wav1} as the slot word {word['text']}",
         session.post(f"{me}/slot-words/{word['id']}/enroll", files=upload(args.wav1), timeout=90))
    show(f"enroll {args.wav2} as the fixed part of {template['text']}",
         session.post(f"{me}/templates/{template['id']}/enroll", files=upload(args.wav2), timeout=90))

    heard = show(f"recognize {args.wav1} at home",
                 session.post(f"{me}/recognize", data={"context": "home"}, files=upload(args.wav1), timeout=90))
    top = heard["candidates"][0]
    answer = ({"template_id": top["template_id"], "slot_word_id": top["slot_word_id"]} if top["composed"]
              else {"phrase_id": top["phrase_id"]})
    show(f"confirm {top['text']}", session.post(f"{me}/confirm", json={"sample_id": heard["sample_id"], **answer}))

    show("mark the second phrase urgent, at home",
         session.patch(f"{me}/phrases/{phrases[1]['id']}", json={"contexts": ["home"], "urgent": True}))
    second = show("recognize again, to delete that sample",
                  session.post(f"{me}/recognize", files=upload(args.wav2), timeout=90))
    show("delete that sample", session.delete(f"{me}/samples/{second['sample_id']}"))
    show("delete the second phrase", session.delete(f"{me}/phrases/{phrases[1]['id']}"))

    if args.voice:
        show("clone my voice", session.post(f"{me}/voice", data={"consent": "true"}, files=upload(args.voice),
                                            timeout=90))
        show("use my voice", session.patch(me, json={"use_own_voice": True}))
        show(f"say {phrases[0]['text']} in my voice",
             session.post(f"{args.url}/speak", json={"text": phrases[0]["text"]}, timeout=90))
        show("forget my voice", session.delete(f"{me}/voice"))

    show("phrases", session.get(f"{me}/phrases"))
    show("stats", session.get(f"{me}/stats"))
    show("usage (403 unless OWNER_EMAIL is this account)", session.get(f"{me}/usage"), ok=False)
    show("delete the account", session.delete(me))
    show("who am I, after deleting (401)", session.get(f"{args.url}/auth/me"), ok=False)

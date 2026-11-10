"""Each user's Gnani calls in a rolling 24 hours: 20 Prisma (stt), 20 Timbre (tts) and 40 Prisma
for teaching phrases (enroll). Only calls sent to Gnani count."""
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

import db
import gnani
import prisma
import trainings


def user_id(client):
    return client.get("/auth/me").json()["id"]


def fill(uid, quota, n, age=timedelta(0)):
    """n calls sent for uid against quota, age ago."""
    at = (datetime.now(timezone.utc) - age).isoformat(timespec="seconds")
    kind = "tts" if quota == "tts" else "stt"
    db.transaction(*[("INSERT INTO api_calls (kind, cached, created_at, user_id, quota) VALUES (?, 0, ?, ?, ?)",
                      (kind, at, uid, quota))] * n)


def recognize(env, client, recording=None):
    env.fake.transcripts.append("पानी चाहिए")
    return client.post("/me/recognize", files=recording or env.recording())


def first_call_plus_a_day(quota):
    first = db.row("SELECT MIN(created_at) AS at FROM api_calls WHERE quota = ?", (quota,))["at"]
    return datetime.fromisoformat(first) + timedelta(hours=24)


def test_twenty_recordings_pass_and_the_21st_is_refused(env):
    client = env.signup()
    for _ in range(20):
        assert recognize(env, client).status_code == 200
    refused = recognize(env, client)
    assert refused.status_code == 429
    body = refused.json()
    assert {k: body[k] for k in ("error", "kind", "limit", "used")} == {
        "error": "daily_limit", "kind": "stt", "limit": 20, "used": 20}
    assert datetime.fromisoformat(body["resets_at"]) == first_call_plus_a_day("stt")
    assert len(env.fake.sent("stt")) == 20  # the 21st never reached Gnani


def test_twenty_spoken_phrases_pass_and_the_21st_is_refused(env):
    client = env.signup()
    for n in range(20):
        assert client.post("/speak", json={"text": f"नमस्ते {n}"}).status_code == 200
    refused = client.post("/speak", json={"text": "नमस्ते 20"})
    assert refused.status_code == 429
    assert {k: refused.json()[k] for k in ("error", "kind", "limit", "used")} == {
        "error": "daily_limit", "kind": "tts", "limit": 20, "used": 20}
    clone = client.post("/me/voice", data={"consent": "true"}, files=env.recording(6.0))
    assert clone.status_code == 429 and clone.json()["kind"] == "tts"  # cloning a voice is Timbre too
    assert len(env.fake.sent("tts")) == 20 and not env.fake.sent("clone")


def test_the_window_rolls_over_24_hours_not_a_calendar_day(env):
    client = env.signup()
    uid = user_id(client)
    fill(uid, "stt", 20, age=timedelta(hours=24, minutes=1))
    assert recognize(env, client).status_code == 200  # 24 h and a minute ago no longer counts
    assert client.get("/me/usage").json()["stt"]["used"] == 1

    fill(uid, "stt", 19, age=timedelta(hours=23, minutes=59))
    refused = recognize(env, client)
    assert refused.status_code == 429
    frees_in = datetime.fromisoformat(refused.json()["resets_at"]) - datetime.now(timezone.utc)
    assert timedelta(0) < frees_in <= timedelta(minutes=1)  # when the oldest of them stops counting


def test_cache_hits_never_count(env, tmp_path, monkeypatch):
    client = env.signup()
    uid = user_id(client)
    recording = env.recording()
    assert recognize(env, client, recording).status_code == 200
    fill(uid, "stt", 19)
    assert recognize(env, client, recording).status_code == 200  # heard before: from the cache, at 20 of 20
    for _ in range(2):
        assert client.post("/speak", json={"text": "नमस्ते"}).status_code == 200

    # Training audio made ahead of time is a file, not a Gnani call.
    key = next(iter(trainings.LIBRARY.audio))
    (tmp_path / f"{key}.mp3").write_bytes(b"ID3")
    monkeypatch.setattr(trainings, "WEB_AUDIO_DIR", str(tmp_path))
    assert client.get(f"/trainings/audio/{key}").status_code == 200

    usage = client.get("/me/usage").json()
    assert (usage["stt"]["used"], usage["tts"]["used"]) == (20, 1)
    assert len(env.fake.sent("stt")) == 1 and len(env.fake.sent("tts")) == 1


def test_a_retry_counts_once(env):
    client = env.signup()
    env.fake.failures = [500]
    assert recognize(env, client).status_code == 200
    assert len(env.fake.sent("stt")) == 2  # both reached Gnani, and both count against GNANI_CALL_LIMIT ...
    assert db.row("SELECT COUNT(*) AS n FROM api_calls WHERE cached = 0")["n"] == 2
    assert client.get("/me/usage").json()["stt"]["used"] == 1  # ... but the user made one request


def test_enroll_has_its_own_limit(env):
    client = env.signup()
    uid = user_id(client)
    fill(uid, "stt", 20)
    assert recognize(env, client).status_code == 429
    env.enroll_phrase(client, "पानी चाहिए")  # teaching Sunn still works with the stt limit used up
    fill(uid, "enroll", 38)
    env.enroll_phrase(client, "पानी चाहिए")  # the 40th

    phrase = next(p for p in client.get("/me/phrases").json() if p["text"] == "पानी चाहिए")
    refused = client.post("/me/enroll", data={"phrase_id": phrase["id"]}, files=env.recording())
    assert refused.status_code == 429
    assert {k: refused.json()[k] for k in ("error", "kind", "limit", "used")} == {
        "error": "daily_limit", "kind": "enroll", "limit": 40, "used": 40}
    word = client.get("/me/slot-words").json()[0]
    assert client.post(f"/me/slot-words/{word['id']}/enroll", files=env.recording()).json()["kind"] == "enroll"
    usage = client.get("/me/usage").json()
    assert (usage["stt"]["used"], usage["enroll"]["used"]) == (20, 40)


@pytest.mark.parametrize("setting", ["OWNER_EMAIL", "LIMIT_EXEMPT_EMAILS"])
def test_exempt_accounts_are_never_limited(env, monkeypatch, setting):
    client = env.signup()
    me = client.get("/auth/me").json()
    monkeypatch.setenv(setting, me["email"].upper() if setting == "OWNER_EMAIL" else f"x@example.com, {me['email']} ")
    for quota in ("stt", "tts", "enroll"):
        fill(me["id"], quota, 50)
    assert recognize(env, client).status_code == 200
    assert client.post("/speak", json={"text": "नमस्ते"}).status_code == 200
    env.enroll_phrase(client, "पानी चाहिए")

    other = env.signup()
    fill(user_id(other), "stt", 20)
    assert recognize(env, other).status_code == 429  # only the listed accounts


def test_two_requests_at_19_of_20_cannot_both_pass(env, monkeypatch):
    client = env.signup()
    uid = user_id(client)
    fill(uid, "stt", 19)

    def slow_gnani(*args, **kwargs):  # long enough for the other request to check the count meanwhile
        time.sleep(0.3)
        return env.fake(*args, **kwargs)

    monkeypatch.setattr(gnani.requests, "post", slow_gnani)
    start, results = threading.Barrier(2), []

    def call():
        start.wait()
        try:
            gnani.post("stt", prisma.URL, user_id=uid, quota="stt", data={}, files={})
            results.append("sent")
        except gnani.GnaniError as e:
            results.append(e.code)

    threads = [threading.Thread(target=call) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["daily_limit", "sent"]
    assert len(env.fake.sent("stt")) == 1


def test_signed_out_requests_get_401(env):
    client = env.client()
    for method, path, body in [
        ("get", "/me/usage", {}),
        ("post", "/me/recognize", {"files": env.recording()}),
        ("post", "/me/enroll", {"data": {"phrase_id": 1}, "files": env.recording()}),
        ("post", "/speak", {"json": {"text": "नमस्ते"}}),
        ("post", "/me/trainings/attempts", {"data": {"step_id": "s-and-sh-1-echo", "check": "true"},
                                            "files": env.recording()}),
    ]:
        response = getattr(client, method)(path, **body)
        assert response.status_code == 401 and response.json()["error"] == "not_logged_in", path
    assert not env.fake.requests


def test_my_usage_counts_each_limit(env):
    client = env.signup()
    assert client.get("/me/usage").json() == {"stt": {"used": 0, "limit": 20, "resets_at": None},
                                              "tts": {"used": 0, "limit": 20, "resets_at": None},
                                              "enroll": {"used": 0, "limit": 40, "resets_at": None}}
    for _ in range(2):
        recognize(env, client)
    client.post("/speak", json={"text": "नमस्ते"})
    for _ in range(3):
        env.enroll_phrase(client, "पानी चाहिए")

    usage = client.get("/me/usage").json()
    assert {quota: usage[quota]["used"] for quota in usage} == {"stt": 2, "tts": 1, "enroll": 3}
    for quota in usage:
        assert datetime.fromisoformat(usage[quota]["resets_at"]) == first_call_plus_a_day(quota)
    assert env.signup().get("/me/usage").json()["stt"]["used"] == 0  # someone else's are their own

"""GNANI_MOCK=1: every Gnani call is answered locally, and never behind a proxy."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import audio
import gnani
import gnani_mock
from conftest import wav

ROOT = Path(__file__).resolve().parent.parent


def test_mock_mode_answers_every_call_without_gnani(env, monkeypatch):
    monkeypatch.setenv("GNANI_MOCK", "1")
    client = env.signup()
    phrase = next(p for p in client.get("/me/phrases").json() if p["text"] == "पानी चाहिए")

    enrolled = client.post("/me/enroll", data={"phrase_id": phrase["id"]}, files=env.recording())
    assert enrolled.json()["hypothesis"] == "पानी चाहिए"  # the default for hi
    heard = client.post("/me/recognize", files=env.recording()).json()
    assert heard["candidates"][0]["phrase_id"] == phrase["id"]

    spoken = client.post("/speak", json={"text": "पानी चाहिए"})
    assert spoken.status_code == 200 and spoken.headers["content-type"] == "audio/wav"
    assert client.post("/me/voice", data={"consent": "true"}, files=env.recording(6)).json()["has_own_voice"]
    assert client.patch("/me", json={"use_own_voice": True}).status_code == 200
    assert client.post("/speak", json={"text": "पानी चाहिए"}).status_code == 200

    assert env.fake.requests == []  # nothing reached the network
    assert not os.path.exists("data/cache")  # and nothing landed in the real caches
    with pytest.raises(gnani.GnaniError):  # a call that slipped past prisma.py or speak.py
        gnani.post("stt", "https://example.invalid")


def test_mock_transcript_by_audio_hash(env, monkeypatch, tmp_path):
    monkeypatch.setenv("GNANI_MOCK", "1")
    recording = wav(1.0, 330)
    (tmp_path / "in.wav").write_bytes(recording)
    audio.to_wav(str(tmp_path / "in.wav"), str(tmp_path / "out.wav"))  # what the server stores
    digest = hashlib.sha256((tmp_path / "out.wav").read_bytes()).hexdigest()
    fixtures = tmp_path / "fixtures.json"
    fixtures.write_text(json.dumps({"default": {"hi": "x", "en": "x"}, "by_sha256": {digest: ""}}), encoding="utf-8")
    monkeypatch.setattr(gnani_mock, "FIXTURES", str(fixtures))

    client = env.signup()
    response = client.post("/me/recognize", files={"audio": ("r.wav", recording, "audio/wav")})
    assert response.status_code == 422 and response.json()["error"] == "no_speech"


def test_the_shipped_fixtures_cover_both_languages():
    with open(gnani_mock.FIXTURES, encoding="utf-8") as f:
        fixtures = json.load(f)
    assert set(fixtures["default"]) == {"hi", "en"} and isinstance(fixtures["by_sha256"], dict)


@pytest.mark.parametrize("trust_proxy, starts", [("0", True), ("1", False)])
def test_mock_mode_refuses_to_start_behind_a_proxy(tmp_path, trust_proxy, starts):
    env = {**os.environ, "GNANI_MOCK": "1", "TRUST_PROXY": trust_proxy, "DATA_DIR": str(tmp_path / "data"),
           "JWT_SECRET": "a-test-secret-long-enough-for-hs256-keys", "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run([sys.executable, "-c", "import api"], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=120)
    assert (result.returncode == 0) is starts, result.stderr
    assert ("GNANI_MOCK is on" in result.stderr) is starts
    if not starts:
        assert "GNANI_MOCK and TRUST_PROXY are both set" in result.stderr

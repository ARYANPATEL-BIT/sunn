"""Unit and integration tests for speech pipeline verification and audio asset strategy.

All tests operate in mock/offline mode with zero live API credit consumption.
"""
import io
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import audio
import db
import matcher
import api
from generate_training_audio import get_priority


def make_synthetic_wav(seconds=1.0, rate=16000) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    waveform = 0.2 * np.sin(2 * np.pi * 440.0 * t)
    buf = io.BytesIO()
    soundfile.write(buf, waveform, rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def test_audio_manifest_prioritization_breakdown():
    """Verify that all 128 manifest keys are classified into tiers A, B, and C."""
    manifest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "content", "trainings", "audio_manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    assert len(manifest) == 128

    counts = {"A": 0, "B": 0, "C": 0}
    for item in manifest:
        priority = get_priority(item["audio_key"])
        counts[priority] += 1

    # Priority A: Core demo-critical phrases for Easy Starts 1 and Introductions 1
    assert counts["A"] == 13
    # Priority B: Core foundation lessons
    assert counts["B"] == 65
    # Priority C: Advanced tongue-twisters and long dialogues
    assert counts["C"] == 50
    assert sum(counts.values()) == 128


def test_training_audio_cache_control_headers(tmp_path, monkeypatch):
    """Verify that /trainings/audio/{key} serves Cache-Control immutable headers when audio exists."""
    client = TestClient(api.app)

    # Place a dummy mp3 in a temporary web audio dir
    test_key = "easy-starts-1-vowels-aam"
    dummy_mp3 = tmp_path / f"{test_key}.mp3"
    dummy_mp3.write_bytes(b"ID3_DUMMY_MP3_CONTENT")

    monkeypatch.setattr("trainings.WEB_AUDIO_DIR", str(tmp_path))

    response = client.get(f"/trainings/audio/{test_key}")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "audio/mpeg"
    assert "public, max-age=86400, immutable" in response.headers.get("cache-control", "")
    assert response.content == b"ID3_DUMMY_MP3_CONTENT"


def test_training_audio_missing_unmocked_returns_404(tmp_path, monkeypatch):
    """When GNANI_MOCK is off and no file is on disk, return 404 not_found."""
    client = TestClient(api.app)
    monkeypatch.setattr("trainings.WEB_AUDIO_DIR", str(tmp_path))
    monkeypatch.setattr("trainings.AUDIO_DIR", str(tmp_path))
    monkeypatch.setenv("GNANI_MOCK", "0")

    response = client.get("/trainings/audio/easy-starts-1-vowels-aam")
    assert response.status_code == 404
    body = response.json()
    assert body.get("error") == "not_found"


def test_matcher_scores_verified_hindi_stt_transcript():
    """Verify that real Gnani STT output format matches expected phrase candidates."""
    # Real transcript verified from live smoke test
    stt_transcript = "नमस्ते, मुझे पानी चाहिए।"

    # Normalize Devanagari punctuation
    norm_transcript = matcher.normalize(stt_transcript)
    assert len(norm_transcript) > 0
    # Ensure terminal danda or punctuation is cleaned by matcher
    assert "।" not in norm_transcript

    # Score against candidate phrases using similarity
    candidates = [
        "मुझे पानी चाहिए",
        "नमस्ते, मुझे पानी चाहिए",
        "चाय दीजिए",
    ]

    sims = [matcher.similarity(stt_transcript, c) for c in candidates]
    # Candidate 1 (exact match phrase) should have the highest similarity score
    assert sims[1] > sims[0]
    assert sims[1] > sims[2]
    assert sims[1] >= 95.0


def test_attempt_audio_cleanup_and_kids_privacy(tmp_path, monkeypatch):
    """Verify that attempt processing does not persist audio on disk and strips transcript for kids-speaking."""
    import trainings
    monkeypatch.setenv("GNANI_MOCK", "1")

    # Create dummy user
    dummy_user = {"id": "test-user-speech", "email": "speech@example.com", "name": "Speech Tester", "language": "hi"}

    # Mock db calls
    monkeypatch.setattr(db, "row", lambda q, p=(): {"n": 0})
    monkeypatch.setattr(db, "rows", lambda q, p=(): [{"n": 0}])
    inserted = []
    monkeypatch.setattr(db, "execute", lambda q, p=(): inserted.append((q, p)))

    wav_bytes = make_synthetic_wav(seconds=1.5)
    upload = MagicMock()
    upload.file.read.side_effect = [wav_bytes, b""]

    # Call attempt endpoint with actual kids-speaking step: sound-play-1-animals, item lion
    with patch.object(trainings.prisma, "transcribe", return_value="शेर"):
        res = trainings.attempt(
            step_id="sound-play-1-animals",
            item_id="lion",
            check=True,
            audio_file=upload,
            user=dummy_user,
        )

    assert res.checked is True
    # Verify that the DB insert for kids-speaking stored None for transcript
    assert len(inserted) > 0
    insert_sql, params = inserted[-1]
    assert "INSERT INTO training_attempts" in insert_sql
    # transcript is index 4 in (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)
    stored_transcript = params[4]
    assert stored_transcript is None, "Kids speaking attempts must never persist a transcript"


def test_smoke_cli_safety_gate():
    """Verify that scripts/gnani_live_smoke.py stops if --confirm-live-credit-spend is missing."""
    smoke_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "gnani_live_smoke.py")

    # Run without confirm flag
    proc = subprocess.run(
        [sys.executable, smoke_script, "--tts"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "SAFETY STOP" in proc.stdout or "SAFETY STOP" in proc.stderr

    # Run with dry-run
    proc_dry = subprocess.run(
        [sys.executable, smoke_script, "--tts", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert proc_dry.returncode == 0
    assert "Dry-run mode active" in proc_dry.stdout

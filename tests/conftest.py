import io
import json
import os
import uuid
from collections import defaultdict, deque
from itertools import count

import numpy as np
import pytest
import requests
import soundfile

# Set before the app is imported: auth refuses to start without a JWT secret, and load_dotenv
# never overrides a variable that is already set, so the real key in .env is never used here.
os.environ["JWT_SECRET"] = "a-test-secret-long-enough-for-hs256-keys"
os.environ["GNANI_API_KEY"] = "test-key"
os.environ["DATA_DIR"] = "data"  # relative, so each test's data lands in its own folder
# The judge and the reranker are off, and the LLM is unreachable, unless a test sets them.
os.environ["LLM_ENABLED"] = "0"
os.environ["LLM_BASE_URL"] = "https://llm.invalid/v1"
os.environ["LLM_API_KEY"] = "test-llm-key"
os.environ["LLM_MODEL"] = "test-model"
os.environ["RERANKER_ENABLED"] = "0"
for name in ("LLM_MODE", "LLM_MARGIN", "LLM_MIN_SCORE", "LLM_TIMEOUT_S", "LLM_RATE_PER_MIN", "LLM_REASONING_EFFORT",
             "RERANKER_PATH", "RERANKER_WEIGHT", "RERANKER_THREADS"):
    os.environ[name] = ""  # empty is the code's default

import auth  # noqa: E402
import db  # noqa: E402
import gnani  # noqa: E402
import prisma  # noqa: E402
import speak  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

EMBEDDING = {"embedding": "ZmFrZQ==", "shape": [1, 768], "dtype": "torch.bfloat16"}


def wav(seconds=1.0, freq=440.0, rate=16000):
    t = np.arange(int(seconds * rate)) / rate
    buffer = io.BytesIO()
    soundfile.write(buffer, 0.3 * np.sin(2 * np.pi * freq * t), rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def reply(status, body=None, content=None):
    response = requests.Response()
    response.status_code = status
    response._content = content if content is not None else json.dumps(body).encode()
    return response


class FakeGnani:
    """Stands in for requests.post inside gnani.py, so no test reaches Gnani. Each STT request
    takes the next of transcripts; failures (an exception or a status code) are used up first."""

    def __init__(self):
        self.transcripts, self.failures, self.requests = [], [], []

    def __call__(self, url, headers, timeout, **request):
        assert headers["X-API-Key-ID"] == "test-key" and timeout == gnani.TIMEOUT
        kind = {prisma.URL: "stt", speak.URL: "tts", speak.CLONE_URL: "clone"}[url]
        self.requests.append((kind, request))
        if self.failures:
            failure = self.failures.pop(0)
            if isinstance(failure, Exception):
                raise failure
            return reply(failure, {"success": False, "error": {"type": "X", "message": "refused"}})
        if kind == "stt":
            transcript = self.transcripts.pop(0) if self.transcripts else "नमस्ते"
            return reply(200, {"success": True, "transcript": transcript})
        if kind == "clone":
            return reply(200, {"success": True, "data": {"voice_clone_embedding": EMBEDDING}})
        return reply(200, content=wav(0.5, rate=44100))

    def sent(self, kind):
        return [request for k, request in self.requests if k == kind]


class Env:
    def __init__(self, fake):
        self.fake, self.freqs = fake, count(200, 37)

    def client(self):
        # https: the session cookie is Secure, so it is only sent back over https.
        import api  # here, not at the top: importing it runs db.init() in the current folder

        return TestClient(api.app, base_url="https://testserver")

    def signup(self, language="hi"):
        client = self.client()
        response = client.post("/auth/signup", json={
            "name": "Test", "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "password123",
            "language": language, "consent": True})
        assert response.status_code == 200, response.text
        client.post("/me/phrases/default").raise_for_status()
        return client

    def recording(self, seconds=1.0):
        """A new recording each call (its own pitch), so no two hit the same cache entry."""
        return {"audio": ("recording.wav", wav(seconds, next(self.freqs)), "audio/wav")}

    def enroll(self, client, path, transcript, recording=None):
        """POST a recording to an enroll path, heard by Prisma as transcript."""
        self.fake.transcripts.append(transcript)
        response = client.post(path, files=recording or self.recording())
        assert response.status_code == 200, response.text
        return response.json()

    def enroll_phrase(self, client, text, transcript=None):
        phrase = next(p for p in client.get("/me/phrases").json() if p["text"] == text)
        self.fake.transcripts.append(transcript or text)
        response = client.post("/me/enroll", data={"phrase_id": phrase["id"]}, files=self.recording())
        assert response.status_code == 200, response.text
        return phrase

    def recognize(self, client, transcript, context=None, recording=None):
        self.fake.transcripts.append(transcript)
        response = client.post("/me/recognize", data={"context": context} if context else {},
                               files=recording or self.recording())
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture
def env(tmp_path, monkeypatch):
    """The API in an empty folder of its own: its own data/app.db, recordings and caches."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GNANI_CALL_LIMIT", "4000")
    monkeypatch.setenv("DAILY_CALL_CAP_PER_USER", "60")
    monkeypatch.delenv("OWNER_EMAIL", raising=False)
    monkeypatch.delenv("DEMO_INVITE_CODE", raising=False)  # open sign-up, whatever .env says
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("TRUST_PROXY", raising=False)
    monkeypatch.delenv("GNANI_MOCK", raising=False)  # FakeGnani, not mock mode, unless a test sets it
    monkeypatch.setattr(auth, "_failures", defaultdict(deque))  # no lockouts left by another test
    db.init()
    fake = FakeGnani()
    monkeypatch.setattr(gnani.requests, "post", fake)
    return Env(fake)

"""scripts/load_demo.py and scripts/evaluate.py, run against the faked Gnani. These check the
scripts' logic; the numbers here are made up by the test and are not results."""
import csv
import os

import pytest

import db
import evaluate
import load_demo
from conftest import wav

URL = "https://testserver"
MANIFEST = [  # phrase, file, kind, source, what Prisma hears
    ("पानी चाहिए", "water-1.wav", "enroll", "simulated", "paani chahiye"),
    ("पानी चाहिए", "water-2.wav", "enroll", "simulated", "pani chahie"),
    ("दर्द हो रहा है", "pain-1.wav", "enroll", "pilot", "dard ho raha hai"),
    ("पानी चाहिए", "water-3.wav", "test", "simulated", "paani chahiyee"),
    ("दर्द हो रहा है", "pain-2.wav", "test", "pilot", ""),  # Prisma heard nothing: a miss
]


def demo_folder(tmp_path, rows=MANIFEST):
    folder = tmp_path / "demo"
    folder.mkdir(exist_ok=True)
    with open(folder / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(load_demo.COLUMNS)
        for n, (phrase, file, kind, source, _) in enumerate(rows):
            writer.writerow([phrase, file, kind, source])
            (folder / file).write_bytes(wav(1.0, 300 + 40 * n))
    return str(folder)


def test_the_manifest_is_checked_before_anything_is_sent(tmp_path):
    folder = demo_folder(tmp_path, MANIFEST + [("पानी चाहिए", "water-4.wav", "enroll", "real", "")])
    with pytest.raises(SystemExit, match="source is 'real'"):
        load_demo.read_manifest(folder)
    folder = demo_folder(tmp_path)
    (tmp_path / "demo" / "water-3.wav").write_bytes((tmp_path / "demo" / "water-1.wav").read_bytes())
    with pytest.raises(SystemExit, match="both enroll and test"):
        load_demo.read_manifest(folder)


def test_load_then_evaluate(env, tmp_path):
    folder = demo_folder(tmp_path)
    rows = load_demo.read_manifest(folder)
    env.fake.transcripts += [heard for *_, kind, _, heard in MANIFEST if kind == "enroll"]
    session = env.client()
    load_demo.sign_in(session, URL, "demo@example.com", "password123", "Demo", "hi", None)
    assert load_demo.load(session, URL, rows) == 3
    phrases = {p["text"]: p for p in session.get("/me/phrases").json()}
    assert phrases["पानी चाहिए"]["enrolled"] == 2 and phrases["पानी चाहिए"]["sources"] == ["simulated"]
    assert phrases["दर्द हो रहा है"]["sources"] == ["pilot"]

    again = env.client()  # a second run signs in to the same account and sends nothing new
    load_demo.sign_in(again, URL, "demo@example.com", "password123", "Demo", "hi", None)
    assert load_demo.load(again, URL, rows) == 0 and len(env.fake.sent("stt")) == 3

    env.fake.transcripts += [heard for *_, kind, _, heard in MANIFEST if kind == "test"]
    samples, summary, bank = evaluate.evaluate("demo@example.com", folder)
    assert [(s["phrase"], s["hypothesis"], s["top1"], s["context"]) for s in samples] == [
        ("पानी चाहिए", "paani chahiyee", 1, "home"), ("दर्द हो रहा है", "", 0, "hospital")]
    found = {(r["source"], r["metric"]): (r["correct"], r["n"]) for r in summary}
    assert found["all", "raw_exact"] == (0, 2) and found["all", "top1"] == (1, 2) and found["all", "top3"] == (1, 2)
    assert found["pilot", "top1"] == (0, 1) and found["simulated", "top1_k1"] == (1, 1)
    assert ("torgo", "top1") not in found  # no torgo rows, so no torgo numbers
    assert db.rows("SELECT DISTINCT user_id FROM api_calls WHERE kind = 'stt' AND cached = 0 AND id > 3") == [
        {"user_id": None}]  # the evaluation's calls are no account's

    os.makedirs(evaluate.RESULTS)
    assert [os.path.basename(p) for p in evaluate.plot("demo", summary, samples, bank)] == [
        "eval_demo_accuracy.png", "eval_demo_context.png", "eval_demo_enrollments.png"]
    evaluate.evaluate("demo@example.com", folder)  # a second run is all cached
    assert len(env.fake.sent("stt")) == 5

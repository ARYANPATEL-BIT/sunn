"""Trainings (docs/TRAININGS_CONTRACT.md): each route answers the contract's shape, and the
content in content/trainings/ passes scripts/validate_trainings.py."""
from datetime import datetime, timedelta, timezone
import json
import os
import shutil

import pytest

import db
import trainings_content
import validate_trainings

TEXT = {"en", "hi"}
CATEGORY = {"id", "title", "subtitle", "description", "icon", "audience", "order"}
STEP = {"id", "type", "title"}


def test_categories_come_in_order_with_progress_only_when_signed_in(env):
    signed_out = env.client().get("/trainings/categories").json()
    assert [c["id"] for c in signed_out] == ["smooth-speaking", "clear-sounds", "kids-speaking", "everyday-talk"]
    assert all(set(c) == CATEGORY | {"course_count", "percent"} and set(c["title"]) == TEXT for c in signed_out)
    assert all(c["course_count"] == 1 and c["percent"] is None for c in signed_out)
    signed_in = env.signup().get("/trainings/categories").json()
    assert all(isinstance(c["percent"], int) for c in signed_in)


def test_category_lists_its_courses(env):
    found = env.client().get("/trainings/categories/clear-sounds").json()
    assert set(found) == CATEGORY | {"courses"}
    [course] = found["courses"]
    assert set(course) == {"id", "title", "summary", "level", "minutes", "practice_lang", "lesson_count", "percent"}
    assert (course["id"], course["lesson_count"], course["percent"]) == ("s-and-sh", 4, None)
    assert env.client().get("/trainings/categories/nowhere").json()["error"] == "not_found"


def test_course_lists_its_lessons(env):
    client = env.signup()
    found = client.get("/trainings/courses/easy-starts").json()
    assert set(found) == {"id", "category_id", "title", "summary", "what_you_practise", "level", "minutes",
                          "practice_lang", "percent", "lessons"}
    assert all(set(lesson) == {"id", "title", "minutes", "step_count", "completed"} for lesson in found["lessons"])
    assert [lesson["completed"] for lesson in found["lessons"]] == [False, False, False, False] and found["percent"] == 0
    # After completing the first lesson
    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 5, "completed": True})
    updated = client.get("/trainings/courses/easy-starts").json()
    assert [lesson["completed"] for lesson in updated["lessons"]] == [True, False, False, False] and updated["percent"] == 25
    assert env.client().get("/trainings/courses/nowhere").status_code == 404


def test_lesson_has_every_step_with_every_field(env):
    found = env.client().get("/trainings/lessons/easy-starts-1").json()
    assert set(found) == {"id", "title", "minutes", "steps", "course_id", "category_id", "practice_lang",
                          "next_lesson_id"}
    assert found["next_lesson_id"] == "easy-starts-2"
    assert all(STEP <= set(step) for step in found["steps"])
    [words] = [step for step in found["steps"] if step["type"] == "listen_repeat"]
    assert all(set(item) == {"id", "text", "latin", "meaning_en", "focus_sound", "audio_key"} for item in words["items"])
    assert env.client().get("/trainings/lessons/nowhere").status_code == 404


def test_audio_is_served_once_made(env, monkeypatch):
    client = env.client()
    assert client.get("/trainings/audio/easy-starts-1-vowels-aam").json()["error"] == "not_found"  # not made yet
    assert client.get("/trainings/audio/not-listed").status_code == 404
    monkeypatch.setenv("GNANI_MOCK", "1")
    assert client.get("/trainings/audio/easy-starts-1-vowels-aam").headers["content-type"] == "audio/wav"


def test_progress(env):
    client = env.signup()
    empty = client.get("/me/trainings/progress").json()
    assert set(empty) == {"courses", "resume", "lessons_done", "minutes_practised", "days_this_week"}
    assert empty["courses"] == []
    assert empty["resume"] is None
    assert empty["lessons_done"] == 0

    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 2, "completed": False})
    found = client.get("/me/trainings/progress").json()
    assert set(found) == {"courses", "resume", "lessons_done", "minutes_practised", "days_this_week"}
    assert all(set(c) == {"id", "percent"} for c in found["courses"])
    assert found["resume"] == {"course_id": "easy-starts", "lesson_id": "easy-starts-1", "step_index": 2}


def test_save_progress(env):
    client = env.signup()
    found = client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-2", "step_index": 6, "completed": True})
    assert found.json() == {"lesson_id": "easy-starts-2", "course_id": "easy-starts", "step_index": 6,
                            "completed": True, "course_percent": 25}
    past_the_end = client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-2", "step_index": 7,
                                                               "completed": False})
    assert past_the_end.json()["error"] == "invalid_input"


def test_reflect(env):
    client = env.signup()
    body = {"lesson_id": "easy-starts-1", "step_id": "easy-starts-1-reflect", "feeling": "okay"}
    assert client.post("/me/trainings/reflect", json=body).json() == {"ok": True}
    not_a_reflect_step = client.post("/me/trainings/reflect", json={**body, "step_id": "easy-starts-1-welcome"})
    assert not_a_reflect_step.status_code == 404
    assert client.post("/me/trainings/reflect", json={**body, "feeling": "great"}).status_code == 422
    # Verify reflection row was stored
    row = db.row("SELECT feeling FROM training_reflections WHERE lesson_id = ? AND step_id = ?",
                 ("easy-starts-1", "easy-starts-1-reflect"))
    assert row and row["feeling"] == "okay"


def test_attempts(env):
    client, keys = env.signup(), {"checked", "words", "similarity", "wpm", "pace", "message_key", "checks_left_today"}

    def attempt(rec=None, **form):
        response = client.post("/me/trainings/attempts", data=form, files=rec or env.recording())
        assert set(response.json()) == keys or response.status_code != 200, response.text
        return response.json()

    # Checked attempt with words feedback (clear-sounds)
    env.fake.transcripts.append("सोनू सुबह सात बजे उठा")
    words = attempt(step_id="s-and-sh-1-echo", check="true")
    assert words["checked"] and words["wpm"] is None and {w["status"] for w in words["words"]} <= {"clear", "practise"}
    assert words["checks_left_today"] == 19
    stt_count = len(env.fake.sent("stt"))
    assert stt_count == 1

    # Checked attempt with pace feedback (smooth-speaking)
    env.fake.transcripts.append("आज मौसम अच्छा है")
    pace = attempt(step_id="easy-starts-1-together", check="true")
    assert pace["checked"] and pace["pace"] in ("slower", "good", "faster") and pace["words"] is None
    assert pace["checks_left_today"] == 18
    assert len(env.fake.sent("stt")) == 2

    # Unchecked attempt (check=false): Prisma is NOT called
    unchecked = attempt(step_id="easy-starts-1-vowels", item_id="aam", check="false")
    assert not unchecked["checked"] and unchecked["message_key"] == "practised"
    assert unchecked["checks_left_today"] == 18  # Not decremented
    assert len(env.fake.sent("stt")) == 2  # No additional STT call

    # Bad step / item validations
    assert attempt(step_id="easy-starts-1-vowels", item_id="nowhere")["error"] == "not_found"
    assert attempt(step_id="easy-starts-1-welcome")["error"] == "invalid_input"  # an intro takes no recording

    # Audio length limits: 0.2 s is too short, 31 s is too long
    too_short = attempt(rec=env.recording(seconds=0.2), step_id="easy-starts-1-vowels", item_id="aam", check="false")
    assert too_short["error"] == "audio_too_short"
    too_long = attempt(rec=env.recording(seconds=31.0), step_id="easy-starts-1-vowels", item_id="aam", check="false")
    assert too_long["error"] == "audio_too_long"


def test_tricky_sounds_empty_for_new_user(env):
    found = env.signup().get("/me/trainings/tricky-sounds").json()
    assert found == []


def test_tricky_sounds_thresholds(env):
    client = env.signup()
    uid = db.row("SELECT id FROM users ORDER BY id DESC LIMIT 1")["id"]

    # 1. Speak substitutions: below threshold 5 -> empty
    phrase_id = db.execute("INSERT INTO phrases (user_id, text) VALUES (?, ?)", (uid, "पानी"))
    for _ in range(4):
        db.execute(
            "INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (uid, phrase_id, "mock.wav", "बानी", "enroll", "2026-11-09T10:00:00Z"),
        )
    assert client.get("/me/trainings/tricky-sounds").json() == []

    # 5th substitution triggers qualification for 'p'
    db.execute(
        "INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (uid, phrase_id, "mock.wav", "बानी", "enroll", "2026-11-09T10:00:00Z"),
    )
    sounds = client.get("/me/trainings/tricky-sounds").json()
    assert len(sounds) == 1
    assert sounds[0]["sound_id"] == "p"
    assert sounds[0]["why_key"] == "heard_in_speak"
    assert sounds[0]["evidence"]["speak"] == 5
    assert sounds[0]["practise_lesson_id"] == "easy-starts-2"

    # 2. Practice attempts: 8 total words with >40% practise rate triggers qualification
    # s-and-sh-1-echo has target: 'सोनू सुबह सात बजे स्कूल जाता है' (4 's' words)
    # 1 attempt gives 4 words (< 8) -> not qualified yet
    db.execute(
        "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, "s-and-sh-1", "s-and-sh-1-echo", None, "कल हम घर गए", 0.1, None, 1, "2026-11-09T10:00:00Z"),
    )
    sounds = client.get("/me/trainings/tricky-sounds").json()
    assert [s["sound_id"] for s in sounds] == ["p"]

    # 2nd attempt brings 's' words to 8 (>= 8) with 100% practise rate -> qualifies!
    db.execute(
        "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, "s-and-sh-1", "s-and-sh-1-echo", None, "कल हम घर गए", 0.1, None, 1, "2026-11-09T10:00:00Z"),
    )
    sounds = client.get("/me/trainings/tricky-sounds").json()
    assert {s["sound_id"] for s in sounds} == {"p", "s"}
    s_sound = next(s for s in sounds if s["sound_id"] == "s")
    assert s_sound["why_key"] == "heard_in_practice"
    assert s_sound["evidence"]["practice"] == 8
    assert s_sound["practise_lesson_id"] == "s-and-sh-1"

    # 3. Self reflection: 2 'hard' reflections on a lesson focusing on 'r' and 'l'
    # 1 reflection -> does not qualify
    db.execute(
        "INSERT INTO training_reflections (user_id, lesson_id, step_id, feeling, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (uid, "s-and-sh-2", "s-and-sh-2-reflect", "hard", "2026-11-09T10:00:00Z"),
    )
    sounds = client.get("/me/trainings/tricky-sounds").json()
    assert {s["sound_id"] for s in sounds} == {"p", "s"}

    # 2nd and 3rd reflection -> qualifies 'r' and 'l' with you_said_hard
    for _ in range(2):
        db.execute(
            "INSERT INTO training_reflections (user_id, lesson_id, step_id, feeling, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (uid, "s-and-sh-2", "s-and-sh-2-reflect", "hard", "2026-11-09T10:01:00Z"),
        )
    # We now have 4 qualifying sounds ('p', 's', 'r', 'l'). API must return top 3!
    sounds = client.get("/me/trainings/tricky-sounds").json()
    assert len(sounds) == 3
    assert sounds[0]["sound_id"] == "s"
    assert sounds[1]["sound_id"] == "p"
    assert sounds[2]["sound_id"] in ("r", "l")
    assert sounds[2]["why_key"] == "you_said_hard"


def test_alternatives_library_ranking_and_avoids(env):
    client = env.signup()
    uid = db.row("SELECT id FROM users ORDER BY id DESC LIMIT 1")["id"]

    # Give user tricky sound 'p'
    phrase_id = db.execute("INSERT INTO phrases (user_id, text) VALUES (?, ?)", (uid, "पानी"))
    for _ in range(5):
        db.execute(
            "INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (uid, phrase_id, "mock.wav", "बानी", "enroll", "2026-11-09T10:00:00Z"),
        )
    tricky = client.get("/me/trainings/tricky-sounds").json()
    assert [t["sound_id"] for t in tricky] == ["p"]

    # Request alternatives for "पानी चाहिए"
    res = client.post("/me/trainings/alternatives", json={"text": "पानी चाहिए", "lang": "hi"}).json()
    assert res["meaning_en"] == "I need water"
    assert len(res["alternatives"]) <= 4
    assert all(a["source"] == "library" for a in res["alternatives"])

    # First alternative avoids 'p'
    first_alt = res["alternatives"][0]
    assert "p" in first_alt["avoids"]

    # Sorter order: fewer tricky sounds first
    for i in range(len(res["alternatives"]) - 1):
        curr_tricky = len([s for s in ["p"] if s not in res["alternatives"][i]["avoids"]])
        next_tricky = len([s for s in ["p"] if s not in res["alternatives"][i + 1]["avoids"]])
        assert curr_tricky <= next_tricky


def test_alternatives_urgent_retains_urgency(env):
    client = env.signup()

    # Search for an urgent meaning
    res = client.post("/me/trainings/alternatives", json={"text": "मदद कीजिए", "lang": "hi"}).json()
    assert res["meaning_en"]
    assert len(res["alternatives"]) > 0
    for a in res["alternatives"]:
        assert not any(w in a["text"].lower() for w in ["fine", "all good", "no problem", "सब ठीक"])


def test_alternatives_groq_mocked(env, monkeypatch):
    import json as json_mod
    import httpx
    import trainings

    client = env.signup()
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("LLM_API_KEY", "mock-groq-key")

    calls = []

    # 1. Valid assistant response
    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        payload = {
            "choices": [{
                "message": {
                    "content": json_mod.dumps({
                        "meaning_en": "Please open the window",
                        "alternatives": [
                            {"text": "खिड़की खोल दीजिए", "latin": "khidki khol deejiye"},
                            {"text": "खिड़की खोलें", "latin": "khidki kholein"},
                        ]
                    })
                }
            }]
        }
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(trainings.httpx, "post", fake_post)

    # Input not in library
    res = client.post("/me/trainings/alternatives", json={"text": "कृपया खिड़की खोलिए", "lang": "hi"}).json()
    assert res["meaning_en"] == "Please open the window"
    assert len(res["alternatives"]) == 2
    assert all(a["source"] == "assistant" for a in res["alternatives"])

    # 2. Bad JSON from Groq: handled gracefully without 500 error
    def fake_bad_json(url, headers=None, json=None, timeout=None):
        return httpx.Response(200, text="Invalid json response", request=httpx.Request("POST", url))

    monkeypatch.setattr(trainings.httpx, "post", fake_bad_json)
    trainings._alternatives_cache.clear()

    bad_res = client.post("/me/trainings/alternatives", json={"text": "कुछ नया बोलिए", "lang": "hi"})
    assert bad_res.status_code == 200
    assert bad_res.json()["alternatives"] == []

    # 3. Timeout from Groq: handled gracefully without 500 error
    def fake_timeout(url, headers=None, json=None, timeout=None):
        raise httpx.TimeoutException("Groq timed out")

    monkeypatch.setattr(trainings.httpx, "post", fake_timeout)
    trainings._alternatives_cache.clear()

    to_res = client.post("/me/trainings/alternatives", json={"text": "कुछ और बोलिए", "lang": "hi"})
    assert to_res.status_code == 200
    assert to_res.json()["alternatives"] == []

    # 4. LLM_ENABLED=false: skips Groq cleanly
    monkeypatch.setenv("LLM_ENABLED", "0")
    calls.clear()
    off_res = client.post("/me/trainings/alternatives", json={"text": "कोई अनोखा वाक्य", "lang": "hi"})
    assert off_res.status_code == 200
    assert len(calls) == 0


@pytest.mark.parametrize("method, path", [
    ("GET", "/me/trainings/progress"), ("POST", "/me/trainings/progress"), ("POST", "/me/trainings/reflect"),
    ("POST", "/me/trainings/attempts"), ("GET", "/me/trainings/tricky-sounds"), ("POST", "/me/trainings/alternatives")])
def test_me_routes_need_a_session(env, method, path):
    assert env.client().request(method, path).json()["error"] == "not_logged_in"


def test_the_content_fits_the_contract_and_each_course_uses_every_step_type():
    assert validate_trainings.check() == []
    for course in trainings_content.load().courses.values():
        assert {step.type for lesson in course.lessons for step in lesson.steps} == set(trainings_content.STEP_TYPES)


def test_the_validator_finds_words_feedback_in_smooth_speaking(tmp_path):
    root = tmp_path / "trainings"
    shutil.copytree(trainings_content.ROOT, root)
    path = root / "courses" / "easy-starts.json"
    course = json.loads(path.read_text(encoding="utf-8"))
    course["lessons"][0]["steps"][3]["feedback"] = "words"
    course["lessons"][0]["steps"][3]["items"][0]["audio_key"] = "unlisted"
    path.write_text(json.dumps(course, ensure_ascii=False), encoding="utf-8")
    found = validate_trainings.check(os.fspath(root))
    assert any("feedback none or pace" in p for p in found), found
    assert any("unlisted is not listed" in p for p in found), found


def test_progress_upsert_never_goes_backwards(env):
    client = env.signup()
    first = client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 5, "completed": True}).json()
    assert first["completed"] is True
    assert first["course_percent"] == 25

    revisit = client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 2, "completed": False}).json()
    assert revisit["completed"] is True
    assert revisit["step_index"] == 2
    assert revisit["course_percent"] == 25

    course_data = client.get("/trainings/courses/easy-starts").json()
    assert course_data["lessons"][0]["completed"] is True


def test_resume_picks_the_right_lesson(env):
    client = env.signup()
    assert client.get("/me/trainings/progress").json()["resume"] is None

    # Start lesson 1 (unfinished)
    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 1, "completed": False})
    p1 = client.get("/me/trainings/progress").json()
    assert p1["resume"] == {"course_id": "easy-starts", "lesson_id": "easy-starts-1", "step_index": 1}

    # Start lesson 2 (unfinished) - becomes most recently updated unfinished lesson
    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-2", "step_index": 3, "completed": False})
    p2 = client.get("/me/trainings/progress").json()
    assert p2["resume"] == {"course_id": "easy-starts", "lesson_id": "easy-starts-2", "step_index": 3}

    # Complete lesson 2 - resume falls back to lesson 1 which is still unfinished
    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-2", "step_index": 6, "completed": True})
    p3 = client.get("/me/trainings/progress").json()
    assert p3["resume"] == {"course_id": "easy-starts", "lesson_id": "easy-starts-1", "step_index": 1}

    # Complete lesson 1 - no unfinished lessons left
    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 5, "completed": True})
    p4 = client.get("/me/trainings/progress").json()
    assert p4["resume"] is None


def test_days_this_week(env):
    import auth
    client = env.signup()
    uid = auth.user_id_from_token(client.cookies.get("sunn_session"))
    assert client.get("/me/trainings/progress").json()["days_this_week"] == 0

    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 0, "completed": False})
    assert client.get("/me/trainings/progress").json()["days_this_week"] == 1

    today = datetime.now(timezone.utc).date()
    d1 = (today - timedelta(days=2)).isoformat()
    d2 = (today - timedelta(days=5)).isoformat()
    d_old = (today - timedelta(days=12)).isoformat()
    db.execute("INSERT INTO training_minutes (user_id, day, seconds) VALUES (?, ?, ?)", (uid, d1, 180))
    db.execute("INSERT INTO training_minutes (user_id, day, seconds) VALUES (?, ?, ?)", (uid, d2, 240))
    db.execute("INSERT INTO training_minutes (user_id, day, seconds) VALUES (?, ?, ?)", (uid, d_old, 300))

    assert client.get("/me/trainings/progress").json()["days_this_week"] == 3


def test_percent_math(env):
    client = env.signup()
    assert client.get("/trainings/courses/easy-starts").json()["percent"] == 0

    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-1", "step_index": 5, "completed": True})
    assert client.get("/trainings/courses/easy-starts").json()["percent"] == 25

    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-2", "step_index": 6, "completed": True})
    assert client.get("/trainings/courses/easy-starts").json()["percent"] == 50

    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-3", "step_index": 6, "completed": True})
    assert client.get("/trainings/courses/easy-starts").json()["percent"] == 75

    client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-4", "step_index": 5, "completed": True})
    assert client.get("/trainings/courses/easy-starts").json()["percent"] == 100


def test_unknown_lesson_ids_rejected(env):
    client = env.signup()
    res = client.post("/me/trainings/progress", json={"lesson_id": "non-existent-lesson", "step_index": 0, "completed": False})
    assert res.status_code == 404 and res.json()["error"] == "not_found"

    res_reflect = client.post("/me/trainings/reflect", json={"lesson_id": "non-existent-lesson", "step_id": "easy-starts-1-reflect", "feeling": "okay"})
    assert res_reflect.status_code == 404 and res_reflect.json()["error"] == "not_found"

    res_reflect_step = client.post("/me/trainings/reflect", json={"lesson_id": "easy-starts-1", "step_id": "non-existent-step", "feeling": "okay"})
    assert res_reflect_step.status_code == 404 and res_reflect_step.json()["error"] == "not_found"


def test_browsing_works_logged_out(env):
    client = env.client()
    cats = client.get("/trainings/categories").json()
    assert len(cats) == 4
    assert all(c["percent"] is None for c in cats)

    cat = client.get("/trainings/categories/smooth-speaking").json()
    assert cat["courses"][0]["percent"] is None

    course_data = client.get("/trainings/courses/easy-starts").json()
    assert course_data["percent"] is None
    assert all(l["completed"] is False for l in course_data["lessons"])

    lesson_data = client.get("/trainings/lessons/easy-starts-1").json()
    assert lesson_data["id"] == "easy-starts-1"


def test_feedback_rules_per_category(env):
    client = env.signup()

    # 1. smooth-speaking never returns words, only pace
    env.fake.transcripts.append("आज मौसम अच्छा है")
    smooth = client.post("/me/trainings/attempts", data={"step_id": "easy-starts-1-together", "check": "true"},
                         files=env.recording()).json()
    assert smooth["checked"] is True and smooth["words"] is None and smooth["wpm"] is not None

    # 2. kids-speaking never returns words
    env.fake.transcripts.append("शेर दहाड़ता है")
    kids = client.post("/me/trainings/attempts", data={"step_id": "sound-play-1-choral", "check": "true"},
                       files=env.recording()).json()
    assert kids["checked"] is True and kids["words"] is None

    # 3. clear-sounds (feedback=words) returns words and similarity, wpm is None
    env.fake.transcripts.append("सोनू सुबह सात बजे उठा")
    clear = client.post("/me/trainings/attempts", data={"step_id": "s-and-sh-1-echo", "check": "true"},
                        files=env.recording()).json()
    assert clear["checked"] is True and clear["words"] is not None and clear["similarity"] is not None
    assert clear["wpm"] is None and clear["pace"] is None


def test_attempts_cap_reaching_zero(env):
    import auth
    client = env.signup()
    uid = auth.user_id_from_token(client.cookies.get("sunn_session"))
    today = datetime.now(timezone.utc).date().isoformat()
    now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Insert 20 checks today to exhaust daily allowance
    for i in range(20):
        db.execute(
            "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, "easy-starts-1", "easy-starts-1-together", None, "test", None, 80, 1, now_str),
        )

    # Calling with check=true when cap is 0 returns checked=false with friendly message
    env.fake.transcripts.append("आज मौसम अच्छा है")
    res = client.post("/me/trainings/attempts", data={"step_id": "easy-starts-1-together", "check": "true"},
                      files=env.recording())
    assert res.status_code == 200
    data = res.json()
    assert data["checked"] is False
    assert data["message_key"] == "no_checks_left"
    assert data["checks_left_today"] == 0
    # STT should not have been called because cap was already 0
    assert not env.fake.sent("stt")


def test_kids_attempts_store_no_transcript(env):
    client = env.signup()

    # Kids attempt
    env.fake.transcripts.append("हाथी धीरे चलता है")
    client.post("/me/trainings/attempts", data={"step_id": "sound-play-1-choral", "check": "true"},
                files=env.recording())
    kids_row = db.row("SELECT transcript FROM training_attempts WHERE step_id = 'sound-play-1-choral' ORDER BY id DESC LIMIT 1")
    assert kids_row is not None and kids_row["transcript"] is None

    # Adult attempt
    env.fake.transcripts.append("सोनू सुबह सात बजे उठा")
    client.post("/me/trainings/attempts", data={"step_id": "s-and-sh-1-echo", "check": "true"},
                files=env.recording())
    adult_row = db.row("SELECT transcript FROM training_attempts WHERE step_id = 's-and-sh-1-echo' ORDER BY id DESC LIMIT 1")
    assert adult_row is not None and adult_row["transcript"] == "सोनू सुबह सात बजे उठा"


def test_alignment_hindi_and_hinglish():
    from trainings import align_words

    # Exact Hindi
    exact = align_words("सोनू सुबह सात बजे उठा", "सोनू सुबह सात बजे उठा")
    assert all(w.status == "clear" for w in exact)

    # Missing word
    partial = align_words("सोनू सुबह सात बजे उठा", "सोनू सात बजे उठा")
    statuses = {w.text: w.status for w in partial}
    assert statuses["सुबह"] == "practise"
    assert statuses["सोनू"] == "clear" and statuses["सात"] == "clear"

    # Hinglish romanized transcript aligns to Devanagari target
    hinglish = align_words("सोनू सुबह सात", "sonu subah saat")
    assert all(w.status == "clear" for w in hinglish)

    # Mispronounced word gets marked practise
    mispronounced = align_words("सोनू सुबह सात", "सोनू सुबह खात")
    m_statuses = {w.text: w.status for w in mispronounced}
    assert m_statuses["सात"] == "practise"
    assert m_statuses["सोनू"] == "clear"

    # English sentence
    eng = align_words("I need a glass of water", "I want a cup of water")
    e_statuses = {w.text: w.status for w in eng}
    assert e_statuses["I"] == "clear" and e_statuses["water"] == "clear"
    assert e_statuses["need"] == "practise" and e_statuses["glass"] == "practise"


def test_pace_math(env):
    client = env.signup()

    # Step easy-starts-2-paced has pace_wpm [50, 80] and 8 words
    # 8 words in 2.0 s -> WPM = 8 / 2.0 * 60 = 240 (> 80) -> pace is slower
    env.fake.transcripts.append("मेरे पास बोलने के लिए पूरा समय है")
    fast = client.post("/me/trainings/attempts", data={"step_id": "easy-starts-2-paced", "check": "true"},
                       files=env.recording(seconds=2.0)).json()
    assert fast["wpm"] == 240 and fast["pace"] == "slower"

    # 8 words in 7.0 s -> WPM = 8 / 7.0 * 60 = 69 (50 <= 69 <= 80) -> pace is good
    env.fake.transcripts.append("मेरे पास बोलने के लिए पूरा समय है")
    good = client.post("/me/trainings/attempts", data={"step_id": "easy-starts-2-paced", "check": "true"},
                       files=env.recording(seconds=7.0)).json()
    assert good["wpm"] == 69 and good["pace"] == "good"

    # 8 words in 15.0 s -> WPM = 8 / 15.0 * 60 = 32 (< 50) -> pace is faster
    env.fake.transcripts.append("मेरे पास बोलने के लिए पूरा समय है")
    slow = client.post("/me/trainings/attempts", data={"step_id": "easy-starts-2-paced", "check": "true"},
                       files=env.recording(seconds=15.0)).json()
    assert slow["wpm"] == 32 and slow["pace"] == "faster"

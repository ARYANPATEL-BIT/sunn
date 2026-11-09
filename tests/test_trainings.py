"""Trainings (docs/TRAININGS_CONTRACT.md): each route answers the contract's shape, and the
content in content/trainings/ passes scripts/validate_trainings.py."""
import json
import os
import shutil

import pytest

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
    found = env.signup().get("/trainings/courses/easy-starts").json()
    assert set(found) == {"id", "category_id", "title", "summary", "what_you_practise", "level", "minutes",
                          "practice_lang", "percent", "lessons"}
    assert all(set(lesson) == {"id", "title", "minutes", "step_count", "completed"} for lesson in found["lessons"])
    assert [lesson["completed"] for lesson in found["lessons"]] == [True, False, False, False] and found["percent"] == 25
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
    found = env.signup().get("/me/trainings/progress").json()
    assert set(found) == {"courses", "resume", "lessons_done", "minutes_practised", "days_this_week"}
    assert all(set(c) == {"id", "percent"} for c in found["courses"])
    assert set(found["resume"]) == {"course_id", "lesson_id", "step_index"}


def test_save_progress(env):
    client = env.signup()
    found = client.post("/me/trainings/progress", json={"lesson_id": "easy-starts-2", "step_index": 6, "completed": True})
    assert found.json() == {"lesson_id": "easy-starts-2", "course_id": "easy-starts", "step_index": 6,
                            "completed": True, "course_percent": 50}
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


def test_attempts(env):
    client, keys = env.signup(), {"checked", "words", "similarity", "wpm", "pace", "message_key", "checks_left_today"}

    def attempt(**form):
        response = client.post("/me/trainings/attempts", data=form, files=env.recording())
        assert set(response.json()) == keys or response.status_code != 200, response.text
        return response.json()

    words = attempt(step_id="s-and-sh-1-echo", check="true")
    assert words["checked"] and words["wpm"] is None and {w["status"] for w in words["words"]} <= {"clear", "practise"}
    pace = attempt(step_id="easy-starts-1-together", check="true")
    assert pace["pace"] in ("slower", "good", "faster") and pace["words"] is None
    unchecked = attempt(step_id="easy-starts-1-vowels", item_id="aam", check="false")
    assert not unchecked["checked"] and unchecked["message_key"] == "practised"
    assert attempt(step_id="easy-starts-1-vowels", item_id="nowhere")["error"] == "not_found"
    assert attempt(step_id="easy-starts-1-welcome")["error"] == "invalid_input"  # an intro takes no recording
    assert not env.fake.sent("stt")  # the stub hears nothing


def test_tricky_sounds(env):
    found = env.signup().get("/me/trainings/tricky-sounds").json()
    assert found and all(set(s) == {"sound_id", "label", "why_key", "evidence", "practise_lesson_id"} for s in found)
    assert all(set(s["evidence"]) == {"speak", "practice", "self"} for s in found)


def test_alternatives(env):
    found = env.signup().post("/me/trainings/alternatives", json={"text": "शुक्रिया", "lang": "hi"}).json()
    assert set(found) == {"meaning_en", "alternatives"}
    assert all(set(a) == {"text", "latin", "meaning_en", "avoids", "source"} for a in found["alternatives"])


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

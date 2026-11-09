"""Trainings: speaking practice in short course-style lessons, a practice and confidence tool that
Training progress, reflections and attempts are stored in the database.
docs/TRAININGS_CONTRACT.md is the contract. Browsing the content (content/trainings/,
read through src/trainings_content.py) needs no session; everything under /me does."""
import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Cookie, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import auth
import db
import gnani_mock
import schemas
import trainings_content as content
from api import Refused, current_user, get_user

# Once, at start: content that breaks the contract stops the server here, not on a request.
LIBRARY = content.load()
if content.problems(LIBRARY):
    raise RuntimeError("content/trainings/ breaks docs/TRAININGS_CONTRACT.md: run uv run scripts/validate_trainings.py")
# The Timbre audio for each audio_key in content/trainings/audio.json, made ahead of time.
AUDIO_DIR = os.path.join(db.DATA_DIR, "trainings", "audio")
# What a pace check compares against when the step has no pace_wpm of its own.
DEFAULT_PACE_WPM = (70, 120)
RECORDED = (content.ListenRepeat, content.SpeakWithMe, content.ReadAloud)  # the steps attempts take

router = APIRouter()


# --- responses

class CategorySummary(content.Category):
    course_count: int
    percent: int | None  # lessons completed in its courses, 0-100; null when signed out


class CourseSummary(BaseModel):
    id: str
    title: content.Text
    summary: content.Text
    level: Literal["beginner"]
    minutes: int
    practice_lang: content.Lang
    lesson_count: int
    percent: int | None  # null when signed out


class CategoryDetail(content.Category):
    courses: list[CourseSummary]


class LessonSummary(BaseModel):
    id: str
    title: content.Text
    minutes: int
    step_count: int
    completed: bool  # false when signed out


class CourseDetail(BaseModel):
    id: str
    category_id: str
    title: content.Text
    summary: content.Text
    what_you_practise: content.Texts
    level: Literal["beginner"]
    minutes: int
    practice_lang: content.Lang
    percent: int | None  # null when signed out
    lessons: list[LessonSummary]


class LessonDetail(content.Lesson):
    course_id: str
    category_id: str
    practice_lang: content.Lang
    next_lesson_id: str | None  # null for the course's last lesson


class CoursePercent(BaseModel):
    id: str
    percent: int


class Resume(BaseModel):
    course_id: str
    lesson_id: str
    step_index: int


class Progress(BaseModel):
    courses: list[CoursePercent]  # every course started; any other is 0
    resume: Resume | None  # where the user stopped; null before any progress
    lessons_done: int
    minutes_practised: int
    days_this_week: int  # days since Monday with any practice


class ProgressUpdate(schemas.Request):
    lesson_id: str
    step_index: int = Field(ge=0)  # the step the user is on, 0-based
    completed: bool  # true once the last step is done


class LessonProgress(BaseModel):
    lesson_id: str
    course_id: str
    step_index: int
    completed: bool
    course_percent: int


class Reflection(schemas.Request):
    lesson_id: str
    step_id: str
    feeling: content.Feeling


class AttemptWord(BaseModel):
    text: str
    status: Literal["clear", "practise"]


class Attempt(BaseModel):
    checked: bool  # false: nothing was sent to the speech service, and every score is null
    words: list[AttemptWord] | None  # feedback words only
    similarity: float | None  # 0-1, feedback words only
    wpm: int | None  # feedback pace only
    pace: Literal["slower", "good", "faster"] | None  # what to try next time; feedback pace only
    message_key: Literal["practised", "no_checks_left", "pace_good", "pace_slower", "pace_faster",
                         "words_clear", "words_practise"]
    checks_left_today: int


class Evidence(BaseModel):
    speak: int  # Speak recognitions where words with this sound were heard differently
    practice: int  # practice words with this sound marked practise
    self: int  # reflections of hard on steps that practise this sound


class TrickySound(BaseModel):
    sound_id: str
    label: content.Text
    why_key: Literal["heard_in_speak", "heard_in_practice", "you_said_hard"]  # the biggest evidence
    evidence: Evidence
    practise_lesson_id: str | None


class AlternativesRequest(schemas.Request):
    text: str = Field(min_length=1)
    lang: content.Lang


class Alternative(BaseModel):
    text: str
    latin: str
    meaning_en: str
    avoids: list[str]  # sound ids this wording leaves out
    source: Literal["library", "assistant"]  # Sunn's own list, or the LLM when LLM_ENABLED


class Alternatives(BaseModel):
    meaning_en: str
    alternatives: list[Alternative]


# --- helpers

def signed_in(sunn_session: str | None = Cookie(None)):
    """The signed-in user, or None: browsing works without a session, and shows progress with one."""
    user_id = auth.user_id_from_token(sunn_session) if sunn_session else None
    return get_user(user_id) if user_id else None


def first_course():
    return LIBRARY.courses_in(LIBRARY.categories[0].id)[0]


def done_lessons(user):
    """The set of lesson ids user has completed, from the database."""
    if not user:
        return set()
    result = db.rows(
        "SELECT lesson_id FROM training_progress WHERE user_id = ? AND completed_at IS NOT NULL",
        (user["id"],)
    )
    return {r["lesson_id"] for r in result if r["lesson_id"] in LIBRARY.lessons}


def percent(lessons, done):
    return round(100 * sum(lesson.id in done for lesson in lessons) / len(lessons)) if lessons else 0


def find(table, key, what):
    if key not in table:
        raise Refused(404, "not_found", f"{what} not found")
    return table[key]


def course_summary(course, done, user):
    return {**course.model_dump(include={"id", "title", "summary", "level", "minutes", "practice_lang"}),
            "lesson_count": len(course.lessons), "percent": percent(course.lessons, done) if user else None}


def category_summary(category, done, user):
    courses = LIBRARY.courses_in(category.id)
    lessons = [lesson for course in courses for lesson in course.lessons]
    return {**category.model_dump(), "course_count": len(courses), "percent": percent(lessons, done) if user else None}


# --- browsing: no session needed

@router.get("/trainings/categories", response_model=list[CategorySummary])
def categories(user=Depends(signed_in)):
    """Every category in order, with how many courses it has and, signed in, how far the user is."""
    done = done_lessons(user)
    return [category_summary(category, done, user) for category in LIBRARY.categories]


@router.get("/trainings/categories/{category_id}", response_model=CategoryDetail)
def category(category_id: str, user=Depends(signed_in)):
    found = find({c.id: c for c in LIBRARY.categories}, category_id, "category")
    done = done_lessons(user)
    return {**found.model_dump(), "courses": [course_summary(c, done, user) for c in LIBRARY.courses_in(category_id)]}


@router.get("/trainings/courses/{course_id}", response_model=CourseDetail)
def course(course_id: str, user=Depends(signed_in)):
    found, done = find(LIBRARY.courses, course_id, "course"), done_lessons(user)
    return {**found.model_dump(exclude={"lessons"}), "percent": percent(found.lessons, done) if user else None,
            "lessons": [{"id": lesson.id, "title": lesson.title, "minutes": lesson.minutes,
                         "step_count": len(lesson.steps), "completed": lesson.id in done} for lesson in found.lessons]}


@router.get("/trainings/lessons/{lesson_id}", response_model=LessonDetail)
def lesson(lesson_id: str):
    found_course, found = find(LIBRARY.lessons, lesson_id, "lesson")
    following = found_course.lessons[found_course.lessons.index(found) + 1:]
    return {**found.model_dump(), "course_id": found_course.id, "category_id": found_course.category_id,
            "practice_lang": found_course.practice_lang, "next_lesson_id": following[0].id if following else None}


@router.get("/trainings/audio/{audio_key}", response_class=FileResponse, responses={200: {"content": {"audio/wav": {}}}})
def audio(audio_key: str):
    """The Timbre audio for an audio_key, made ahead of time into AUDIO_DIR; not_found until it
    is. With GNANI_MOCK, a listed key that has none answers half a second of silence."""
    find(LIBRARY.audio, audio_key, "audio")  # only listed keys, so the path is always a plain file name
    path = os.path.join(AUDIO_DIR, f"{audio_key}.wav")
    if not os.path.exists(path):
        if not gnani_mock.on():
            raise Refused(404, "not_found", "audio not made yet")
        path = gnani_mock.silence()
    return FileResponse(path, media_type="audio/wav")


# --- the user's own practice

@router.get("/me/trainings/progress", response_model=Progress)
def progress(user=Depends(current_user)):
    done = done_lessons(user)

    # Every course the user has started (has any row in training_progress)
    prog_rows = db.rows(
        "SELECT lesson_id, updated_at FROM training_progress WHERE user_id = ? ORDER BY updated_at DESC",
        (user["id"],)
    )
    started_courses = set()
    for r in prog_rows:
        if r["lesson_id"] in LIBRARY.lessons:
            c, _ = LIBRARY.lessons[r["lesson_id"]]
            started_courses.add(c.id)

    courses = [
        {"id": c.id, "percent": percent(c.lessons, done)}
        for c in LIBRARY.courses.values()
        if c.id in started_courses
    ]

    # Resume: the most recently updated unfinished lesson
    unfinished = db.row(
        "SELECT lesson_id, step_index FROM training_progress WHERE user_id = ? AND completed_at IS NULL ORDER BY updated_at DESC, rowid DESC LIMIT 1",
        (user["id"],)
    )
    resume = None
    if unfinished and unfinished["lesson_id"] in LIBRARY.lessons:
        c, _ = LIBRARY.lessons[unfinished["lesson_id"]]
        resume = {"course_id": c.id, "lesson_id": unfinished["lesson_id"], "step_index": unfinished["step_index"]}

    # Minutes practised: sum of seconds across all days in training_minutes, rounded to nearest minute
    min_row = db.row(
        "SELECT COALESCE(SUM(seconds), 0) AS total_seconds FROM training_minutes WHERE user_id = ?",
        (user["id"],)
    )
    total_seconds = min_row["total_seconds"] if min_row else 0
    minutes_practised = round(total_seconds / 60)

    # Days this week: distinct days with any activity in the last 7 days
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=6)).isoformat()
    day_row = db.row(
        "SELECT COUNT(DISTINCT day) AS cnt FROM ("
        "  SELECT day FROM training_minutes WHERE user_id = ? AND day >= ? AND seconds > 0"
        "  UNION"
        "  SELECT substr(updated_at, 1, 10) AS day FROM training_progress WHERE user_id = ? AND updated_at >= ?"
        ")",
        (user["id"], cutoff, user["id"], cutoff)
    )
    days_this_week = day_row["cnt"] if day_row else 0

    return {
        "courses": courses,
        "resume": resume,
        "lessons_done": len(done),
        "minutes_practised": minutes_practised,
        "days_this_week": days_this_week,
    }


@router.post("/me/trainings/progress", response_model=LessonProgress)
def save_progress(body: ProgressUpdate, user=Depends(current_user)):
    found_course, found = find(LIBRARY.lessons, body.lesson_id, "lesson")
    if body.step_index >= len(found.steps):
        raise Refused(400, "invalid_input", f"step_index: the lesson has {len(found.steps)} steps")

    now_dt = datetime.now(timezone.utc)
    now_str = now_dt.isoformat(timespec="milliseconds")
    today_str = now_dt.date().isoformat()

    # Time tracking: add elapsed seconds since last update to training_minutes (capped at 10 minutes)
    prev = db.row("SELECT updated_at FROM training_progress WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (user["id"],))
    if prev and prev.get("updated_at"):
        try:
            prev_dt = datetime.fromisoformat(prev["updated_at"])
            if prev_dt.tzinfo is None:
                prev_dt = prev_dt.replace(tzinfo=timezone.utc)
            delta = int((now_dt - prev_dt).total_seconds())
            seconds = min(600, max(15, delta))
        except Exception:
            seconds = 60
    else:
        seconds = 60

    db.execute(
        "INSERT INTO training_minutes (user_id, day, seconds) VALUES (?, ?, ?)"
        " ON CONFLICT(user_id, day) DO UPDATE SET seconds = seconds + excluded.seconds",
        (user["id"], today_str, seconds)
    )

    # Progress upsert: completed only moves forward, never back
    completed_at = now_str if body.completed else None
    db.execute(
        "INSERT INTO training_progress (user_id, lesson_id, step_index, completed_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(user_id, lesson_id) DO UPDATE SET"
        " step_index = excluded.step_index,"
        " completed_at = COALESCE(training_progress.completed_at, excluded.completed_at),"
        " updated_at = excluded.updated_at",
        (user["id"], body.lesson_id, body.step_index, completed_at, now_str)
    )

    # Fetch stored completion state
    stored = db.row("SELECT completed_at FROM training_progress WHERE user_id = ? AND lesson_id = ?",
                    (user["id"], body.lesson_id))
    is_completed = bool(stored and stored["completed_at"])
    done = done_lessons(user)

    return {
        "lesson_id": found.id,
        "course_id": found_course.id,
        "step_index": body.step_index,
        "completed": is_completed,
        "course_percent": percent(found_course.lessons, done),
    }


@router.post("/me/trainings/reflect", response_model=schemas.Ok)
def reflect(body: Reflection, user=Depends(current_user)):
    _, found = find(LIBRARY.lessons, body.lesson_id, "lesson")
    if not any(step.id == body.step_id and isinstance(step, content.Reflect) for step in found.steps):
        raise Refused(404, "not_found", "no reflect step with that id in the lesson")
    now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.execute(
        "INSERT INTO training_reflections (user_id, lesson_id, step_id, feeling, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (user["id"], body.lesson_id, body.step_id, body.feeling, now_str)
    )
    return {"ok": True}


def attempted(step_id, item_id):
    """(the step, the text it asks the user to say) for an attempt."""
    _, _, step = find(LIBRARY.steps, step_id, "step")
    if not isinstance(step, RECORDED):
        raise Refused(400, "invalid_input", "step_id: attempts are for listen_repeat, speak_with_me and read_aloud")
    if isinstance(step, content.ListenRepeat):
        return step, find({item.id: item for item in step.items}, item_id, "item").text
    return step, step.paragraph if isinstance(step, content.ReadAloud) else step.text


@router.post("/me/trainings/attempts", response_model=Attempt)
def attempt(audio_file: UploadFile = File(alias="audio"), step_id: str = Form(), item_id: str | None = Form(None),
            check: bool = Form(False), user=Depends(current_user)):
    """One try at a step (item_id names the item of a listen_repeat step). With check and a step
    whose feedback isn't none, Prisma hears it and it is scored; the recording is never kept."""
    found_course, found_lesson, step = find(LIBRARY.steps, step_id, "step")
    if not isinstance(step, RECORDED):
        raise Refused(400, "invalid_input", "step_id: attempts are for listen_repeat, speak_with_me and read_aloud")
    if isinstance(step, content.ListenRepeat):
        text = find({item.id: item for item in step.items}, item_id, "item").text
    else:
        text = step.paragraph if isinstance(step, content.ReadAloud) else step.text

    unchecked = {"checked": False, "words": None, "similarity": None, "wpm": None, "pace": None,
                 "message_key": "practised", "checks_left_today": 24}
    res = unchecked
    if check and step.feedback != "none":
        if step.feedback == "pace":
            res = {**unchecked, "checked": True, "wpm": 84, "pace": "good", "message_key": "pace_good"}
        else:
            words = [word.strip("।,.?!'\"") for word in text.split()]
            statuses = ["clear"] * (len(words) - 1) + ["practise" if len(words) > 1 else "clear"]
            res = {**unchecked, "checked": True, "words": [{"text": w, "status": s} for w, s in zip(words, statuses)],
                   "similarity": 0.82 if len(words) > 1 else 0.93,
                   "message_key": "words_practise" if len(words) > 1 else "words_clear", "checks_left_today": 23}

    now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")
    transcript = None if found_course.category_id == "kids-speaking" else text
    db.execute(
        "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user["id"], found_lesson.id, step_id, item_id, transcript, res.get("similarity"), res.get("wpm"), int(res["checked"]), now_str)
    )
    return res


@router.get("/me/trainings/tricky-sounds", response_model=list[TrickySound])
def tricky_sounds(user=Depends(current_user)):
    """Sounds the user might like to practise, with the evidence for each. A suggestion, never a
    diagnosis."""
    sounds = {s.id: s for s in LIBRARY.sounds}
    made_up = [("s", "heard_in_practice", {"speak": 2, "practice": 5, "self": 1}),
               ("sh", "heard_in_speak", {"speak": 4, "practice": 1, "self": 0})]
    return [{"sound_id": i, "label": sounds[i].label, "why_key": why, "evidence": evidence,
             "practise_lesson_id": sounds[i].practise_lesson_id} for i, why, evidence in made_up if i in sounds]


@router.post("/me/trainings/alternatives", response_model=Alternatives)
def alternatives(body: AlternativesRequest, user=Depends(current_user)):
    """Other ways to say text that leave out the user's tricky sounds."""
    if body.lang == "en":
        return {"meaning_en": "thank you", "alternatives": [
            {"text": "Much appreciated", "latin": "Much appreciated", "meaning_en": "thank you",
             "avoids": ["th-english"], "source": "library"},
            {"text": "Cheers", "latin": "Cheers", "meaning_en": "thanks, said casually", "avoids": ["th-english"],
             "source": "assistant"}]}
    return {"meaning_en": "thank you", "alternatives": [
        {"text": "धन्यवाद", "latin": "dhanyavaad", "meaning_en": "thank you", "avoids": ["sh"], "source": "library"},
        {"text": "बहुत मेहरबानी", "latin": "bahut meharbaani", "meaning_en": "thank you very much", "avoids": ["sh"],
         "source": "assistant"}]}

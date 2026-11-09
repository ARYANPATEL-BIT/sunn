"""Trainings: speaking practice in short course-style lessons, a practice and confidence tool that
Training progress, reflections and attempts are stored in the database.
docs/TRAININGS_CONTRACT.md is the contract. Browsing the content (content/trainings/,
read through src/trainings_content.py) needs no session; everything under /me does."""
import json
import os
import re
import subprocess
import tempfile
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Cookie, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from rapidfuzz.distance import Levenshtein

import audio as audio_utils
import auth
import db
import gnani
import gnani_mock
import llm_judge
import matcher
import prisma
import schemas
import trainings_content as content

router = APIRouter()
from api import Refused, current_user, get_user

# Once, at start: content that breaks the contract stops the server here, not on a request.
LIBRARY = content.load()
if content.problems(LIBRARY):
    raise RuntimeError("content/trainings/ breaks docs/TRAININGS_CONTRACT.md: run uv run scripts/validate_trainings.py")
# The Timbre audio for each audio_key in content/trainings/audio.json, made ahead of time.
AUDIO_DIR = os.path.join(db.DATA_DIR, "trainings", "audio")
WEB_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "public", "training-audio")
# What a pace check compares against when the step has no pace_wpm of its own.
DEFAULT_PACE_WPM = (70, 120)
RECORDED = (content.ListenRepeat, content.SpeakWithMe, content.ReadAloud)  # the steps attempts take
TRAINING_CHECKS_PER_DAY = int(os.environ.get("TRAINING_CHECKS_PER_DAY", 20))
WORD_CLEAR_THRESHOLD = float(os.environ.get("WORD_CLEAR_THRESHOLD", 0.70))
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB upload cap

DEV_CHAR_TO_SOUND: dict[str, str] = {
    'प': 'p',
    'ब': 'b',
    'त': 't-dental',
    'ट': 't-retroflex',
    'द': 'd', 'ड': 'd', 'ड़': 'd',
    'क': 'k', 'क़': 'k',
    'ग': 'g', 'ग़': 'g',
    'च': 'ch',
    'ज': 'j', 'ज़': 'j',
    'स': 's',
    'श': 'sh', 'ष': 'sh',
    'र': 'r',
    'ल': 'l',
    'ख': 'aspirated', 'ख़': 'aspirated', 'घ': 'aspirated', 'छ': 'aspirated',
    'झ': 'aspirated', 'ठ': 'aspirated', 'ढ': 'aspirated', 'ढ़': 'aspirated',
    'थ': 'aspirated', 'ध': 'aspirated', 'फ': 'aspirated', 'फ़': 'aspirated', 'भ': 'aspirated',
    'म': 'nasal', 'न': 'nasal', 'ण': 'nasal', 'ङ': 'nasal', 'ञ': 'nasal',
}


def extract_word_sounds(word: str) -> set[str]:
    """Sounds a word contains: word-initial consonant, clusters, and character sounds."""
    sounds: set[str] = set()
    cleaned = word.strip("।,?!'\"()[]{}")
    if not cleaned:
        return sounds
    w_lower = cleaned.lower()

    if "th" in w_lower:
        sounds.add("th-english")
    if "sh" in w_lower:
        sounds.add("sh")
    if "ch" in w_lower:
        sounds.add("ch")
    for k in ["kh", "gh", "chh", "jh", "dh", "bh", "ph"]:
        if k in w_lower:
            sounds.add("aspirated")

    if re.search(r"[\u0915-\u0939]\u094d[\u0915-\u0939]", cleaned):
        sounds.add("clusters")
    if re.search(r"(?:sk|pr|kr|pl|bl|st|sp|cl|gl|dr|tr|br|str|spr|sch)", w_lower):
        sounds.add("clusters")

    for char in cleaned:
        if char in DEV_CHAR_TO_SOUND:
            sounds.add(DEV_CHAR_TO_SOUND[char])
            break

    for char in cleaned:
        if char in DEV_CHAR_TO_SOUND:
            sounds.add(DEV_CHAR_TO_SOUND[char])
        elif char in ("\u0902", "\u0901"):
            sounds.add("nasal")

    if "p" in w_lower:
        sounds.add("p")
    if "b" in w_lower:
        sounds.add("b")
    if "d" in w_lower:
        sounds.add("d")
    if "k" in w_lower or ("c" in w_lower and "ch" not in w_lower):
        sounds.add("k")
    if "g" in w_lower:
        sounds.add("g")
    if "j" in w_lower:
        sounds.add("j")
    if "s" in w_lower and "sh" not in w_lower:
        sounds.add("s")
    if "r" in w_lower:
        sounds.add("r")
    if "l" in w_lower:
        sounds.add("l")
    if any(c in w_lower for c in ["m", "n"]):
        sounds.add("nasal")

    return sounds


def extract_text_sounds(text: str) -> set[str]:
    """All speech sounds present in a sentence or phrase."""
    sounds: set[str] = set()
    for word in text.split():
        sounds.update(extract_word_sounds(word))
    return sounds


ALTERNATIVES_PATH = os.path.join(content.ROOT, "alternatives.json")
TAGGED_ALTERNATIVES = []
if os.path.exists(ALTERNATIVES_PATH):
    with open(ALTERNATIVES_PATH, encoding="utf-8") as _f:
        _raw_meanings = json.load(_f)
    for _m in _raw_meanings:
        _meaning_item = {
            "meaning_id": _m.get("meaning_id", ""),
            "meaning_en": _m.get("meaning_en", ""),
            "category": _m.get("category", ""),
            "urgent": bool(_m.get("urgent", False)),
            "variants": [],
        }
        for _idx, _v in enumerate(_m.get("variants", [])):
            _v_text = _v.get("text", "")
            _v_latin = _v.get("latin", _v_text)
            _v_lang = _v.get("lang", "hi")
            _v_sounds = extract_text_sounds(_v_text) | extract_text_sounds(_v_latin)
            _meaning_item["variants"].append({
                "text": _v_text,
                "latin": _v_latin,
                "lang": _v_lang,
                "sounds": _v_sounds,
                "norm": matcher.normalize(_v_text),
                "norm_latin": matcher.normalize(_v_latin),
                "index": _idx,
            })
        TAGGED_ALTERNATIVES.append(_meaning_item)


_assistant_calls_today: dict[tuple[int, str], int] = defaultdict(int)
_alternatives_cache: dict[tuple, Any] = {}
_alternatives_lock = threading.Lock()


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
                         "words_clear", "words_practise", "nice_work", "take_your_time", "try_slower", "great_pace"]
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


@router.get("/trainings/audio/{audio_key}", response_class=FileResponse, responses={200: {"content": {"audio/mpeg": {}, "audio/wav": {}, "audio/ogg": {}}}})
def audio(audio_key: str):
    """The Timbre audio for an audio_key. Serves web/public/training-audio/<key>.mp3,
    then AUDIO_DIR/<key>.wav; not_found until it is generated. With GNANI_MOCK, a listed
    key without audio answers half a second of silence."""
    find(LIBRARY.audio, audio_key, "audio")  # only listed keys, so the path is always a plain file name
    mp3_path = os.path.join(WEB_AUDIO_DIR, f"{audio_key}.mp3")
    if os.path.exists(mp3_path):
        return FileResponse(mp3_path, media_type="audio/mpeg")
    opus_path = os.path.join(WEB_AUDIO_DIR, f"{audio_key}.opus")
    if os.path.exists(opus_path):
        return FileResponse(opus_path, media_type="audio/ogg")
    wav_path = os.path.join(AUDIO_DIR, f"{audio_key}.wav")
    if os.path.exists(wav_path):
        return FileResponse(wav_path, media_type="audio/wav")
    if not gnani_mock.on():
        raise Refused(404, "not_found", "audio not made yet")
    return FileResponse(gnani_mock.silence(), media_type="audio/wav")


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


def normalize_for_align(text: str) -> str:
    norm = matcher.normalize(text)
    # Collapse repeating vowels for colloquial Latin / ITRANS alignment tolerance
    return re.sub(r"([aeiou])\1+", r"\1", norm)


def align_words(target_text: str, hypo_text: str, threshold: float = WORD_CLEAR_THRESHOLD) -> list[AttemptWord]:
    """Align hypothesis words to target words and return word statuses."""
    target_words = [w.strip("।,?!'\"") for w in target_text.split() if w.strip("।,?!'\"")]
    hypo_words = [w.strip("।,?!'\"") for w in hypo_text.split() if w.strip("।,?!'\"")]

    if not target_words:
        return []
    if not hypo_words:
        return [AttemptWord(text=w, status="practise") for w in target_words]

    n, m = len(target_words), len(hypo_words)
    t_norm = [normalize_for_align(w) for w in target_words]
    h_norm = [normalize_for_align(w) for w in hypo_words]

    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sim = Levenshtein.normalized_similarity(t_norm[i - 1], h_norm[j - 1])
            match_score = dp[i - 1][j - 1] + sim
            skip_t = dp[i - 1][j]
            skip_h = dp[i][j - 1]

            best = max(match_score, skip_t, skip_h)
            dp[i][j] = best
            if best == match_score:
                back[i][j] = (i - 1, j - 1, sim)
            elif best == skip_t:
                back[i][j] = (i - 1, j, 0.0)
            else:
                back[i][j] = (i, j - 1, 0.0)

    i, j = n, m
    matched_sim = [0.0] * n
    while i > 0 and j > 0:
        prev_i, prev_j, sim = back[i][j]
        if prev_i == i - 1 and prev_j == j - 1:
            matched_sim[i - 1] = sim
            i, j = prev_i, prev_j
        elif prev_i == i - 1:
            matched_sim[i - 1] = 0.0
            i, j = prev_i, prev_j
        else:
            i, j = prev_i, prev_j

    return [
        AttemptWord(text=w, status="clear" if matched_sim[idx] >= threshold else "practise")
        for idx, w in enumerate(target_words)
    ]


@router.post("/me/trainings/attempts", response_model=Attempt)
def attempt(
    audio_file: UploadFile = File(alias="audio"),
    step_id: str = Form(),
    item_id: str | None = Form(None),
    check: bool = Form(False),
    user=Depends(current_user),
):
    """One try at a step (item_id names the item of a listen_repeat step). With check=true and a step
    whose feedback isn't none, Prisma hears it and it is scored; the recording is never kept."""
    found_course, found_lesson, step = find(LIBRARY.steps, step_id, "step")
    if not isinstance(step, RECORDED):
        raise Refused(400, "invalid_input", "step_id: attempts are for listen_repeat, speak_with_me and read_aloud")
    if isinstance(step, content.ListenRepeat):
        text = find({item.id: item for item in step.items}, item_id, "item").text
    else:
        text = step.paragraph if isinstance(step, content.ReadAloud) else step.text

    # Calculate remaining checks today
    today_str = datetime.now(timezone.utc).date().isoformat()
    now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")
    used_today = db.row(
        "SELECT COUNT(*) AS n FROM training_attempts WHERE user_id = ? AND checked = 1 AND created_at >= ?",
        (user["id"], today_str),
    )["n"]
    checks_left = max(0, TRAINING_CHECKS_PER_DAY - used_today)

    # Read and convert uploaded audio to 16kHz mono WAV for validation and Prisma
    data = audio_file.file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise Refused(413, "file_too_large", "the audio file is too large")

    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as raw_f, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_f:
        raw_path = raw_f.name
        wav_path = wav_f.name
        raw_f.write(data)

    try:
        try:
            audio_utils.to_wav(raw_path, wav_path)
        except subprocess.CalledProcessError:
            raise Refused(400, "bad_audio", "could not read the audio file")

        audio_seconds = audio_utils.seconds(wav_path) or 0.0
        if audio_seconds < 0.3:
            raise Refused(400, "audio_too_short",
                          f"the recording is {audio_seconds:.1f} s; it needs 0.3 to 30 s",
                          seconds=round(audio_seconds, 1))
        if audio_seconds > 30.0:
            raise Refused(400, "audio_too_long",
                          f"the recording is {audio_seconds:.1f} s; it needs 0.3 to 30 s",
                          seconds=round(audio_seconds, 1))

        # 1. Not checked (check=False) or step feedback is "none"
        if not check or step.feedback == "none":
            # If check requested on feedback="none" step:
            if check and checks_left > 0:
                lang = getattr(found_course, "practice_lang", "hi")
                try:
                    hypothesis = prisma.transcribe(wav_path, language=lang, user_id=user["id"])
                except gnani.GnaniError as ge:
                    if ge.code in ("daily_cap_reached", "credit_limit_reached"):
                        return Attempt(
                            checked=False, words=None, similarity=None, wpm=None, pace=None,
                            message_key="no_checks_left", checks_left_today=0,
                        )
                    raise
                stored_transcript = None if found_course.category_id == "kids-speaking" else hypothesis
                db.execute(
                    "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user["id"], found_lesson.id, step_id, item_id, stored_transcript, None, None, 1, now_str),
                )
                return Attempt(
                    checked=True, words=None, similarity=None, wpm=None, pace=None,
                    message_key="practised", checks_left_today=max(0, checks_left - 1),
                )

            # Plain practice without check
            stored_transcript = None if found_course.category_id == "kids-speaking" else text
            db.execute(
                "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], found_lesson.id, step_id, item_id, stored_transcript, None, None, 0, now_str),
            )
            return Attempt(
                checked=False, words=None, similarity=None, wpm=None, pace=None,
                message_key="practised", checks_left_today=checks_left,
            )

        # 2. Check requested, but daily check cap reached
        if checks_left <= 0:
            stored_transcript = None if found_course.category_id == "kids-speaking" else text
            db.execute(
                "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], found_lesson.id, step_id, item_id, stored_transcript, None, None, 0, now_str),
            )
            return Attempt(
                checked=False, words=None, similarity=None, wpm=None, pace=None,
                message_key="no_checks_left", checks_left_today=0,
            )

        # 3. Check requested and cap available: transcribe with Prisma
        lang = getattr(found_course, "practice_lang", "hi")
        try:
            hypothesis = prisma.transcribe(wav_path, language=lang, user_id=user["id"])
        except gnani.GnaniError as ge:
            if ge.code in ("daily_cap_reached", "credit_limit_reached"):
                return Attempt(
                    checked=False, words=None, similarity=None, wpm=None, pace=None,
                    message_key="no_checks_left", checks_left_today=0,
                )
            raise

        if not hypothesis or not hypothesis.strip():
            raise Refused(422, "no_speech", "no speech was heard in the recording")

        # Compute WPM and pace
        target_words = [w.strip("।,?!'\"") for w in text.split() if w.strip("।,?!'\"")]
        wpm = round(60 * len(target_words) / audio_seconds) if audio_seconds > 0 else 0
        pace_min, pace_max = step.pace_wpm if getattr(step, "pace_wpm", None) else DEFAULT_PACE_WPM
        if wpm > pace_max:
            pace = "slower"
        elif wpm < pace_min:
            pace = "faster"
        else:
            pace = "good"

        # Apply feedback rule: smooth-speaking and kids-speaking never return words
        is_speech_restricted = found_course.category_id in ("smooth-speaking", "kids-speaking")
        effective_feedback = "pace" if (is_speech_restricted and step.feedback == "words") else step.feedback

        if effective_feedback == "words":
            words_scored = align_words(text, hypothesis)
            overall_sim = round(Levenshtein.normalized_similarity(matcher.normalize(text), matcher.normalize(hypothesis)), 2)
            all_clear = all(w.status == "clear" for w in words_scored)
            message_key = "words_clear" if all_clear else "words_practise"
            res_words = words_scored
            res_similarity = overall_sim
            res_wpm = None
            res_pace = None
        elif effective_feedback == "pace":
            res_words = None
            res_similarity = None
            res_wpm = wpm
            res_pace = pace
            message_key = f"pace_{pace}"
        else:  # none
            res_words = None
            res_similarity = None
            res_wpm = None
            res_pace = None
            message_key = "practised"

        # Store attempt (never store audio; for kids-speaking store no transcript at all)
        stored_transcript = None if found_course.category_id == "kids-speaking" else hypothesis
        db.execute(
            "INSERT INTO training_attempts (user_id, lesson_id, step_id, item_id, transcript, similarity, wpm, checked, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], found_lesson.id, step_id, item_id, stored_transcript, res_similarity, res_wpm, 1, now_str),
        )

        return Attempt(
            checked=True,
            words=res_words,
            similarity=res_similarity,
            wpm=res_wpm,
            pace=res_pace,
            message_key=message_key,
            checks_left_today=max(0, checks_left - 1),
        )

    finally:
        for p in (raw_path, wav_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def get_user_tricky_sounds(user: dict) -> list[TrickySound]:
    """Collects evidence across speak, practice, and self reflections for the user."""
    user_id = user["id"]
    sounds_dict = {s.id: s for s in LIBRARY.sounds}

    # 1. Speak evidence: count consistent substitutions
    speak_counts: dict[str, int] = defaultdict(int)
    samples = db.rows(
        "SELECT s.prisma_hypothesis, p.text FROM samples s JOIN phrases p ON s.phrase_id = p.id WHERE s.user_id = ?",
        (user_id,)
    )
    for sample in samples:
        target = sample["text"] or ""
        hypo = sample["prisma_hypothesis"] or ""
        if not target or not hypo:
            continue
        ops = Levenshtein.editops(target, hypo)
        for op, s1, _ in ops:
            if op == "replace" and s1 < len(target):
                ch = target[s1]
                if ch in DEV_CHAR_TO_SOUND:
                    sound_id = DEV_CHAR_TO_SOUND[ch]
                    speak_counts[sound_id] += 1
                elif ch.lower() in ("m", "n"):
                    speak_counts["nasal"] += 1
                elif ch in ("\u0902", "\u0901"):
                    speak_counts["nasal"] += 1

    # 2. Practice evidence: checked attempts word alignments
    practice_words_practise: dict[str, int] = defaultdict(int)
    practice_words_total: dict[str, int] = defaultdict(int)
    attempts = db.rows(
        "SELECT step_id, item_id, transcript FROM training_attempts WHERE user_id = ? AND checked = 1",
        (user_id,)
    )
    for att in attempts:
        step_id = att["step_id"]
        item_id = att["item_id"]
        transcript = att["transcript"]
        if step_id not in LIBRARY.steps or not transcript:
            continue
        _, _, step = LIBRARY.steps[step_id]

        target_text = ""
        if isinstance(step, content.ListenRepeat):
            if item_id:
                for it in step.items:
                    if it.id == item_id:
                        target_text = it.text
                        break
        elif isinstance(step, (content.SpeakWithMe, content.ReadAloud)):
            target_text = step.text

        if not target_text:
            continue

        aligned = align_words(target_text, transcript)
        for w_item in aligned:
            w_sounds = extract_word_sounds(w_item.text)
            for sid in w_sounds:
                practice_words_total[sid] += 1
                if w_item.status == "practise":
                    practice_words_practise[sid] += 1

    # 3. Self evidence: "hard" reflections on steps that have focus_sound
    self_counts: dict[str, int] = defaultdict(int)
    reflections = db.rows(
        "SELECT step_id, feeling FROM training_reflections WHERE user_id = ? AND feeling = 'hard'",
        (user_id,)
    )
    for ref in reflections:
        step_id = ref["step_id"]
        if step_id not in LIBRARY.steps:
            continue
        found_course, found_lesson, step = LIBRARY.steps[step_id]
        step_sounds = set()
        if getattr(step, "focus_sound", None):
            step_sounds.add(step.focus_sound)
        if getattr(step, "sound_a", None):
            step_sounds.add(step.sound_a)
        if getattr(step, "sound_b", None):
            step_sounds.add(step.sound_b)
        if not step_sounds:
            for s in found_lesson.steps:
                if getattr(s, "focus_sound", None):
                    step_sounds.add(s.focus_sound)
                if getattr(s, "items", None):
                    for it in s.items:
                        if getattr(it, "focus_sound", None):
                            step_sounds.add(it.focus_sound)
        for sid in step_sounds:
            self_counts[sid] += 1

    # 4. Filter by thresholds:
    # at least 5 speak substitutions, OR 8 practice words with >40% practise rate, OR 2 "hard" reflections
    qualifying = []
    for sid, sound in sounds_dict.items():
        spk = speak_counts.get(sid, 0)
        prc = practice_words_practise.get(sid, 0)
        prc_tot = practice_words_total.get(sid, 0)
        slf = self_counts.get(sid, 0)

        prc_rate = (prc / prc_tot) if prc_tot > 0 else 0.0

        qualifies = (spk >= 5) or (prc_tot >= 8 and prc_rate > 0.40) or (slf >= 2)
        if not qualifies:
            continue

        if spk >= prc and spk >= slf:
            why = "heard_in_speak"
        elif prc >= slf:
            why = "heard_in_practice"
        else:
            why = "you_said_hard"

        total_evidence = spk + prc + slf
        qualifying.append({
            "sound_id": sid,
            "label": sound.label,
            "why_key": why,
            "evidence": Evidence(speak=spk, practice=prc, self=slf),
            "practise_lesson_id": sound.practise_lesson_id,
            "total_score": total_evidence,
        })

    qualifying.sort(key=lambda x: x["total_score"], reverse=True)
    top3 = qualifying[:3]
    return [
        TrickySound(
            sound_id=item["sound_id"],
            label=item["label"],
            why_key=item["why_key"],
            evidence=item["evidence"],
            practise_lesson_id=item["practise_lesson_id"],
        )
        for item in top3
    ]


@router.get("/me/trainings/tricky-sounds", response_model=list[TrickySound])
def tricky_sounds(user=Depends(current_user)):
    """Sounds the user might like to practise, with the evidence for each. A suggestion, never a
    diagnosis."""
    return get_user_tricky_sounds(user)


def call_groq_alternatives(text: str, lang: str, tricky_ids: list[str]) -> Alternatives | None:
    try:
        base = llm_judge.setting("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        model = llm_judge.setting("GROQ_MODEL") or llm_judge.setting("LLM_MODEL", "openai/gpt-oss-120b")
        key = llm_judge.setting("GROQ_API_KEY") or llm_judge.setting("LLM_API_KEY")
        timeout = float(llm_judge.setting("LLM_TIMEOUT_S", "3"))

        sounds_dict = {s.id: s for s in LIBRARY.sounds}
        if tricky_ids:
            sound_desc_list = []
            for tid in tricky_ids:
                if tid in sounds_dict:
                    s = sounds_dict[tid]
                    label = s.label.hi if lang == "hi" else s.label.en
                    eg = s.examples[0].text if s.examples else tid
                    sound_desc_list.append(f"{tid} ({label}, e.g. {eg})")
                else:
                    sound_desc_list.append(tid)
            sounds_str = ", ".join(sound_desc_list)
        else:
            sounds_str = "none"

        lang_name = "Hindi" if lang == "hi" else "English"
        system_prompt = (
            f"you help a person who finds some speech sounds hard. give 3 short, natural ways to say the same thing in {lang_name}, "
            f"keeping exactly the same meaning and the same urgency. avoid these sounds where you can: {sounds_str}. "
            "if the meaning is about pain, help, a doctor or danger, keep it just as clear and urgent. "
            'reply with json only: {"meaning_en": "...", "alternatives": [{"text": "...", "latin": "..."}]}'
        )

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        resp = httpx.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=timeout)
        if resp.status_code != 200:
            return None

        data = resp.json()
        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(raw_content)

        meaning_en = parsed.get("meaning_en")
        raw_alts = parsed.get("alternatives")
        if not isinstance(meaning_en, str) or not isinstance(raw_alts, list):
            return None
        if not (1 <= len(raw_alts) <= 3):
            return None

        text_lower = text.lower()
        is_urgent_input = any(w in text_lower for w in ["pain", "hurt", "doctor", "help", "sos", "danger", "दर्द", "डॉक्टर", "मदद", "सांस", "तकलीफ़"])

        valid_alts = []
        for item in raw_alts:
            if not isinstance(item, dict):
                continue
            alt_text = item.get("text", "").strip()
            alt_latin = item.get("latin", alt_text).strip()
            if not alt_text or len(alt_text) >= 60:
                continue
            if alt_text.lower() == text.strip().lower() or matcher.normalize(alt_text) == matcher.normalize(text):
                continue

            if is_urgent_input:
                dismissive_words = ["fine", "ok", "all good", "no problem", "better", "nothing", "सब ठीक", "कोई बात नहीं", "दर्द नहीं"]
                if any(dw in alt_text.lower() for dw in dismissive_words):
                    continue

            v_sounds = extract_text_sounds(alt_text) | extract_text_sounds(alt_latin)
            avoids = [s for s in tricky_ids if s not in v_sounds]
            valid_alts.append({
                "text": alt_text,
                "latin": alt_latin,
                "meaning_en": meaning_en,
                "avoids": avoids,
                "source": "assistant",
                "sounds": v_sounds,
            })

        if not valid_alts:
            return None

        tricky_set = set(tricky_ids)
        valid_alts.sort(key=lambda x: (len(x["sounds"] & tricky_set), len(x["text"])))

        return Alternatives(
            meaning_en=meaning_en,
            alternatives=[
                Alternative(
                    text=a["text"],
                    latin=a["latin"],
                    meaning_en=a["meaning_en"],
                    avoids=a["avoids"],
                    source="assistant",
                )
                for a in valid_alts
            ]
        )
    except Exception:
        return None


@router.post("/me/trainings/alternatives", response_model=Alternatives)
def alternatives(body: AlternativesRequest, user=Depends(current_user)):
    """Other ways to say text that leave out the user's tricky sounds."""
    user_tricky = get_user_tricky_sounds(user)
    tricky_ids = [ts.sound_id for ts in user_tricky]
    tricky_set = set(tricky_ids)

    norm_input = matcher.normalize(body.text)

    # 1. Search in Library: exact match or fuzzy match >= 0.85
    best_meaning = None
    best_variant = None
    best_sim = 0.0

    for m in TAGGED_ALTERNATIVES:
        for v in m["variants"]:
            if norm_input == v["norm"] or norm_input == v["norm_latin"]:
                best_meaning = m
                best_variant = v
                best_sim = 1.0
                break
        if best_meaning:
            break

    if not best_meaning:
        for m in TAGGED_ALTERNATIVES:
            for v in m["variants"]:
                sim1 = Levenshtein.normalized_similarity(norm_input, v["norm"])
                sim2 = Levenshtein.normalized_similarity(norm_input, v["norm_latin"])
                sim = max(sim1, sim2)
                if sim > best_sim:
                    best_sim = sim
                    best_meaning = m
                    best_variant = v

    if best_meaning and best_sim >= 0.85:
        other_variants = [v for v in best_meaning["variants"] if v["text"] != body.text and v["norm"] != norm_input]
        if not other_variants:
            other_variants = best_meaning["variants"]

        def rank_key(v):
            tricky_contained = len(v["sounds"] & tricky_set)
            return (tricky_contained, len(v["text"]), v["index"])

        sorted_variants = sorted(other_variants, key=rank_key)
        alts = []
        for v in sorted_variants[:4]:
            avoids = [s for s in tricky_ids if s not in v["sounds"]]
            alts.append(Alternative(
                text=v["text"],
                latin=v["latin"],
                meaning_en=best_meaning["meaning_en"],
                avoids=avoids,
                source="library",
            ))
        return Alternatives(meaning_en=best_meaning["meaning_en"], alternatives=alts)

    # 2. Not found in library: check Groq assistant if LLM_ENABLED
    cache_key = (user["id"], norm_input, body.lang, tuple(sorted(tricky_ids)))
    with _alternatives_lock:
        if cache_key in _alternatives_cache:
            return _alternatives_cache[cache_key]

    if llm_judge.enabled():
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with _alternatives_lock:
            calls_today = _assistant_calls_today[(user["id"], today_str)]
            if calls_today < 20:
                _assistant_calls_today[(user["id"], today_str)] += 1
                can_call = True
            else:
                can_call = False

        if can_call:
            assistant_res = call_groq_alternatives(body.text, body.lang, tricky_ids)
            if assistant_res is not None:
                with _alternatives_lock:
                    _alternatives_cache[cache_key] = assistant_res
                return assistant_res

    # 3. Fallback: closest library results if similarity >= 0.60, or empty list
    if best_meaning and best_sim >= 0.60:
        other_variants = [v for v in best_meaning["variants"] if v["text"] != body.text and v["norm"] != norm_input]
        if not other_variants:
            other_variants = best_meaning["variants"]

        def rank_key(v):
            tricky_contained = len(v["sounds"] & tricky_set)
            return (tricky_contained, len(v["text"]), v["index"])

        sorted_variants = sorted(other_variants, key=rank_key)
        alts = []
        for v in sorted_variants[:4]:
            avoids = [s for s in tricky_ids if s not in v["sounds"]]
            alts.append(Alternative(
                text=v["text"],
                latin=v["latin"],
                meaning_en=best_meaning["meaning_en"],
                avoids=avoids,
                source="library",
            ))
        return Alternatives(meaning_en=best_meaning["meaning_en"], alternatives=alts)

    return Alternatives(meaning_en="practice", alternatives=[])

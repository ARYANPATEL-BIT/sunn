"""The Trainings content in content/trainings/: the models every file is read through, and
problems(), the checks across files that one model can't make. Together they are the content
half of docs/TRAININGS_CONTRACT.md. src/trainings.py serves the content and
scripts/validate_trainings.py checks it; this module needs neither of them."""
import os
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "trainings")

# Lowercase words joined by hyphens: every id, and every audio_key, which is also a file name.
Id = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
Line = Annotated[str, Field(min_length=1)]
Lang = Literal["hi", "en"]
Feedback = Literal["none", "pace", "words"]
Feeling = Literal["easy", "okay", "hard"]
Wpm = Annotated[int, Field(ge=30, le=200)]
# The category icons, drawn in web/src/ui/icons.jsx.
Icon = Literal["waves", "audioLines", "shapes", "messages"]
Technique = Literal["easy-start", "light-touch", "slow-pace", "pausing", "tongue-place", "take-turns"]
# Their steps may give pace feedback but never say which words to practise.
NO_WORD_FEEDBACK = {"smooth-speaking", "kids-speaking"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a misspelt field is an error, not ignored


class Text(Strict):
    en: Line
    hi: Line


class Texts(Strict):
    en: list[Line] = Field(min_length=1)
    hi: list[Line] = Field(min_length=1)


class Category(Strict):
    id: Id
    title: Text
    subtitle: Text
    description: Text
    icon: Icon
    audience: Literal["all", "kids"]
    order: int


class Example(Strict):
    text: Line
    latin: Line


class Sound(Strict):
    id: Id
    label: Text
    devanagari: list[Line]  # [] for a sound Hindi doesn't have, like English th
    latin: list[Line] = Field(min_length=1)
    examples: list[Example] = Field(min_length=1)
    practise_lesson_id: Id | None = None  # null until a lesson practises it


# --- steps: every one has id, type and title

class Step(Strict):
    id: Id  # unique across all courses: attempts name a step by its id alone
    title: Text


class Intro(Step):
    type: Literal["intro"]
    body: Text


class Tip(Step):
    type: Literal["tip"]
    body: Text
    technique_id: Technique


class Breath(Strict):
    """Seconds in, then out. There is deliberately no hold."""
    in_s: int = Field(ge=2, le=6)
    out_s: int = Field(ge=2, le=8)


class Breathing(Step):
    type: Literal["breathing"]
    body: Text
    pattern: Breath
    rounds: int = Field(ge=1, le=10)


class Item(Strict):
    id: Id  # unique in its step
    text: Line
    latin: Line
    meaning_en: Line
    focus_sound: Id | None = None  # a sound id from sounds.json
    audio_key: Id


class ListenRepeat(Step):
    type: Literal["listen_repeat"]
    items: list[Item] = Field(min_length=1)
    feedback: Feedback


class SpeakWithMe(Step):
    type: Literal["speak_with_me"]
    text: Line
    latin: Line
    meaning_en: Line | None = None
    mode: Literal["choral", "echo", "paced"]  # Sunn speaks along / Sunn first, then you / words light up, no audio
    pace_wpm: tuple[Wpm, Wpm]  # [min, max] words per minute
    audio_key: Id | None = None  # null exactly when mode is paced
    feedback: Feedback


class Word(Strict):
    text: Line
    latin: Line
    audio_key: Id


class Pair(Strict):
    id: Id  # unique in its step
    a: Word
    b: Word
    sound_a: Id
    sound_b: Id


class MinimalPairs(Step):
    type: Literal["minimal_pairs"]
    pairs: list[Pair] = Field(min_length=1)


class ReadAloud(Step):
    type: Literal["read_aloud"]
    paragraph: Line
    latin: Line | None = None
    audio_key: Id
    feedback: Feedback


class Option(Strict):
    text: Line
    latin: Line


class Turn(Strict):
    speaker: Literal["sunn", "you"]
    text: Line  # on a you turn, the suggested line
    latin: Line
    audio_key: Id | None = None  # every sunn turn has one, a you turn never
    options: list[Option] | None = None  # other lines you could say instead; only on a you turn


class Dialogue(Step):
    type: Literal["dialogue"]
    scenario: Text
    turns: list[Turn] = Field(min_length=2)


class Reflect(Step):
    type: Literal["reflect"]
    prompt: Text
    choices: list[Feeling]  # always easy, okay, hard


AnyStep = Annotated[Intro | Tip | Breathing | ListenRepeat | SpeakWithMe | MinimalPairs | ReadAloud | Dialogue
                    | Reflect, Field(discriminator="type")]
STEP_TYPES = [get_args(model.model_fields["type"].annotation)[0] for model in get_args(get_args(AnyStep)[0])]


class Lesson(Strict):
    id: Id
    title: Text
    minutes: int = Field(ge=1)
    steps: list[AnyStep] = Field(min_length=1)


class Course(Strict):
    id: Id  # also its file name: courses/<id>.json
    category_id: Id
    title: Text
    summary: Text
    what_you_practise: Texts
    level: Literal["beginner"]
    minutes: int = Field(ge=1)  # the sum of its lessons' minutes
    practice_lang: Lang  # the language the lines are spoken in
    lessons: list[Lesson] = Field(min_length=1)


class AudioLine(Strict):
    """What Timbre says for one audio_key, in the stock voice of lang."""
    text: Line
    lang: Lang


class Library:
    """Everything in content/trainings/, read and validated, with lookups by id."""

    def __init__(self, categories, sounds, audio, courses):
        self.categories = sorted(categories, key=lambda c: c.order)
        self.sounds, self.audio, self.courses = sounds, audio, courses  # courses: {file name: Course}
        self.lessons = {lesson.id: (course, lesson) for course in courses.values() for lesson in course.lessons}
        self.steps = {step.id: (course, lesson, step) for course, lesson in self.lessons.values() for step in lesson.steps}

    def courses_in(self, category_id):
        return [c for c in self.courses.values() if c.category_id == category_id]


def read(path, model):
    try:
        with open(path, encoding="utf-8") as f:
            return TypeAdapter(model).validate_json(f.read())
    except ValidationError as e:
        raise ValueError(f"{os.path.relpath(path, ROOT)}: {e}") from None


def load(root=ROOT):
    """The Library in root; ValueError naming the file when one doesn't fit its model."""
    folder = os.path.join(root, "courses")
    courses = {name.removesuffix(".json"): read(os.path.join(folder, name), Course)
               for name in sorted(os.listdir(folder)) if name.endswith(".json")}
    return Library(read(os.path.join(root, "categories.json"), list[Category]),
                   read(os.path.join(root, "sounds.json"), list[Sound]),
                   read(os.path.join(root, "audio.json"), dict[Id, AudioLine]), courses)


def spoken(step):
    """(audio_key, the text Timbre says for it) for every line of step that has audio."""
    if isinstance(step, ListenRepeat):
        return [(item.audio_key, item.text) for item in step.items]
    if isinstance(step, MinimalPairs):
        return [(word.audio_key, word.text) for pair in step.pairs for word in (pair.a, pair.b)]
    if isinstance(step, ReadAloud):
        return [(step.audio_key, step.paragraph)]
    if isinstance(step, SpeakWithMe | Dialogue):
        lines = step.turns if isinstance(step, Dialogue) else [step]
        return [(line.audio_key, line.text) for line in lines if line.audio_key]
    return []


def duplicates(ids):
    seen, twice = set(), set()
    for i in ids:
        (twice if i in seen else seen).add(i)
    return sorted(twice)


def problems(library):
    """Every way library breaks the contract that its models can't see, in plain English."""
    found = []
    for kind, ids in [("category", [c.id for c in library.categories]), ("sound", [s.id for s in library.sounds]),
                      ("lesson", [l.id for c in library.courses.values() for l in c.lessons]),
                      ("step", [s.id for c in library.courses.values() for l in c.lessons for s in l.steps])]:
        found += [f"{kind} id {i} is used twice" for i in duplicates(ids)]

    categories, sounds = {c.id for c in library.categories}, {s.id for s in library.sounds}
    used = {}  # audio_key -> text
    for name, course in library.courses.items():
        where = f"courses/{name}.json"
        if course.id != name:
            found.append(f"{where}: id is {course.id}, not the file name")
        if course.category_id not in categories:
            found.append(f"{where}: no category {course.category_id}")
        if course.minutes != sum(lesson.minutes for lesson in course.lessons):
            found.append(f"{where}: minutes is not the sum of its lessons' minutes")
        for lesson in course.lessons:
            for step in lesson.steps:
                at = f"{where}: step {step.id}"
                found += [f"{at}: {e}" for e in step_problems(step, course, sounds)]
                for key, text in spoken(step):
                    listed = library.audio.get(key)
                    if used.setdefault(key, text) != text:
                        found.append(f"{at}: audio_key {key} is used for two different texts")
                    if listed is None:
                        found.append(f"{at}: audio_key {key} is not listed in audio.json")
                    elif (listed.text, listed.lang) != (text, course.practice_lang):
                        found.append(f"{at}: audio.json has another text or language for {key}")
    found += [f"audio.json: {key} is not used by any step" for key in sorted(library.audio.keys() - used.keys())]
    found += [f"sounds.json: {s.id} names lesson {s.practise_lesson_id}, which doesn't exist"
              for s in library.sounds if s.practise_lesson_id and s.practise_lesson_id not in library.lessons]
    return found


def step_problems(step, course, sounds):
    found = []
    if getattr(step, "feedback", None) == "words" and course.category_id in NO_WORD_FEEDBACK:
        found.append(f"{course.category_id} steps may only use feedback none or pace")
    if isinstance(step, ListenRepeat):
        found += [f"item id {i} is used twice" for i in duplicates(item.id for item in step.items)]
        found += [f"no sound {item.focus_sound}" for item in step.items
                  if item.focus_sound and item.focus_sound not in sounds]
    if isinstance(step, MinimalPairs):
        found += [f"pair id {i} is used twice" for i in duplicates(pair.id for pair in step.pairs)]
        found += [f"no sound {s}" for pair in step.pairs for s in (pair.sound_a, pair.sound_b) if s not in sounds]
    if isinstance(step, SpeakWithMe):
        if step.pace_wpm[0] > step.pace_wpm[1]:
            found.append("pace_wpm is [min, max]")
        if (step.mode == "paced") != (step.audio_key is None):
            found.append("a paced step has no audio_key, and a choral or echo step needs one")
    if isinstance(step, Dialogue):
        for n, turn in enumerate(step.turns):
            if (turn.speaker == "sunn") != (turn.audio_key is not None):
                found.append(f"turn {n}: every sunn turn has an audio_key, and a you turn none")
            if turn.speaker == "sunn" and turn.options:
                found.append(f"turn {n}: only a you turn has options")
    if isinstance(step, Reflect) and step.choices != list(get_args(Feeling)):
        found.append("choices are easy, okay, hard")
    return found

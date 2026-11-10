"""Every request and response body of the API. FastAPI turns these into /docs, which is the
live contract; docs/API.md is the short version. Each response model carries one realistic
example, shown in /docs."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

import languages

Language = Literal[languages.CODES]  # the language the user speaks, or a phrase is in
Context = Literal["home", "hospital", "market"]  # where the user is, for POST /me/recognize
PhraseContext = Literal["home", "hospital", "market", "any"]  # where a phrase is used
Slot = Literal["item", "person", "place"]
SpeechSource = Literal["pilot", "torgo", "simulated"]  # where a demo recording came from

ErrorCode = Literal[
    "not_logged_in", "not_found", "consent_required", "invalid_input",
    "audio_too_short", "audio_too_long", "file_too_large", "no_speech",
    "gnani_unreachable", "gnani_rejected", "credit_limit_reached", "daily_cap_reached", "invite_required",
    # Specific refusals the app words on their own.
    "bad_login", "too_many_attempts", "email_taken", "no_name", "bad_email", "short_password",
    "phrase_exists", "no_voice", "not_owner", "bad_audio", "server_error",
    "invalid_google_token", "google_unreachable", "unverified_email",
]


def example(**values):
    return ConfigDict(json_schema_extra={"examples": [values]})


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")  # an unknown field is invalid_input, not ignored


# --- errors

class Error(BaseModel):
    """Every error. The extra fields come only with the codes that use them."""
    model_config = example(error="audio_too_short", message="the recording is 0.2 s; it needs 0.3 to 15 s",
                           seconds=0.2)
    error: ErrorCode
    message: str  # plain English, for logs and developers; the app words error itself
    seconds: float | None = None  # audio_too_short, audio_too_long: how long the recording was
    retry_after: int | None = None  # too_many_attempts: seconds until login opens again
    phrase_id: int | None = None  # phrase_exists: the phrase that already has this text


class Ok(BaseModel):
    model_config = example(ok=True)
    ok: Literal[True]


# --- account

class Signup(Request):
    name: str
    email: str
    password: str  # 8 or more characters
    language: Language
    consent: bool = False  # must be true
    invite_code: str | None = None  # needed when GET /config says invite_required


class Login(Request):
    email: str
    password: str


class GoogleAuth(Request):
    id_token: str
    invite_code: str | None = None
    language: Language = "en"
    consent: bool = True


class User(BaseModel):
    model_config = example(id=7, name="सुनीता", email="sunita@example.com", language="hi",
                           consent_given_at="2026-10-01T09:30:00Z", caregiver_name="राहुल",
                           caregiver_phone="919876543210", has_own_voice=True, use_own_voice=True,
                           can_clone_voice=True, phrase_goal=10)
    id: int
    name: str
    email: str
    language: Language
    consent_given_at: datetime
    caregiver_name: str | None
    caregiver_phone: str | None  # digits with the country code, ready for https://wa.me/<phone>
    has_own_voice: bool  # a cloned voice is recorded
    use_own_voice: bool  # /speak uses it
    can_clone_voice: bool  # own voice is offered in the language the user speaks (speak.CLONE_LANGUAGES)
    phrase_goal: int | None = None


class UserUpdate(Request):
    """Any of these; null or "" clears a caregiver field."""
    use_own_voice: bool | None = None  # true needs a recorded voice
    caregiver_name: str | None = None
    caregiver_phone: str | None = None  # spaces, dashes, brackets and + are dropped
    language: Language | None = None  # Prisma and new phrases follow it; nothing is deleted
    phrase_goal: int | None = None


class Config(BaseModel):
    model_config = example(invite_required=False)
    invite_required: bool  # sign-up needs an invite code


class GoogleConfig(BaseModel):
    model_config = example(client_id="")
    client_id: str  # Google OAuth Client ID for GIS


# --- phrases

class Phrase(BaseModel):
    model_config = example(id=12, text="पानी चाहिए", contexts=["home", "hospital"], urgent=False, language="hi")
    id: int
    text: str
    contexts: list[PhraseContext]
    urgent: bool
    language: Language  # the phrase's own; Timbre says it in this language


class PhraseDetail(Phrase):
    model_config = example(id=12, text="पानी चाहिए", contexts=["home", "hospital"], urgent=False, language="hi",
                           enrolled=3, sample_count=9, last_used_at="2026-10-20T18:05:00Z", sources=[])
    enrolled: int  # enrollment recordings
    sample_count: int  # enrollments and confirmed recognitions in the user's current language or English
    last_used_at: datetime | None
    sources: list[SpeechSource]  # where its demo recordings came from; [] when all were made in the app


class NewPhrase(Request):
    text: str


class PhraseUpdate(Request):
    text: str | None = None
    contexts: list[PhraseContext] | None = None  # [] means any
    urgent: bool | None = None


class Enrolled(BaseModel):
    """One enrollment recording. Exactly one of phrase_id, slot_word_id, template_id is set."""
    model_config = example(sample_id=301, hypothesis="paani chahiye", phrase_id=12, slot_word_id=None,
                           template_id=None, source=None)
    sample_id: int
    hypothesis: str  # what Prisma heard
    phrase_id: int | None = None
    slot_word_id: int | None = None
    template_id: int | None = None
    source: SpeechSource | None = None  # set only for a demo recording (scripts/load_demo.py)


class SlotWord(BaseModel):
    model_config = example(id=2, slot="item", text="दवाई", enrolled=2)
    id: int
    slot: Slot
    text: str
    enrolled: int


class NewSlotWord(Request):
    slot: Slot
    text: str


class Template(BaseModel):
    model_config = example(id=1, text="{item} चाहिए", fixed_part="चाहिए", slot="item", enrolled=3)
    id: int
    text: str  # one {item}, {person} or {place}, at the start or end
    fixed_part: str  # the words recorded on their own
    slot: Slot
    enrolled: int


class NewTemplate(Request):
    text: str


# --- speak

class ScoreParts(BaseModel):
    similarity: float  # 0-100
    context: float  # 0 or 6
    freq: float  # 0-4
    time: float  # 0-3
    # 0 to RERANKER_WEIGHT; left out unless RERANKER_ENABLED
    rerank: float | None = Field(None, exclude_if=lambda value: value is None)


class Candidate(BaseModel):
    """A phrase, or (composed) a template × slot word that isn't a phrase yet."""
    phrase_id: int | None  # null when composed
    text: str
    score: float  # similarity + context + freq + time
    parts: ScoreParts
    urgent: bool
    composed: bool
    template_id: int | None = None  # set when composed
    slot_word_id: int | None = None  # set when composed


class Timings(BaseModel):
    """Milliseconds per step; null for a step that didn't run."""
    stt: int | None = None  # storing the upload and Prisma
    match: int | None = None
    rerank: int | None = None  # RERANKER_ENABLED
    llm: int | None = None  # the judge, when it was asked
    tts: int | None = None  # always null here: Timbre runs in POST /speak (its Server-Timing header)


class Recognition(BaseModel):
    model_config = example(
        sample_id=412, hypothesis="dawai chahie", context="hospital", low_confidence=False, candidates=[
            {"phrase_id": 14, "text": "दवाई चाहिए", "score": 92.4, "urgent": False, "composed": False,
             "parts": {"similarity": 84.6, "context": 6, "freq": 1.2, "time": 0.6},
             "template_id": None, "slot_word_id": None},
            {"phrase_id": None, "text": "चाय चाहिए", "score": 71.3, "urgent": False, "composed": True,
             "parts": {"similarity": 71.3, "context": 0, "freq": 0, "time": 0},
             "template_id": 1, "slot_word_id": 4},
            {"phrase_id": 2, "text": "दर्द हो रहा है", "score": 48.0, "urgent": True, "composed": False,
             "parts": {"similarity": 42.0, "context": 6, "freq": 0, "time": 0},
             "template_id": None, "slot_word_id": None}],
        chosen_by="judge", reason="sounds like dawai chahiye, and they are at hospital",
        timings_ms={"stt": 840, "match": 12, "rerank": None, "llm": 610, "tts": None})
    sample_id: int  # pass to /me/confirm
    hypothesis: str  # what Prisma heard
    context: Context | None
    candidates: list[Candidate]  # best first, at most 3
    low_confidence: bool  # the first candidate's similarity is under 60
    chosen_by: Literal["matcher", "judge"] = "matcher"  # which put the first candidate first
    reason: str | None = None  # the judge's, in plain English, when chosen_by is judge
    timings_ms: Timings | None = None


class Confirm(Request):
    """sample_id plus one of: phrase_id, new_text, or template_id with slot_word_id."""
    sample_id: int
    phrase_id: int | None = None
    new_text: str | None = None
    template_id: int | None = None
    slot_word_id: int | None = None


class Confirmed(BaseModel):
    model_config = example(sample_id=412, phrase_id=14, text="दवाई चाहिए", urgent=False)
    sample_id: int
    phrase_id: int
    text: str
    urgent: bool


class Speak(Request):
    text: str


# --- progress

class Week(BaseModel):
    week_start: date  # a Monday
    confirmed: int
    clear: int  # confirmed recognitions Prisma already got right without the personal layer
    rate: float | None  # clear / confirmed; null in a week with none


class TopPhrase(BaseModel):
    phrase_id: int
    text: str
    uses: int


class Stats(BaseModel):
    model_config = example(
        phrases=51, samples=164, enroll_samples=153, recognitions=14, confirmed=11, top1_hits=9,
        top1_hit_rate=0.818,
        clear_without_help_by_week=[
            {"week_start": "2026-08-31", "confirmed": 0, "clear": 0, "rate": None},
            {"week_start": "2026-09-07", "confirmed": 0, "clear": 0, "rate": None},
            {"week_start": "2026-09-14", "confirmed": 0, "clear": 0, "rate": None},
            {"week_start": "2026-09-21", "confirmed": 0, "clear": 0, "rate": None},
            {"week_start": "2026-09-28", "confirmed": 2, "clear": 0, "rate": 0.0},
            {"week_start": "2026-10-05", "confirmed": 3, "clear": 1, "rate": 0.333},
            {"week_start": "2026-10-12", "confirmed": 4, "clear": 1, "rate": 0.25},
            {"week_start": "2026-10-19", "confirmed": 2, "clear": 1, "rate": 0.5}],
        top_phrases=[{"phrase_id": 14, "text": "दवाई चाहिए", "uses": 5},
                     {"phrase_id": 12, "text": "पानी चाहिए", "uses": 4},
                     {"phrase_id": 2, "text": "दर्द हो रहा है", "uses": 2}])
    phrases: int
    samples: int  # enrollments and confirmed recognitions
    enroll_samples: int
    recognitions: int
    confirmed: int
    top1_hits: int  # confirmed as the first candidate
    top1_hit_rate: float | None
    clear_without_help_by_week: list[Week]  # the last 8 weeks, oldest first
    top_phrases: list[TopPhrase]  # the 5 most used


class KindUsage(BaseModel):
    sent: int
    cached: int
    sent_audio_seconds: float


class Usage(BaseModel):
    model_config = example(limit=4000, sent=212, remaining=3788, by_kind={
        "stt": {"sent": 190, "cached": 640, "sent_audio_seconds": 412.5},
        "tts": {"sent": 21, "cached": 96, "sent_audio_seconds": 38.2},
        "clone": {"sent": 1, "cached": 0, "sent_audio_seconds": 0.0}})
    limit: int
    sent: int
    remaining: int
    by_kind: dict[Literal["stt", "tts", "clone"], KindUsage]


class Health(BaseModel):
    model_config = example(status="ok")
    status: Literal["ok"]

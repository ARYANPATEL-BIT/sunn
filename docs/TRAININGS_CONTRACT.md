# Trainings contract

Trainings is a speaking practice area in Sunn: short course-style lessons to practise speaking
with more ease and confidence. This file is the single source of truth for the content files
and the API between them. Person A builds the backend, person B the frontend; when either
needs a change here, change this file first and tell the other.

The code that holds each side to it:

- `src/trainings_content.py`: the models every content file is read through, and the checks
  across files. `uv run scripts/validate_trainings.py` runs both.
- `src/trainings.py`: the API. The server refuses to start when the content breaks this contract.
- `tests/test_contract.py` checks that every route below exists and that every example is
  exactly what its response model gives. `tests/test_trainings.py` checks each route's shape.

## Rules for everyone

- **Practice, not therapy.** Trainings is a practice and confidence tool. Nothing in the content
  or the interface says it treats, cures, fixes or diagnoses anything. A lesson for a
  condition says it is practice, and that a speech therapist's advice comes first.
- **Kind feedback.** A word is `clear` or `practise`, never wrong. Smooth speaking and kids
  never say which words to practise (the feedback rule below). Kids get no scores at all.
- **Gnani only.** Gnani Prisma is the only speech to text, Gnani Timbre the only text to
  speech. Lesson audio is made ahead of time by Timbre (see `audio.json`).
- **Original text only.** No rhymes, songs or stories copied from anywhere.
- Copy follows `web/DESIGN.md`: short plain sentences, no em dashes. Hindi uses forms that
  don't assume the reader's gender (imperatives like बोलिए, not बोल सकते हैं).

## Content files

```
content/trainings/
  categories.json        the four categories, in order
  sounds.json            the sounds lessons practise and tricky-sounds names
  audio.json             every audio_key, with the text Timbre says for it
  courses/<id>.json      one course per file, named by its id
```

Every id and every `audio_key` is lowercase letters and digits joined by hyphens
(`easy-starts-2`). A field written `name?` below may be left out of a file; the API always
sends it, as `null`. Bilingual text is `{"en": "...", "hi": "..."}` and both are required.

### categories.json

A list. Fields: `id`, `title{en,hi}`, `subtitle{en,hi}`, `description{en,hi}`, `icon`,
`audience` (`all` or `kids`), `order` (the API sorts by it).

| order | id | title | icon |
| - | - | - | - |
| 1 | `smooth-speaking` | Smooth speaking / सहज बोलना (for people who stammer, हकलाहट) | `waves` |
| 2 | `clear-sounds` | Clear sounds / साफ़ उच्चारण (pronunciation, lisping, तुतलाहट) | `audioLines` |
| 3 | `kids-speaking` | Speaking games for kids / बच्चों के बोलने के खेल (with an adult), audience `kids` | `shapes` |
| 4 | `everyday-talk` | Everyday conversations / रोज़ की बातचीत | `messages` |

`icon` is one of these four names. Person B draws them in `web/src/ui/icons.jsx` in its stroke
style (Lucide's `waves`, `audio-lines`, `shapes` and `messages-square` geometry fits).

### courses/&lt;id&gt;.json

`id` (the file name), `category_id`, `title{en,hi}`, `summary{en,hi}`,
`what_you_practise{en[],hi[]}`, `level` (`beginner`), `minutes` (the sum of its lessons'),
`practice_lang` (`hi` or `en`: the language the lines are spoken in), `lessons[]`.

A lesson: `id` (unique across all courses), `title{en,hi}`, `minutes`, `steps[]`.

`latin` is the line in Latin letters: a simple romanisation for Hindi, the same text for
English. For an `en` course `latin` repeats `text` and `meaning_en` says when to use it, so the
app can hide `latin` there.

### Steps

Every step has `id` (unique across all courses, since attempts name a step by id alone),
`type` and `title{en,hi}`.

| type | fields | what the app does |
| - | - | - |
| `intro` | `body{en,hi}` | shows the text |
| `tip` | `body{en,hi}`, `technique_id` | shows the text; the technique can have its own small drawing |
| `breathing` | `body{en,hi}`, `pattern{in_s, out_s}`, `rounds` | paces `rounds` breaths: in for `in_s` seconds, out for `out_s`. There is never a hold |
| `listen_repeat` | `items[{id, text, latin, meaning_en, focus_sound?, audio_key}]`, `feedback` | plays each item, the user says it back |
| `speak_with_me` | `text`, `latin`, `meaning_en?`, `mode`, `pace_wpm[min, max]`, `audio_key`, `feedback` | `choral`: Sunn speaks along with you. `echo`: Sunn first, then you. `paced`: the words light up one by one at the middle of `pace_wpm`, with no audio, and `audio_key` is null |
| `minimal_pairs` | `pairs[{id, a{text, latin, audio_key}, b{...}, sound_a, sound_b}]` | plays a pair to hear the difference, the user says both. Not recorded |
| `read_aloud` | `paragraph`, `latin?`, `audio_key`, `feedback` | the user reads; Sunn's reading can be played first |
| `dialogue` | `scenario{en,hi}`, `turns[{speaker, text, latin, audio_key?, options?[{text, latin}]}]` | `sunn` turns play (each has an `audio_key`); on a `you` turn the user says `text`, or one of `options` instead. Not recorded |
| `reflect` | `prompt{en,hi}`, `choices` (always `["easy", "okay", "hard"]`) | asks how it felt; sent to `POST /me/trainings/reflect` |

`technique_id` is one of: `easy-start` (let a little air out, then start the sound softly),
`light-touch` (lips and tongue meet lightly), `slow-pace` (stretch words a little),
`pausing` (a short pause between ideas), `tongue-place` (where the tongue and lips go for a
sound), `take-turns` (the adult says it first and waits).

`focus_sound`, `sound_a` and `sound_b` are sound ids from `sounds.json`.

**Feedback** says what a checked attempt reports: `none` (nothing is checked), `pace` (words
per minute against `pace_wpm`, or 70 to 120 for a step without one) or `words` (which words
were clear). **The feedback rule:** steps in `smooth-speaking` and `kids-speaking` courses use
only `none` or `pace`, never `words`.

### sounds.json

A list. `id`, `label{en,hi}`, `devanagari[]` (empty for a sound Hindi doesn't have),
`latin[]`, `examples[{text, latin}]`, `practise_lesson_id` (a lesson that practises it, or
null). The ids: `p`, `b`, `t-dental`, `t-retroflex`, `d`, `k`, `g`, `ch`, `j`, `s`, `sh`, `r`,
`l`, `aspirated`, `nasal`, `clusters`, `th-english`.

### audio.json

`{"<audio_key>": {"text": "...", "lang": "hi"}}`: what Timbre says for each key, in the stock
voice of the course's `practice_lang`. Every key used in a course is listed here with exactly
the text it is used for, and every key listed is used. Person A makes the files ahead of time
into `data/trainings/audio/<audio_key>.wav` (under `DATA_DIR`, so never committed); the API
serves them. Changing a line's text means listing the new text and making its audio again.

## What is kept

- Practice audio is never stored. Prisma hears it, and only the transcript, the scores and
  the pace are kept.
- `kids-speaking` attempts keep no transcript at all, only the pace.
- Reflections keep the feeling and the step.
- Deleting the account (`DELETE /me`) deletes all of it.
- `POST /me/trainings/alternatives` may send its text to the LLM (`source: assistant`), only
  when `LLM_ENABLED`. The privacy page says so.

## API

As in `docs/API.md`: every path is under `/api` in the browser, bodies are JSON, errors have
the one shape there (`not_found` for an unknown id, `invalid_input` for a bad field,
`not_logged_in` without a session). Browsing (categories, courses, lessons, audio) needs no
session, and shows progress when there is one. Every route under `/me` needs the session.

**real** routes work now. **stub** routes answer made-up data of exactly this shape and
check their ids against the content, but store nothing (`TODO(person A)` in
`src/trainings.py`). Their URL and shape won't change when the real logic replaces them.

`percent` everywhere is completed lessons over all lessons, 0 to 100, rounded; `null` when
signed out.

### `GET /trainings/categories` · real

Every category in order, with its number of courses.

```json
[{"id": "smooth-speaking", "title": {"en": "Smooth speaking", "hi": "सहज बोलना"},
  "subtitle": {"en": "Gentle starts and a calm pace", "hi": "हल्की शुरुआत, आराम की रफ़्तार"},
  "description": {"en": "For people who stammer, and anyone who wants to speak with more ease.", "hi": "हकलाहट वाले लोगों के लिए, और हर उस व्यक्ति के लिए जो आराम से बोलना चाहता है।"},
  "icon": "waves", "audience": "all", "order": 1, "course_count": 1, "percent": 50},
 {"id": "kids-speaking", "title": {"en": "Speaking games for kids", "hi": "बच्चों के बोलने के खेल"},
  "subtitle": {"en": "Play together with an adult", "hi": "किसी बड़े के साथ मिलकर खेलें"},
  "description": {"en": "Short sound games for a child to play with a parent or another adult.", "hi": "बच्चों के लिए छोटे खेल, जो वे माता-पिता या किसी बड़े के साथ खेलें।"},
  "icon": "shapes", "audience": "kids", "order": 3, "course_count": 1, "percent": 0}]
```

Errors: none.

### `GET /trainings/categories/{category_id}` · real

The category and its courses.

```json
{"id": "clear-sounds", "title": {"en": "Clear sounds", "hi": "साफ़ उच्चारण"},
 "subtitle": {"en": "One sound at a time", "hi": "एक बार में एक आवाज़"},
 "description": {"en": "For anyone who finds some sounds hard to say, including a lisp.", "hi": "उनके लिए जिन्हें कुछ आवाज़ें बोलना मुश्किल लगता है, तुतलाहट भी।"},
 "icon": "audioLines", "audience": "all", "order": 2,
 "courses": [{"id": "s-and-sh", "title": {"en": "S and Sh", "hi": "स और श"},
   "summary": {"en": "Hear the difference between s and sh, then practise each one.", "hi": "स और श का फ़र्क़ सुनिए, फिर दोनों का अभ्यास कीजिए।"},
   "level": "beginner", "minutes": 13, "practice_lang": "hi", "lesson_count": 2, "percent": null}]}
```

Errors: `not_found`.

### `GET /trainings/courses/{course_id}` · real

The course and its lessons. `completed` is false when signed out.

```json
{"id": "easy-starts", "category_id": "smooth-speaking", "title": {"en": "Easy starts", "hi": "आराम से शुरुआत"},
 "summary": {"en": "Begin words gently, on a slow breath out. Two short lessons.", "hi": "शब्दों को धीमी साँस छोड़ते हुए हल्के से शुरू कीजिए। दो छोटे पाठ।"},
 "what_you_practise": {"en": ["Breathing out slowly before you speak", "Starting the first sound softly"],
                       "hi": ["बोलने से पहले धीरे-धीरे साँस छोड़ना", "पहली आवाज़ हल्के से शुरू करना"]},
 "level": "beginner", "minutes": 13, "practice_lang": "hi", "percent": 50,
 "lessons": [{"id": "easy-starts-1", "title": {"en": "Breath and a soft start", "hi": "साँस और हल्की शुरुआत"}, "minutes": 6, "step_count": 6, "completed": true},
             {"id": "easy-starts-2", "title": {"en": "Light touches", "hi": "हल्का स्पर्श"}, "minutes": 7, "step_count": 7, "completed": false}]}
```

Errors: `not_found`.

### `GET /trainings/lessons/{lesson_id}` · real

The whole lesson, with every step as in the content files (every field present, `null` when
left out). `category_id` says whether it is a kids lesson; `next_lesson_id` is null for a
course's last lesson. Shortened here to two steps.

```json
{"id": "easy-starts-2", "title": {"en": "Light touches", "hi": "हल्का स्पर्श"}, "minutes": 7,
 "course_id": "easy-starts", "category_id": "smooth-speaking", "practice_lang": "hi", "next_lesson_id": null,
 "steps": [
  {"id": "easy-starts-2-paced", "type": "speak_with_me", "title": {"en": "Follow the words", "hi": "शब्दों के साथ चलिए"},
   "text": "मेरे पास बोलने के लिए पूरा समय है", "latin": "mere paas bolne ke liye poora samay hai",
   "meaning_en": "I have all the time I need to speak.", "mode": "paced", "pace_wpm": [50, 80],
   "audio_key": null, "feedback": "pace"},
  {"id": "easy-starts-2-tea-stall", "type": "dialogue", "title": {"en": "At the tea stall", "hi": "चाय की दुकान पर"},
   "scenario": {"en": "You are at a tea stall.", "hi": "आप चाय की दुकान पर हैं।"},
   "turns": [
    {"speaker": "sunn", "text": "नमस्ते! क्या लेंगे?", "latin": "namaste! kya lenge?", "audio_key": "easy-starts-stall-1", "options": null},
    {"speaker": "you", "text": "एक चाय, कम चीनी वाली।", "latin": "ek chaay, kam cheeni waali.", "audio_key": null,
     "options": [{"text": "एक चाय और दो बिस्कुट।", "latin": "ek chaay aur do biscuit."}]}]}]}
```

Errors: `not_found`.

### `GET /trainings/audio/{audio_key}` · real

Answers `audio/wav`: Sunn saying that line. `not_found` for a key not in `audio.json`, and
for a listed key whose audio hasn't been made yet, so the app hides the play button then.
With `GNANI_MOCK` on, a listed key without audio answers half a second of silence instead.

Errors: `not_found`.

### `GET /me/trainings/progress` · real

Every course the user has started, where to pick up again (`step_index` is 0-based; `resume`
is null before any progress), and this week's totals (`days_this_week` counts days since
Monday with any practice).

```json
{"courses": [{"id": "easy-starts", "percent": 50}],
 "resume": {"course_id": "easy-starts", "lesson_id": "easy-starts-2", "step_index": 2},
 "lessons_done": 1, "minutes_practised": 9, "days_this_week": 2}
```

Errors: `not_logged_in`.

### `POST /me/trainings/progress` · real

`{"lesson_id": "easy-starts-2", "step_index": 3, "completed": false}`. Send it when the user
moves to a step, and with `completed: true` after the last one. Answers that lesson's progress.

```json
{"lesson_id": "easy-starts-2", "course_id": "easy-starts", "step_index": 3, "completed": false, "course_percent": 50}
```

Errors: `not_logged_in`, `not_found`, `invalid_input` (a `step_index` past the last step).

### `POST /me/trainings/reflect` · real

`{"lesson_id": "easy-starts-1", "step_id": "easy-starts-1-reflect", "feeling": "okay"}`.
`feeling` is `easy`, `okay` or `hard`; the step must be a `reflect` step of that lesson.

```json
{"ok": true}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`.

### `POST /me/trainings/attempts` · real

Form: `audio` (the try, 0.3 to 15 s), `step_id`, `item_id` (the item's id, for a
`listen_repeat` step only), `check` (`true` or `false`). Only `listen_repeat`,
`speak_with_me` and `read_aloud` steps take attempts.

With `check` true and a step whose `feedback` isn't `none`, Prisma hears the try and it is
scored: `pace` gives `wpm` and `pace`, `words` gives `words` and `similarity` (0 to 1). Else
nothing is sent to Prisma, `checked` is false and every score is null. Checks use the speech
service, so there are `checks_left_today`; at 0 a check isn't made (`no_checks_left`). The
recording itself is never kept.

`pace` is what to try next time: `slower` when the try was faster than the range, `faster`
when slower. `message_key` is what the app says, from its own i18n:

| message_key | when |
| - | - |
| `practised` | not checked |
| `no_checks_left` | `check` was true, but no checks are left today |
| `pace_good`, `pace_slower`, `pace_faster` | a pace check |
| `words_clear` | a words check, every word clear |
| `words_practise` | a words check, some words to practise |

```json
{"checked": true, "words": [{"text": "सोनू", "status": "clear"}, {"text": "सुबह", "status": "clear"},
  {"text": "सात", "status": "practise"}], "similarity": 0.82, "wpm": null, "pace": null,
 "message_key": "words_practise", "checks_left_today": 23}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`, `file_too_large`, `bad_audio`,
`audio_too_short`, `audio_too_long`, `no_speech`, `gnani_unreachable`, `gnani_rejected`,
`credit_limit_reached`, `daily_cap_reached`.

### `GET /me/trainings/tricky-sounds` · real

Sounds the user might like to practise, most evidence first, and a lesson for each. A
suggestion, never a diagnosis: word it as "You might like to practise", never "you have
trouble with". `evidence` counts Speak recognitions where words with the sound were heard
differently (`speak`), practice words with it marked `practise` (`practice`), and `hard`
reflections on steps that practise it (`self`). `why_key` names the biggest of the three:
`heard_in_speak`, `heard_in_practice` or `you_said_hard`. `[]` when there is nothing to suggest.

```json
[{"sound_id": "s", "label": {"en": "S", "hi": "स"}, "why_key": "heard_in_practice",
  "evidence": {"speak": 2, "practice": 5, "self": 1}, "practise_lesson_id": "s-and-sh-1"},
 {"sound_id": "sh", "label": {"en": "Sh", "hi": "श"}, "why_key": "heard_in_speak",
  "evidence": {"speak": 4, "practice": 1, "self": 0}, "practise_lesson_id": "s-and-sh-2"}]
```

Errors: `not_logged_in`.

### `POST /me/trainings/alternatives` · real

`{"text": "शुक्रिया", "lang": "hi"}`. Other ways to say the text that leave out the user's
tricky sounds (`avoids`), for a moment when being understood matters more than practice.
Offered as a choice, never pushed. `source` is `library` (Sunn's own list) or `assistant`
(the LLM, only when `LLM_ENABLED`).

```json
{"meaning_en": "thank you", "alternatives": [
  {"text": "धन्यवाद", "latin": "dhanyavaad", "meaning_en": "thank you", "avoids": ["sh"], "source": "library"},
  {"text": "बहुत मेहरबानी", "latin": "bahut meharbaani", "meaning_en": "thank you very much", "avoids": ["sh"], "source": "assistant"}]}
```

Errors: `not_logged_in`, `invalid_input`.

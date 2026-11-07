# Sunn API

The short version of the contract, for building the app. The live, complete one is `/api/docs`
(generated from `src/schemas.py`) wherever the app runs, like `http://127.0.0.1:7860/api/docs`
after `uv run src/server.py`.

- The web app calls relative `/api/...`, so `/me/phrases` here is `/api/me/phrases` in the
  browser. In production `src/server.py` serves the API under `/api`; in development Vite
  proxies `/api` to the API on port 8000.
- The session is an httpOnly cookie set by sign-up and login. The browser sends it by itself.
  Every route under `/me` and `/speak` needs it.
- Bodies are JSON. Recordings are form uploads with the file in a field named `audio`.
- **real** means the route works now. **stub** means it answers a realistic example
  and has no real logic yet (`# TODO(v2): stub` in `src/api.py`). Its URL and shape won't change
  when the real logic replaces it. Every route is real now.

## Errors

Every error has the same shape:

```json
{"error": "audio_too_short", "message": "the recording is 0.2 s; it needs 0.3 to 15 s", "seconds": 0.2}
```

`error` is the code to word in the app. `message` is plain English for developers. Three codes
add one field: `seconds` (`audio_too_short`, `audio_too_long`), `retry_after` in seconds
(`too_many_attempts`) and `phrase_id` (`phrase_exists`).

| code | status | meaning |
| - | - | - |
| `not_logged_in` | 401 | no session, or it expired: go to login |
| `not_found` | 404 | no such id, or it belongs to someone else |
| `consent_required` | 400 | `consent` must be true |
| `invalid_input` | 400, 422 | a field is missing, of the wrong type, or not allowed |
| `audio_too_short`, `audio_too_long` | 400 | phrase recordings take 0.3–15 s, a voice recording 5–30 s |
| `file_too_large` | 413 | upload over 10 MB |
| `bad_audio` | 400 | the file isn't audio we can read |
| `no_speech` | 422 | Prisma heard nothing; nothing is stored |
| `gnani_unreachable` | 502 | the speech service didn't answer: try again shortly |
| `gnani_rejected` | 502 | the speech service refused the request |
| `credit_limit_reached` | 429 | the speech service credits for this server are used up |
| `daily_cap_reached` | 429 | this account's speech service calls for today (`DAILY_CALL_CAP_PER_USER`, default 60) are used up; cached ones still work, and it resets at midnight UTC |
| `invite_required` | 403 | sign-up needs the invite code, and `invite_code` was missing or wrong (see `GET /config`) |
| `bad_login` | 401 | wrong email or password |
| `too_many_attempts` | 429 | 5 failed logins for this email, or 5 wrong invite codes from this IP, in 15 minutes: wait `retry_after` seconds |
| `email_taken` | 409 | an account with this email exists |
| `no_name`, `bad_email`, `short_password` | 400 | sign-up fields (password needs 8+ characters) |
| `phrase_exists` | 409 | another phrase already has this text |
| `no_voice` | 409 | `use_own_voice` needs a recorded voice |
| `not_owner` | 403 | only the server owner can see usage |
| `invalid_google_token` | 401 | invalid or expired Google ID token |
| `google_unreachable` | 502 | could not reach Google token verification services |
| `unverified_email` | 400 | Google account email is not verified |
| `server_error` | 500 | a bug on our side |

## Onboarding

### `GET /config` · real

No session needed. Whether sign-up needs an invite code: true when the server sets
`DEMO_INVITE_CODE` in `.env`. Ask for the code on the sign-up screen only when it is true.

```json
{"invite_required": false}
```

Errors: none.

### `GET /auth/google/config` · real

No session needed. Returns the Google OAuth Web Client ID for Google Identity Services (GIS). Empty string when unconfigured.

```json
{"client_id": ""}
```

Errors: none.

### `GET /health` · real

No session needed. Liveness health check confirming server responsiveness and database connectivity.

```json
{"status": "ok"}
```

Errors: none.

### `POST /auth/signup` · real

`{"name": "सुनीता", "email": "sunita@example.com", "password": "8 or more", "language": "hi", "consent": true}`.
`language` is the language the person speaks, `hi` or `en`. Add `"invite_code": "..."` when
`GET /config` says `invite_required`; otherwise it can be left out and is ignored. Sets the
session cookie and gives the account the default slot words and templates.

After 5 wrong invite codes from one IP in 15 minutes, sign-up from that IP answers
`too_many_attempts` until `retry_after` passes, even with the right code. Behind a proxy (like
Hugging Face's) the IP is the client's own when the server sets `TRUST_PROXY` (docs/DEPLOY.md).

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "hi",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": null, "caregiver_phone": null,
 "has_own_voice": false, "use_own_voice": false}
```

Errors: `invite_required`, `too_many_attempts`, `consent_required`, `no_name`, `bad_email`,
`short_password`, `email_taken`, `invalid_input`.

### `POST /auth/login` · real

`{"email": "sunita@example.com", "password": "..."}`. Sets the session cookie.

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "hi",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": "राहुल",
 "caregiver_phone": "919876543210", "has_own_voice": true, "use_own_voice": true}
```

Errors: `bad_login`, `too_many_attempts`, `invalid_input`.

### `POST /auth/google` · real

`{"id_token": "...", "language": "hi", "invite_code": "...", "consent": true}`. Authenticates an existing user or registers a new account using a Google Identity Services ID token. `invite_code` is required when `GET /config` says `invite_required` and the account does not exist yet. Sets the session cookie.

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "hi",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": "राहुल",
 "caregiver_phone": "919876543210", "has_own_voice": true, "use_own_voice": true}
```

Errors: `invalid_google_token`, `google_unreachable`, `unverified_email`, `invite_required`, `too_many_attempts`, `consent_required`, `email_taken`, `invalid_input`.

### `POST /auth/logout` · real

No inputs. Clears the cookie.

```json
{"ok": true}
```

Errors: none.

### `GET /auth/me` · real

The signed-in user. Use this on app start to see whether there is a session.

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "hi",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": "राहुल",
 "caregiver_phone": "919876543210", "has_own_voice": true, "use_own_voice": true}
```

Errors: `not_logged_in`.

### `POST /me/phrases/default` · real

No inputs. Adds the 51 everyday phrases in the user's language, and the default slot words and
templates for it, and returns the whole phrase list, as `GET /me/phrases` does. Text the user
already has is skipped, so after a language change this adds the new language's phrases and
building blocks next to the old ones.

```json
[{"id": 1, "text": "मदद चाहिए", "contexts": ["any"], "urgent": true, "enrolled": 0, "sample_count": 0, "last_used_at": null, "sources": []},
 {"id": 12, "text": "पानी चाहिए", "contexts": ["home", "hospital"], "urgent": false, "enrolled": 0, "sample_count": 0, "last_used_at": null, "sources": []}]
```

Errors: `not_logged_in`.

### `POST /me/enroll` · real

Form: `phrase_id`, `audio` (0.3–15 s). One enrollment recording of a phrase; 3 per phrase is
the goal. `hypothesis` is what Prisma heard. `source` is only for demo recordings loaded by
`scripts/load_demo.py` (`pilot`, `torgo` or `simulated`); the app leaves it out, and it comes
back `null`.

```json
{"sample_id": 301, "hypothesis": "paani chahiye", "phrase_id": 12, "slot_word_id": null, "template_id": null, "source": null}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`, `file_too_large`, `bad_audio`,
`audio_too_short`, `audio_too_long`, `no_speech`, `gnani_unreachable`, `gnani_rejected`,
`credit_limit_reached`, `daily_cap_reached`.

## Speak

### `POST /me/recognize` · real

Form: `audio` (0.3–15 s), optional `context`: `home`, `hospital` or `market`. The top 3
candidates, best first. `score` = `similarity` (0–100) + `context` (6 when the phrase is tagged
with the context sent) + `freq` (up to 4) + `time` (up to 3). A `composed` candidate is a
template × slot word that isn't a phrase yet: `phrase_id` is null and `template_id` and
`slot_word_id` say which. `urgent` ones deserve a louder button. `low_confidence` is true when
the best similarity is under 60.

```json
{"sample_id": 412, "hypothesis": "dawai chahie", "context": "hospital", "low_confidence": false,
 "candidates": [
  {"phrase_id": 14, "text": "दवाई चाहिए", "score": 92.4, "urgent": false, "composed": false,
   "parts": {"similarity": 84.6, "context": 6, "freq": 1.2, "time": 0.6}, "template_id": null, "slot_word_id": null},
  {"phrase_id": null, "text": "चाय चाहिए", "score": 71.3, "urgent": false, "composed": true,
   "parts": {"similarity": 71.3, "context": 0, "freq": 0, "time": 0}, "template_id": 1, "slot_word_id": 4},
  {"phrase_id": 2, "text": "दर्द हो रहा है", "score": 48.0, "urgent": true, "composed": false,
   "parts": {"similarity": 42.0, "context": 6, "freq": 0, "time": 0}, "template_id": null, "slot_word_id": null}]}
```

Errors: `not_logged_in`, `invalid_input`, `file_too_large`, `bad_audio`, `audio_too_short`,
`audio_too_long`, `no_speech`, `gnani_unreachable`, `gnani_rejected`, `credit_limit_reached`,
`daily_cap_reached`.

### `POST /me/confirm` · real

`{"sample_id": 412}` plus exactly one of `{"phrase_id": 14}`, `{"new_text": "चाय चाहिए"}`, or a
composed candidate's `{"template_id": 1, "slot_word_id": 4}` (which makes it a phrase). Says
what the recognition was, which teaches the matcher and logs one use.

```json
{"sample_id": 412, "phrase_id": 14, "text": "दवाई चाहिए", "urgent": false}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`.

### `POST /speak` · real

`{"text": "दवाई चाहिए"}`. Answers `audio/wav`: the user's own voice when `use_own_voice` is on,
else the stock voice for their language.

Errors: `not_logged_in`, `invalid_input`, `gnani_unreachable`, `gnani_rejected`, `credit_limit_reached`,
`daily_cap_reached`.

## Phrases

### `GET /me/phrases` · real

Every phrase. `enrolled` counts enrollment recordings, in any language; `sample_count` counts
enrollments and confirmed recognitions **in the user's current language only**, the ones the
matcher uses. After a language change, a phrase recorded only in the old language has
`sample_count` 0: it needs recording again to be recognized. `contexts` holds `home`,
`hospital`, `market` or `any`.

`sources` says where the phrase's demo recordings came from: `pilot` (a real person who
consented), `torgo` (the TORGO dysarthric speech corpus) or `simulated` (someone imitating
unclear speech). It is `[]` when every recording was made in the app, which is the case for
every normal account. Label a phrase with `simulated` in it, so nobody mistakes it for real
dysarthric speech.

```json
[{"id": 2, "text": "दर्द हो रहा है", "contexts": ["hospital"], "urgent": true, "enrolled": 3, "sample_count": 5, "last_used_at": "2026-10-18T07:40:00Z", "sources": []},
 {"id": 12, "text": "पानी चाहिए", "contexts": ["home", "hospital"], "urgent": false, "enrolled": 3, "sample_count": 9, "last_used_at": "2026-10-20T18:05:00Z", "sources": ["simulated"]},
 {"id": 40, "text": "बेटे को बुलाओ", "contexts": ["any"], "urgent": false, "enrolled": 0, "sample_count": 1, "last_used_at": null, "sources": []}]
```

Errors: `not_logged_in`.

### `POST /me/phrases` · real

`{"text": "खिड़की खोल दो"}`. Adding text that is already a phrase returns that phrase.

```json
{"id": 52, "text": "खिड़की खोल दो", "contexts": ["any"], "urgent": false}
```

Errors: `not_logged_in`, `invalid_input`.

### `PATCH /me/phrases/{phrase_id}` · real

Any of `{"text": "ठंडा पानी चाहिए", "contexts": ["home"], "urgent": false}`. `contexts: []`
means any.

```json
{"id": 12, "text": "ठंडा पानी चाहिए", "contexts": ["home"], "urgent": false}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`, `phrase_exists`.

### `DELETE /me/phrases/{phrase_id}` · real

Deletes the phrase with its recordings and uses.

```json
{"ok": true}
```

Errors: `not_logged_in`, `not_found`.

### `DELETE /me/samples/{sample_id}` · real

Deletes one recording (a `sample_id` from an enroll or recognize answer), like a bad take.

```json
{"ok": true}
```

Errors: `not_logged_in`, `not_found`.

### `GET /me/slot-words` · real

The words that fill a template's slot: `item`, `person` or `place`.

```json
[{"id": 1, "slot": "item", "text": "पानी", "enrolled": 3},
 {"id": 2, "slot": "item", "text": "दवाई", "enrolled": 2},
 {"id": 6, "slot": "person", "text": "बेटे", "enrolled": 0}]
```

Errors: `not_logged_in`.

### `POST /me/slot-words` · real

`{"slot": "item", "text": "दवाई"}`.

```json
{"id": 2, "slot": "item", "text": "दवाई", "enrolled": 0}
```

Errors: `not_logged_in`, `invalid_input`.

### `DELETE /me/slot-words/{slot_word_id}` · real

```json
{"ok": true}
```

Errors: `not_logged_in`, `not_found`.

### `POST /me/slot-words/{slot_word_id}/enroll` · real

Form: `audio` (0.3–15 s), the word said on its own. Optional `source`, as for `POST /me/enroll`.

```json
{"sample_id": 302, "hypothesis": "dawai", "phrase_id": null, "slot_word_id": 2, "template_id": null, "source": null}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`, `file_too_large`, `bad_audio`, `audio_too_short`,
`audio_too_long`, `no_speech`, `gnani_unreachable`, `gnani_rejected`, `credit_limit_reached`,
`daily_cap_reached`.

### `GET /me/templates` · real

Sentences with one slot at the start or end. `fixed_part` is the words recorded on their own.

```json
[{"id": 1, "text": "{item} चाहिए", "fixed_part": "चाहिए", "slot": "item", "enrolled": 3},
 {"id": 2, "text": "{person} को बुलाओ", "fixed_part": "को बुलाओ", "slot": "person", "enrolled": 1}]
```

Errors: `not_logged_in`.

### `POST /me/templates` · real

`{"text": "{place} ले चलो"}`: one `{item}`, `{person}` or `{place}`, at the start or end, and at
least one other word.

```json
{"id": 3, "text": "{place} ले चलो", "fixed_part": "ले चलो", "slot": "place", "enrolled": 0}
```

Errors: `not_logged_in`, `invalid_input`.

### `DELETE /me/templates/{template_id}` · real

```json
{"ok": true}
```

Errors: `not_logged_in`, `not_found`.

### `POST /me/templates/{template_id}/enroll` · real

Form: `audio` (0.3–15 s), the fixed part alone, like "चाहिए" for `{item} चाहिए`. Optional
`source`, as for `POST /me/enroll`.

```json
{"sample_id": 303, "hypothesis": "chahiye", "phrase_id": null, "slot_word_id": null, "template_id": 1, "source": null}
```

Errors: `not_logged_in`, `not_found`, `invalid_input`, `file_too_large`, `bad_audio`, `audio_too_short`,
`audio_too_long`, `no_speech`, `gnani_unreachable`, `gnani_rejected`, `credit_limit_reached`,
`daily_cap_reached`.

## Progress

### `GET /me/stats` · real

Totals, `top1_hit_rate` (how often the first candidate was right; null before any confirm), the
5 most used phrases, and `clear_without_help_by_week`: for each of the last 8 weeks (Monday
first, oldest first), how many confirmed recognitions Prisma already got right without the
personal layer. `rate` is null in a week with none. A rough trend, not a medical measure.

```json
{"phrases": 51, "samples": 164, "enroll_samples": 153, "recognitions": 14, "confirmed": 11,
 "top1_hits": 9, "top1_hit_rate": 0.818,
 "clear_without_help_by_week": [
  {"week_start": "2026-08-31", "confirmed": 0, "clear": 0, "rate": null},
  {"week_start": "2026-09-07", "confirmed": 0, "clear": 0, "rate": null},
  {"week_start": "2026-09-14", "confirmed": 0, "clear": 0, "rate": null},
  {"week_start": "2026-09-21", "confirmed": 0, "clear": 0, "rate": null},
  {"week_start": "2026-09-28", "confirmed": 2, "clear": 0, "rate": 0.0},
  {"week_start": "2026-10-05", "confirmed": 3, "clear": 1, "rate": 0.333},
  {"week_start": "2026-10-12", "confirmed": 4, "clear": 1, "rate": 0.25},
  {"week_start": "2026-10-19", "confirmed": 2, "clear": 1, "rate": 0.5}],
 "top_phrases": [{"phrase_id": 14, "text": "दवाई चाहिए", "uses": 5},
                 {"phrase_id": 12, "text": "पानी चाहिए", "uses": 4},
                 {"phrase_id": 2, "text": "दर्द हो रहा है", "uses": 2}]}
```

Errors: `not_logged_in`.

### `GET /me/usage` · real

Speech service calls by everyone, against the server's limit (`GNANI_CALL_LIMIT`). Each
account also has a daily cap of its own; this doesn't show it. Only for the owner
(`OWNER_EMAIL` in `.env`), so most screens won't need it.

```json
{"limit": 4000, "sent": 212, "remaining": 3788, "by_kind": {
  "stt": {"sent": 190, "cached": 640, "sent_audio_seconds": 412.5},
  "tts": {"sent": 21, "cached": 96, "sent_audio_seconds": 38.2},
  "clone": {"sent": 1, "cached": 0, "sent_audio_seconds": 0.0}}}
```

Errors: `not_logged_in`, `not_owner`.

## Settings

### `PATCH /me` · real

Any of `{"use_own_voice": true, "caregiver_name": "राहुल", "caregiver_phone": "+91 98765 43210", "language": "en"}`.
`null` or `""` clears a caregiver field. `caregiver_phone` comes back as digits with the
country code, ready for `https://wa.me/<phone>`. `use_own_voice: true` needs a recorded voice.

`language` (`hi` or `en`; anything else is `invalid_input`, and Hinglish is `hi`) is the
language the person speaks, not the app's display language. It is saved, and every new
recognition and stock-voice `/speak` uses it. Nothing is deleted: phrases, recordings, slot
words and templates all stay, but recordings in the old language stop counting for
recognition (see `sample_count` in `GET /me/phrases`) until the language is switched back. Call
`POST /me/phrases/default` afterwards to add the new language's everyday phrases.

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "en",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": "राहुल",
 "caregiver_phone": "919876543210", "has_own_voice": true, "use_own_voice": true}
```

Errors: `not_logged_in`, `invalid_input`, `no_voice`.

### `POST /me/voice` · real

Form: `audio` (5–30 s of clear speech), `consent` = `true`. Clones the user's voice; only the
voice's embedding is kept, never the recording. `use_own_voice` stays off until `PATCH /me`
turns it on.

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "hi",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": "राहुल",
 "caregiver_phone": "919876543210", "has_own_voice": true, "use_own_voice": false}
```

Errors: `not_logged_in`, `consent_required`, `invalid_input`, `file_too_large`, `bad_audio`,
`audio_too_short`, `audio_too_long`, `gnani_unreachable`, `gnani_rejected`, `credit_limit_reached`,
`daily_cap_reached`.

### `DELETE /me/voice` · real

Forgets the cloned voice and everything spoken in it; `use_own_voice` goes off.

```json
{"id": 7, "name": "सुनीता", "email": "sunita@example.com", "language": "hi",
 "consent_given_at": "2026-10-01T09:30:00Z", "caregiver_name": "राहुल",
 "caregiver_phone": "919876543210", "has_own_voice": false, "use_own_voice": false}
```

Errors: `not_logged_in`.

### `DELETE /me` · real

Deletes the account and everything it made: phrases, building blocks, recordings, the cloned
voice. Clears the cookie. Can't be undone, so ask first.

```json
{"ok": true}
```

Errors: `not_logged_in`.

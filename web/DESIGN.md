# Sunn design system

## Direction
Reference-led: the landing hero follows `web/reference/landing.png` (kept out of git) for layout,
spacing, type and feel, with Sunn's own copy. Everything else (sections below the hero, login,
signup, the app) uses the same visual language: an aurora dusk sky, a huge glowing wordmark, white pill buttons, outline pills, thin dividers and thin line icons.

Sunn = hindi "sun" (listen). The app's record button is still a sun, in the same saffron as
the dusk glowing up from the bottom of the sky, and the recognized phrase still resolves from blurry to sharp, because unclear speech
becomes clear. Accessibility is never traded for looks.

## Colors (the only colors allowed)
- night #030A18: text on the white pill, the gap in focus rings
- haze #8FB0D8: focus rings, the wordmark's glow
- mist #B4C3D8: secondary text, inactive controls
- foam #F2F6FB: primary text, the white pill, outline pill borders (at 40%), dividers (at 14%)
- saffron #F39A2B: in the UI, ONLY the app's sun and the recording state (never on the landing
  or auth pages). Also the dusk glow in the background
- Background only (aurora dusk, never on UI elements): sky #07071A (the base, the veil),
  teal #0F5E73, violet #5B3FD1, magenta #C2306B, and saffron above
Text must pass WCAG AA (4.5:1) against the BRIGHTEST background pixel that can pass behind it,
not the average.

## Type
- Anek Latin + Anek Devanagari everywhere, including the user's phrases (Tiro is gone). The
  stack is `'Anek Latin', 'Anek Devanagari'`, so each script gets its own cut of the same design
- Wordmark "Sunn": always Latin, in both languages (it is the name). Hero 96–208px, weight 500,
  tight tracking, a soft white glow (layered text-shadows in foam and haze)
- Headline 30–52px / 500. Section titles 32–48px / 500. Body 18px; secondary lines in mist
- Phrases: enroll 44px, top candidate 48px, other candidates 30px, all 500
- Devanagari line height 1.7 (`:lang(hi)`)

## Language
- One language on screen at a time, never stacked. EN / हिं toggle in the landing nav (between
  the links and Sign in), on login/signup, and in the app header
- Default hindi if the browser language starts with "hi", else english; remembered in
  localStorage; `<html lang>` follows it
- Every UI string goes through `t()` (`src/i18n/en.js`, `hi.js`, same keys). Hindi is written
  the way an educated person in UP writes: polite "-इए" forms in sentences, "-ें" on buttons,
  common English loanwords where people actually use them (ईमेल, पासवर्ड, साइन इन)
- The user's own phrases are data: shown exactly as stored, tagged with the user's language

## Components
- White pill (primary): foam, night text, fully rounded, 56px (64px in the app). The start
  button is [mic | label →]: lucide Mic, a thin vertical divider, the label, lucide ArrowRight,
  and a soft glow (`.pill-glow`). Form submits are [label →]
- Outline pill (secondary): transparent, 1px foam at 40%, fully rounded, 44px (64px hit area in
  the app). Used for Sign in / Open app, the language toggle, Log out, Play back, Cancel
- Text link: underlined, no box, for low-emphasis actions
- Thin dividers: 1px foam at 14%, vertical between columns (hero feature strip, who it's for,
  privacy) and horizontal between rows (steps, FAQ)
- Icons: lucide-react, line only, stroke 1.25–1.5. Arrows are allowed (ArrowRight on pills,
  arrows in the pipeline). No filled icons, no emoji
- Inputs: big (60px), a visible label above (never placeholder-only), hint and error under the
  field, the field with an error gets focus. Show/hide on passwords. Correct autocomplete
- Panels: a 1px divider-colored border and a dark translucent fill, only where content is a
  self-contained unit (the example panel, the pipeline steps)

## Background
- One `<SeaLight>` behind every page: fixed, full viewport, a raw WebGL shader called aurora
  dusk. Over the sky base, soft color fields drift like a liquid gradient: teal (large, slow)
  in the upper sky, violet across the upper middle bridging the halves, magenta in the lower
  sky, and saffron rising from the bottom edge like a sun coming up (it never reaches the
  headline). Cool on top, warm at the bottom, always
- The space is domain-warped by slow, low-frequency noise, so the edges between colors swirl
  like aurora curtains. Each field moves on its own 20–40s path inside its band, so the pattern
  never visibly repeats
- Soft blend, then a luminance ceiling (0.06 relative luminance, hue kept): nothing clips or
  goes neon, and mist text keeps 4.5:1 over the brightest pixel anywhere on screen, grain
  included, with no vignette or box behind text. ±3% film grain on top
- Half-resolution render, capped at 30fps, paused while the tab is hidden
- Intensity / veil per page (`src/App.jsx`, `SEA`): landing 1.0 / 0, login and signup 0.8 /
  0.25, speak 0.45 / 0.35, other app screens 0.55 / 0.45
- No WebGL: a still CSS gradient of the same fields. Reduced motion: one frozen frame

## Interaction
- Touch targets: 44px minimum on the landing, 64px in the app (enlarged hit areas where the
  visual pill is smaller)
- Visible focus everywhere: a 2px haze ring with a night gap
- Recording: tap to start, tap to stop, never press-and-hold. Auto-stop at 8s. Show seconds
- Errors say what happened and what to do, in the current language
- Anything that loops for more than 5 seconds (the example panel) has a pause button

## Motion
- Background: slow drift and swirl, never fast or flashy
- Sun at rest: slow 6s breathing. Recording: corona driven by real mic volume. Waiting: dims
  and brightens
- Resolve: the top phrase goes from blur(14px) + transparent to sharp in ~600ms; the example
  panel on the landing uses the same resolve
- Page changes: a quick crossfade via the view transitions API
- prefers-reduced-motion: frozen background, no breathing, no blur, instant changes, a static
  ring while recording, the example panel paused on a finished example

## Honesty
No invented statistics, testimonials or logos, no medical claims, no "real-time translation".
Example content is labelled "Example" / "उदाहरण". Features that aren't built yet say so
("Coming next" on own voice). Promises on the privacy section must stay true in the code.

## Banned
Glassmorphism or frosted panels, gradients as decoration on UI elements, ALL CAPS labels,
emoji, filled icons, colors outside the tokens, saffron in the UI outside the app's sun and
recording state, the background colors on UI elements, a second animated thing competing with the sun inside the app.

## Pages
- `/` landing: nav (wordmark · How it works · Who it's for · Privacy · EN/हिं · Sign in), hero
  (wordmark, headline, two lines, start pill, feature strip), how it works (+ example panel),
  your own voice, who it's for, under the hood (speech → Gnani Prisma → personal correction
  layer → Gnani Timbre), privacy, FAQ, closing line + start pill, footer
- `/login`, `/signup`: centered column, wordmark on top, labelled fields, white pill submit
- `/app/enroll`, `/app/speak`, `/app/progress`: header (wordmark → `/`, EN/हिं, user name,
  log out), bottom tabs with line icons, the sun

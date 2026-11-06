# Sunn design system

## Direction
Apple marketing pages and iOS: calm, precise, a lot of space, big confident type, content first.
The interface is monochrome and gets out of the way of the one thing that matters, the phrase.
Sunn = hindi "sun" (listen). Accessibility is never traded for looks.

Not allowed: gradients, background effects, glass or blur, glow on text, colored decoration,
heavy shadows, ALL CAPS labels, emoji, filled icons.

## Themes
Light, dark and automatic (follows the device, the default). The choice is changed from the
nav (a button that steps through them) and in Settings (Appearance), and remembered in
localStorage (`sunn.theme`, always inside try/catch). An inline script in `index.html` sets
`<html data-theme>` before the first paint, so there is no flash; `src/theme.js` keeps it, the
`color-scheme` and `<meta name="theme-color">` in step after that.

Every screen is one of two surfaces (`<html data-surface>`, set per route in `App.jsx`):
plain (Speak, Teach, the welcome guide, sign in, the landing page) or grouped (Phrases,
Progress, Settings: a tinted page with white cells, like iOS Settings).

## Colors (the only colors allowed)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | #FFFFFF | #000000 | plain pages |
| `--bg-grouped` | #F5F5F7 | #000000 | grouped pages, every other landing section |
| `--surface` | #F5F5F7 on plain, #FFFFFF on grouped | #1C1C1E | cards, list cells, fields |
| `--raised` | #FFFFFF | #2C2C2E | the toast in dark; never under secondary text |
| `--text` | #1D1D1F | #FFFFFF | all primary text and icons |
| `--text-2` | #6E6E73 | #8E8E93 | secondary text, inactive tabs |
| `--separator` | #D2D2D7 | rgba(255,255,255,0.12) | hairlines |
| `--fill` | rgba(118,118,128,0.12) | rgba(118,118,128,0.24) | secondary buttons, chips |
| `--primary` / `--on-primary` | #000000 / #FFFFFF | #FFFFFF / #000000 | primary buttons, the record button |
| `--red` | #FF3B30 | #FF453A | ONLY recording and urgent |
| `--green` | #34C759 | #30D158 | ONLY success |

Contrast (WCAG AA, checked for every pair):
- `--text` passes AAA everywhere. `--text-2` passes AA on `--bg`, `--bg-grouped` and
  `--surface` in both themes (lowest: 4.66 on #F5F5F7, 5.22 on #1C1C1E)
- `--text-2` is never put on `--fill` (4.4 in light) or on #2C2C2E (4.27 in dark). Text on a
  fill is always `--text`. That is why sheets in dark are black with a hairline edge and #1C1C1E
  cells (like every grouped page in dark), not #1C1C1E with #2C2C2E cells as in iOS
- Red and green are never text and never the only signal. Red is a fill (the record button
  while recording, 3.4:1 with its white icon) or a dot next to the word "Urgent" in `--text`.
  Green is a check icon next to the words that say the same thing
- Destructive actions (delete) stay monochrome: they are told apart by their words, their
  place at the end of a group and a confirmation sheet, not by color

## Type
- Latin: the system stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- Devanagari: "Noto Sans Devanagari" (Google Fonts, 400 to 700) first for `:lang(hi)`
- Headlines are large and tight: letter-spacing -0.02em, weight 700, line height 1.05 to 1.1.
  Never tight tracking on Devanagari (it breaks the headline bar), and Devanagari line height
  is 1.5 or more everywhere
- Scale (rem, so the text size setting scales all of it):
  display 3 to 6rem (landing hero) · title 2.25 to 4rem (landing sections) · large title
  2.125rem (each app screen's h1) · title 2 1.375rem · headline 1.125rem/600 · body 1.125rem
  (landing 1.1875 to 1.3125rem) · footnote 1rem, the smallest text there is except tab labels
  and chart axes (0.8125rem)
- Phrases: Teach 2.75rem, the top candidate 2.25 to 3.5rem, alternates 1.25rem, all 700/600
- Numbers in data (Progress, seconds) use tabular figures

## Shape and depth
- 20px radius for surfaces (cards, grouped lists, sheets), 12px for controls (buttons, chips,
  fields), fully round only for primary actions (the pill) and the record button
- Hairline separators (1px `--separator`, inset 16px from the leading edge in lists) instead of
  borders around things
- No shadows, except one very soft one under sheets in light mode
  (`0 -8px 40px rgba(0,0,0,0.08)`)

## Components
- Pill (primary, one per screen at most): `--primary` with `--on-primary`, fully round, 56px,
  optional leading icon. "Start speaking", Save, Create account, Say it
- Button (secondary): `--fill` with `--text`, 12px radius, 56px. Plain buttons (text only,
  `--text`, underlined on hover) for low-emphasis actions like "None of these"
- Chips (Speak's context, Phrases' filter): a radio group of 48px rounded rects, `--fill`;
  the selected one inverts to `--primary`. A row that scrolls sideways if it doesn't fit
- Grouped list: a `--surface` block with 20px radius, rows of 64px or more, hairlines between
  rows, an optional header line above and footnote below in `--text-2`. Rows end in a
  chevron (opens something), a switch, a checkmark (one choice of several) or a value
- Switch: iOS shape, 51×31, `--primary` when on, a `<button aria-pressed>` labelled by its row
- Fields: grouped like iOS: a visible label above the value inside the cell, the hint and error
  under the group, the field with an error gets focus. Show/hide on passwords. Correct
  autocomplete. Errors are `--text` with an alert icon, never red
- Sheet: a native `<dialog>` (focus is trapped, Escape closes, the page behind is inert) that
  slides up from the bottom on phones and sits centered on wide screens. 20px top corners, a
  scrim of black at 40% (60% dark). White in light; black with a hairline edge in dark. Every
  sheet has a Cancel or a close button
- Toast: a small `--surface-raised` capsule above the tab bar, a green check, 4 seconds
- Icons: lucide-react, stroke 1.5, 20px in rows, 24px in the tab bar. No filled icons
  (the stop square is the one exception: a filled square is what "stop" looks like)

## The record button
A circle, 128px (96px once there are results): `--primary` (black in light, white in dark)
with a mic in `--on-primary`, and its label underneath. While recording it turns `--red` with
a white stop square, and a soft red ring behind it grows and shrinks with the real microphone
level (`--level`, 0 to 1, set every frame by `useRecorder`). While Prisma works it dims slowly.
With reduced motion the ring is still and the dimming is a fixed 50%.

## App layout
- Header (64px): the wordmark, then presenter mode, EN / हिं, the theme button; on wide
  screens also the user's name and Log out (on phones, Log out is in Settings)
- Bottom tab bar on every app screen: icon + label, the active one in `--text`, the others in
  `--text-2`. 64px tall plus the safe area, solid background, a hairline on top
- Content: one centered column, 640px at most (Progress 880px)
- Speak: context chips at the top, the result in the middle, the record button low on the
  screen where a thumb reaches it. The recognized phrase is big, in its own card; the two
  alternates are rows in a grouped list; "None of these" opens a sheet to type the phrase
- Phrases: search, filter chips, then one grouped list. Each row shows the phrase, its
  recordings as three small dots (filled = saved), and its tags; tapping it opens a details
  sheet with Listen, Edit and Delete. No swiping
- Progress: big numbers in a grid with hairlines, the first-suggestion rate, the most used
  phrases, and the weekly chart: stacked bars in `--text` (understood directly) and `--text-2`
  (assisted), a 2px gap between the two, a hairline grid, the total above each bar, a legend
  and a table view
- Settings: iOS Settings. Grouped sections of rows: language you speak, app language,
  appearance, text size, accessibility switches, voice, caregiver, welcome guide, account

## Landing page
Apple product page: a sticky nav (wordmark · EN / हिं · theme · Sign in), then a hero with a
huge headline, one line under it and the pill. Then full-width sections, each making one point
with a big headline, a short line and a real visual built from the app's own components (not
a picture of a phone):
1. Speak: the record button, what the speech service heard, and the phrase resolving (the
   example, which plays on a loop with a pause button)
2. The correction loop: the candidates, "None of these" and the sheet with the typed phrase
3. Your own voice: the voice rows from Settings
4. Under the hood: speech → Gnani Prisma → the personal correction layer → Gnani Timbre
5. Privacy: the four promises as a grouped list
Then a closing line with the pill, and a minimal footer ("Built with Gnani Prisma and Gnani
Timbre"). Sections alternate `--bg` and `--bg-grouped` in light; in dark they are all black.

## Language
- Hindi headlines break between phrase units, never inside one (पाते हैं, एक आवाज़, जब चाहें):
  the units are joined with a no-break space (` `) in `hi.js`. Hindi is spelled हिंदी
- One language on screen at a time, never stacked. EN / हिं in the landing nav, on sign in and
  in the app header
- Default hindi if the browser language starts with "hi", else english; remembered in
  localStorage; `<html lang>` follows it
- Every UI string goes through `t()` (`src/i18n/en.js`, `hi.js`, same keys). Hindi is written
  the way an educated person in UP writes: polite "-इए" forms in sentences, "-ें" on buttons,
  common English loanwords where people actually use them (ईमेल, पासवर्ड, साइन इन)
- The user's own phrases are data: shown exactly as stored, tagged with the user's language

## Interaction
- Touch targets: 44px minimum on the landing page, 64px in the app (a hit area larger than
  the visual where the visual is smaller, never overlapping a neighbour's)
- Focus: a 2px ring in `--text` with a 2px gap, on everything, in both themes (inset inside
  lists and grouped cells so nothing clips it). High-contrast focus (Settings) makes it 4px
- Recording: tap to start, tap to stop, never press-and-hold. Auto-stop at 8s. Show seconds
- Errors say what happened and what to do, in the current language
- Anything that loops for more than 5 seconds (the landing example) has a pause button
- Text size (Settings): Large sets the root font size to 118.75%, and everything is in rem

## Motion
- Short and smooth: 200 to 350ms, ease-out (`cubic-bezier(0.22, 1, 0.36, 1)`), exits faster
  than entrances. Only transform and opacity are animated
- Sheets slide up. The top candidate scales in slightly (0.96 → 1) when it appears and again
  when it is chosen. The record ring follows the voice. Page changes crossfade (view
  transitions)
- `prefers-reduced-motion` or the app's own setting (`html.reduced-motion`): no animation and
  no transition anywhere, a still ring while recording, the landing example paused on a
  finished example

## Honesty
No invented statistics, testimonials or logos, no medical claims, no "real-time translation".
Example content is labelled "Example" / "उदाहरण". Features that aren't built yet say so, or
aren't mentioned. Promises on the privacy section must stay true in the code.

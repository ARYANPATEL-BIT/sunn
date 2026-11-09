# Sunn design system: the listening device

## Direction
Sunn is drawn as one calm physical object: a bedside listening unit in the family of a Braun
radio or a hospital call panel. It has a speaker grille, a dark readout window with a living
voice shape in it, a band selector and one orange push button. Every control is printed in
Hindi and English, small and stacked, the way Indian radios and appliances are labelled.
One type family. One accent, used like a hardware indicator light. It should read as an
industrial product, not a website.

Sunn = Hindi "sun" (listen). Accessibility is never traded for looks.

### Where the decisions come from
`ui-ux-pro-max` was run as `search.py "assistive communication accessibility tool"
--design-system -p Sunn --variance 4 --motion 5 --density 3`. Its look (Modern Dark cinema,
slate and green, video hero, ambient blobs, glass) is overruled by the brief. What was kept from
the skill is its accessibility and UX layer:

| Decision | Skill source |
|---|---|
| 7:1+ for body text where the palette allows, 4.5:1 floor, 3:1 for controls | `--domain style "Inclusive Design"`, quick reference §1 `color-contrast` |
| visible 2px focus ring with offset, never removed | `--domain ux "focus visible keyboard"` (Focus States, High) |
| tab order follows the visual order, skip nothing | same search (Keyboard Navigation) |
| every app target 64px, 8px+ between targets | `--domain ux "touch target size"` (44px floor, raised to 64 by the brief) |
| label above every field, error under its field with an icon, focus the first bad field | `--domain ux "form labels errors"` (Form Labels, Error Placement, Error Recovery) |
| `prefers-reduced-motion` plus the in-app setting turn off wobble, blur and spring | `--domain ux "reduced motion"` |
| no decorative infinite animation; the rest blob breathes only with motion allowed and stops in reduced motion | `--domain ux "continuous decorative animation"` (Continuous Animation: loaders only) |
| status of every wait is said in text, not only by the blob | `--domain ux "loading state feedback"` (Loading Indicators) |
| live region for listening / recognising / spoke, semantic landmarks | `--domain ux "status message screen reader"` |
| one rAF loop with cleanup on unmount and tab hide; mic level in a ref, not state | `--stack react` "Clean up effects", "Use refs for non-reactive values" |
| stable keys for candidate and phrase rows | `--stack react` "Use keys properly" |

The `frontend-design` plugin is in the marketplace but not installed here; its SKILL.md was read
and followed for the plan, critique and copy passes (one signature element, the blob; every
structural device encodes something true; copy written from the user's side).

## Hard rules
- No cream, beige, sand or warm off-white. Neutrals are cool aluminium and plastic greys.
- No coral, terracotta, peach or salmon. The only accent is signal orange.
- No serif, no italic display text.
- No gradients of any kind. The one `radial-gradient` is the grille's hole pattern.
- No glass, no glow except the blob's listening glow, no aurora, no noise, no blurred blobs.
- No emoji, no sparkle or star icons, no pill badges, no "AI" or "magic" in the interface.
- No centered gradient hero, no icon-in-a-square feature cards, no logo strip, no testimonials,
  no "10x" stats.
- No mono uppercase kickers above landing sections. Mono is for printed device labels and numbers.
- No cards inside cards. Landing sections are separated by space and hairlines. Only device
  objects are rounded panels.
- Copy: short plain sentences, like a product manual. No em dashes, no "not X, it's Y", no
  triplets of adjectives, no "seamless", "effortless", "empower", "unlock", "revolutionize".

## Themes
Light ("aluminium"), dark ("black device") and system (default). The nav button steps through
them, Settings lists all three, and the choice is kept in localStorage (`sunn.theme`, always in
try/catch). An inline script in `index.html` sets `<html data-theme>` before the first paint;
`src/theme.js` keeps it and `<meta name="theme-color">` in step after that.

## Colors (the only colors allowed)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--body` | #E3E4E6 | #0D0D0E | the device shell, page background |
| `--panel` | #F1F2F3 | #161718 | plates set into the shell, sheets, list groups |
| `--raised` | #FFFFFF | #1E1F21 | the selected band key, fields, toast |
| `--ink` | #111214 | #EBECEE | text, icons, primary button fill |
| `--ink-2` | #5C5F65 | #8C9096 | secondary text. Never inside a well in light |
| `--line` | #C8CACE | #2A2C2F | hairlines between rows. Decorative only |
| `--edge` | #76797F | #6B6F75 | the edge of a field, toggle or checkbox (3:1+) |
| `--hole` | #A7AAAF | #313337 | grille holes |
| `--well` | #D5D7DA | #09090A | recesses: band, push button seat, inputs on panels |
| `--screen` | #121315 | #060607 | the readout window, both themes dark |
| `--screen-text` | #EEF0F2 | #EEF0F2 | readout text, the blob while listening |
| `--screen-dim` | #868A90 | #868A90 | readout labels, raw heard text, the resting blob |
| `--signal` | #FF4A00 | #FF5A14 | push button, listening light, blob glow, active tab mark, urgent |
| `--on-signal` | #FFFFFF | #0D0D0E | the icon on the push button |
| `--signal-edge` | #B83500 | #A83A08 | the push button's rim and side wall |
| `--sos` | #E5352B | #E5352B | the urgent light in the readout (a shape, never text) |
| `--ok` | #2E9E5B | #2E9E5B | the success icon only; its text is ink |

Signal orange appears only on: the push button, the listening light, the blob's glow while
listening, the active-tab mark, and urgent markers. Nothing else is colored.

### Measured contrast (WCAG 2.x relative luminance)
| Pair | Light | Dark | Need |
|---|---|---|---|
| ink on body / panel / raised / well | 14.7 / 16.7 / 18.7 / 13.0 | 16.4 / 15.2 / 14.0 / 16.8 | 7 |
| ink-2 on body / panel / raised | 5.0 / 5.7 / 6.4 | 6.1 / 5.6 / 5.1 | 4.5 |
| ink-2 on well | 4.44, so not used there | 6.2 | 4.5 |
| screen-text on screen | 16.3 | 17.7 | 7 |
| screen-dim on screen | 5.4 | 5.8 | 4.5 |
| icon on signal (white / near-black) | 3.4 | 6.2 | 3 (graphic) |
| signal on well (button vs its seat) | 2.3, so the rim carries it | 6.4 | 3 |
| signal-edge rim on well / panel | 4.1 / 5.3 | n/a | 3 |
| signal light on screen | 5.5 | 5.8 | 3 |
| sos light on screen | 4.3 | 4.7 | 3 (shape) |
| ok icon on raised / panel | 3.4 / 3.0 | 4.8 / 5.3 | 3 (graphic) |
| edge on raised / panel / body / well | 4.4 / 3.9 / 3.4 / 3.0 | 3.3 / 3.6 / 3.9 / 3.9 | 3 |
| primary button text | 18.7 | 15.9 | 7 |

Focus is 2px solid ink with a 2px offset in both themes (orange focus fails on the light shell).
Inside the readout the ring turns screen-text. "High-contrast focus" in Settings makes it 4px.

## Type
One family, IBM Plex, from Google Fonts.
- IBM Plex Sans 400 / 500 / 600: interface and English.
- IBM Plex Sans Devanagari 400 to 700: Hindi, Marathi and every phrase. It is in every stack, so
  Devanagari glyphs fall through to it inside any element.
- Noto Sans Tamil, Telugu, Kannada, Malayalam, Gujarati, Bengali and Gurmukhi: only the active
  interface language's font is fetched (`src/i18n/index.jsx`). One `--font-<script>` stack per
  script; `:root:lang(xx)` picks it.
- IBM Plex Mono 500: printed device labels (uppercase, 0.08em tracking, 11px), step numbers,
  candidate ranks, recording counts, progress numbers. Never used for sentences.

| Role | Size | Weight | Tracking | Line height |
|---|---|---|---|---|
| Landing display | clamp(44px, 6.2vw, 92px) | 600 | -0.04em | 1.0 |
| Section title | clamp(32px, 3.6vw, 52px) | 600 | -0.035em | 1.05 |
| App title | 32px | 600 | -0.03em | 1.1 |
| Readout phrase | clamp(34px, 9vw, 44px) | 600 | 0 (Devanagari), -0.02em (Latin) | 1.35 |
| Body | 16px landing, 17px app | 400 | 0 | 1.5 |
| Printed label, Latin | 11px mono | 500 | 0.08em uppercase | 1.2 |
| Printed label, Devanagari | 13px | 500 | 0 | 1.35 |

Indian scripts never get negative tracking and never a line height under 1.35, so vowel signs
are not clipped (`:not(:lang(en))` resets tracking). Body text is 1.6 in Indian scripts and 1.7 in
Tamil, Telugu, Kannada and Malayalam, whose signs stack deeper. Long words shrink inside their
own key (tabs ellipsize, band keys take the width their longest word needs) and never spill into
the next one. Text size "Large" scales the root to 118.75%; everything is in rem.

## Shape, depth, texture
- Radii: device panels 28px, readout and wells 14px, buttons 10px, the push button round.
- Hairlines (1px `--line`) separate rows and landing sections. No boxes around sections.
- One soft drop shadow, `--shadow-device`, only under device objects (landing device, phone,
  the Speak device on wide screens, the sign-in panel, sheets). Nowhere else.
- The push button has a side wall: a solid 4px `--signal-edge` band under it, drawn as a hard
  edge, not a blur. Pressed, it moves 2px down and the wall shrinks to 2px.
- Grille: `radial-gradient(circle, var(--hole) 1.7px, transparent 2.1px)` on a 10px grid.
  The only radial-gradient allowed.

## Components (`src/ui/`)
- `Label`: a stacked bilingual printed label: the interface language on top (Hindi when the
  interface is English) and English mono under it. The language that is not the interface
  language is `aria-hidden`, so screen readers hear one.
- `Grille`: the speaker strip. Decorative.
- `Led`: the listening light. Off is a dark lens; on is signal orange with a 1px rim. The
  status text next to it carries the meaning.
- `Readout`: the dark window. Printed rows "सुना गया · HEARD" and "समझा गया · UNDERSTOOD", the raw
  Prisma text dim and very slightly blurred, the understood phrase large, the English meaning
  under it in English mode. The phrase resolves from blur to sharp. The Blob sits at the top.
- `Blob`: one SVG path of 9 points around a circle. Each radius is offset by the sum of three
  sines with their own speeds and phases; the closed curve is Catmull-Rom converted to cubic
  Béziers. One requestAnimationFrame loop runs only while listening, thinking or settling,
  and is cancelled on unmount and when the tab is hidden. Input is the recorder's own analyser
  level (no second mic stream), smoothed with a 60ms attack and 250ms release; missing = 0.
  - rest: a near circle in screen-dim, breathing 1 to 1.02 over 4s (CSS, motion allowed only)
  - listening: screen-text fill, wobble and size follow the level, an orange glow behind
  - thinking: amplitude eases down, slow wobble, 70% opacity
  - result: a spring back to the rest circle (slight overshoot, ~700ms), interruptible
  - error: snaps to rest, no glow
  - reduced motion: the path stays a circle; only its scale follows the level; no spring
  - `aria-hidden`; the light and the status text are the accessible signal
- `PushButton`: the orange key in its well, the listening light beside it and the label under
  it ("Tap to speak", "Tap to stop · 2 of 8 seconds", "Record again"). Class `record`.
- `Band`: a segmented selector in a well. Each key prints the interface language (Hindi under
  English) on top and English mono under it.
  Keys: सभी / ANY, घर / HOME, अस्पताल / HOSPITAL, बाज़ार / MARKET. The selected key is raised.
  ANY stays because Speak can send no context; the brief listed the other three.
- `RankedList`: alternates as rows on a panel, mono ranks 02 03 04, a chevron, hairlines.
- `Sheet`: a modal `<dialog>` bottom sheet on a panel, 28px top corners, 50% black scrim.
- `Toggle`: a switch. Off: well track with an edge. On: ink track. Never orange.
- `Row`, `Group`, `Choices`: settings rows on panels, 64px minimum, hairlines between.
- Icons: one inline stroke set (`src/ui/icons.jsx`), 1.5px, round caps and joins, Lucide
  geometry copied in. No filled icons, no icons in colored squares. `lucide-react` is removed.

## Motion
| Token | Value |
|---|---|
| `--fast` | 160ms |
| `--base` | 240ms |
| `--ease-out` | cubic-bezier(0.2, 0.7, 0.2, 1) |

Only the blob moves continuously, and only while it has something to show. Phrase resolve:
blur 8px to 0 and opacity 0 to 1 over 360ms after the spring. Candidate rows rise 6px with
a 40ms stagger. Reduced motion (system or Settings) removes wobble, blur, spring, breathing,
stagger and sheet slides; theme changes are instant.

## Screens
- Landing: left-aligned 12-column hero (the English headline, the interface language's under it, one
  lede, solid ink button, underlined link) and the device object on the right, cycling three
  made-up examples marked "EXAMPLE / उदाहरण" on the device, its blob driven by a fake level
  curve. Then a four-cell spec strip divided by hairlines, "The same object in your pocket"
  with three numbered steps beside a phone running the Speak screen, own voice, privacy, a
  hairline FAQ accordion and the footer.
- Speak: the screen is the device. Grille strip, readout with the blob, ranked alternates and
  "None of these", band, push button in its well, tab bar with bilingual printed labels and an
  orange mark on the active tab.
- Teach: the same readout (the phrase to say), blob and push button, so recording feels the
  same everywhere. Three meter segments and "1 / 3" in mono show recordings saved.
- Phrases, Progress, Settings: panels with hairline rows, mono labels and numbers, no
  decoration. Charts are solid ink and outlined bars with values, never gradients.
- Sign in, create account: a small device panel with a grille strip, labels above fields,
  errors under fields, one ink submit button.
- Interface text follows the language picker (ten languages, `src/i18n/languages.js`; the
  machine-translated ones say "beta" until a native speaker has read them). Only printed device
  labels are always bilingual.
- `LanguagePicker`: a key in a well printed with the current language's own name. It opens a
  listbox of all ten, each in its own script with the English name under it: a bottom sheet on
  phones, a small menu on wider screens. Arrow keys, Enter, Escape; focus returns to the key.

## Accessibility floor
- 64px targets in the app, 48px on the landing page; 8px or more between targets.
- Every tab stop shows a ring (checked by `e2e/keyboard.spec.js`).
- Each field has a visible label above it; hints and errors are linked with `aria-describedby`;
  the first invalid field takes focus.
- State is never only color: urgent has a word, success an icon and a word, the active tab
  `aria-current` and a heavier label, the listening light a status line.
- `aria-live="polite"` announces recording, recognising and what was spoken.

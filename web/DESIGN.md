# Sunn design system

## Concept
Sunn = hindi "sun" (listen) + english "sun". The app lives in a night sea: a soft cold light drifts slowly through dark water behind every screen. The record button is the sun, the only warm thing in that sea. Speaking makes the sun respond to the real voice volume. The recognized phrase resolves from blurry to sharp, because unclear speech becomes clear. That resolve is the ONE bold moment. Everything else is quiet, spacious and disciplined. Accessibility is never sacrificed for looks.

## Colors (the only colors allowed)
- abyss #000A14: base of the sea, darkest areas, veil color
- deep #06415A: deep teal in the light's outer halo
- tide #44A5BB: cyan body of the light; focus rings
- mist #B5DAE2: the bright core of the light; secondary text
- foam #EEF6F8: primary text, solid primary buttons (abyss text on them)
- genda #F2A93B: ONLY the sun, the active recording state, the active-tab dot
Text must pass WCAG AA (4.5:1) against the BRIGHTEST background pixel that can pass behind it, not the average.

## Type
- Tiro Devanagari Hindi: phrases only (what the user says). Recognized phrase 44px+, enroll phrase 40px+
- Anek Devanagari + Anek Latin: everything else. Body 20px, small english lines 15px in mist
- Devanagari line height 1.5+

## Background
- One <SeaLight> component behind every screen, fixed, full viewport
- intensity: landing 1.0, setup/enroll/progress 0.55, speak 0.4
- a veil of abyss at 0-50% opacity sits between the light and the content, plus a soft radial darkening behind the main text block, so text always passes contrast

## Banned
Cards with borders or shadows, glassmorphism or frosted panels, gradients used as decoration on ui elements, ALL CAPS labels, eyebrow labels above headings, emoji, "→" in buttons, identical rounded boxes everywhere, decorative icons, colors outside the tokens, a second animated thing competing with the sun.

## Interaction
- Buttons min 64px tall. Primary = solid foam with abyss text. Secondary = foam text with a thin underline, no box
- Visible focus ring (tide, 3px) on everything interactive
- Recording: tap to start, tap to stop, never press-and-hold. Auto-stop at 8s. Show seconds while recording
- Hindi first, small english underneath. Plain verbs. Errors say what happened and what to do

## Motion
- Background light: slow drift, never fast or flashy
- Sun at rest: genda disc ~55% of screen width on mobile, slow 6s breathing scale
- Sun while recording: corona/glow driven by real mic volume (Web Audio AnalyserNode). Never fake
- Waiting for recognition: the sun slowly dims and brightens
- Resolve: top phrase from blur(14px) + opacity 0 to sharp in ~600ms; the other 2 candidates fade in after
- Screen changes: quick crossfade via the view transitions api
- prefers-reduced-motion: background frozen on one frame, no breathing, no blur, instant fades, static ring only while recording

## Screens (all dark, over the sea)
Landing (/): full-strength light
  [ Sunn (huge, Anek Latin) ] / [ जो आप कहना चाहते हैं, वो सब समझें ] / [ speech that's hard to understand, made clear ] / [ शुरू करें · get started ]
  below: how it works (3 numbered steps: record a few phrases / speak / be heard clearly, in your own voice), one privacy line, footer: built with Gnani Prisma and Gnani Timbre
Setup: name field, consent checkbox + short hindi explanation, continue, load default phrases
Enroll: hairline progress at top / phrase huge in Tiro / 3 dots for 3 recordings / record, play, re-record, save
Speak: शायद (only if low confidence) / top phrase resolves huge / 2 more candidates as large rows / इनमें से कोई नहीं / the SUN in the lower half, in thumb reach
Progress: big numerals with a short label under each, on the sea, no boxes. A link to the own-voice screen.
Bottom bar: सीखें / बोलें / प्रगति with english under, active = small genda dot

# Sunn: challenge write-up

## Problem

Dysarthria, which comes with stroke, Parkinson's disease, cerebral palsy, ALS and other
conditions, makes speech slurred, slow or uneven. Family members often learn to understand the
person, but nurses, shopkeepers and strangers often can't, and general speech recognition,
built mostly on typical speech, often gets it wrong as well. The person is left pointing,
writing, or waiting for someone to translate everyday needs like water, medicine or "call my
son".

## Users

Dysarthric speakers of Hindi or Indian English, and the family members or caregivers who help
them set it up. It is a web app, so it runs on the phone they already have.

## Solution

Sunn is a personal phrasebook that understands its owner. The person records each of their
everyday phrases about three times (51 common ones come built in, in Hindi and English, and
they can add their own). Later they say a phrase the way they can, and Sunn shows the three
most likely phrases. They tap the right one, and Sunn says it aloud in a clear voice. Each
confirmation is kept as another example, so it learns from use.

The idea underneath is an error fingerprint. Sunn doesn't try to fix the speech recognizer or
train a new one. When Prisma mishears a particular person saying a particular phrase, it tends
to mishear it in a similar way each time, and that consistent wrong transcript is a usable
signature of the phrase in that person's voice. Sunn stores the transcripts from enrollment
and matches each new one against them by edit distance. Small boosts for the chosen place
(home, hospital, market) and for frequent phrases only settle near ties. Because nothing is trained, a phrase works after a few
recordings, and every person's data stays separate.

## Gnani technology used

- **Prisma speech to text** (`stt/v3`, `hi-IN` or `en-IN`, verbatim format) transcribes every
  enrollment and every attempt to speak. Its transcripts are the fingerprints, so Sunn is
  built on Prisma rather than around it.
- **Timbre text to speech** (`timbre-v2.5`, voices Nalini and Kaveri) says the chosen phrase.
- **Voice cloning** (voice clone embeddings and `vachana-vc-v1`), optional and with separate
  consent, lets the phrase be spoken in a voice like the person's own.

## Compared with Voiceitt and Google Project Relate

Both are established tools for non-standard speech, and both do more than Sunn in important
ways. This comparison comes from their public descriptions, not from testing them. Voiceitt
is a commercial product that adapts speech recognition to its user's own recordings and has
grown from phrases towards open dictation. Project Relate is Google's Android app, which
personalizes recognition after the user records a set of phrases, and was released for English
speakers. As far as their public material shows, neither is aimed at Hindi.

What Sunn does differently, as far as we know:

- **Hindi and Indian English first**, using Gnani's Indian-language models.
- **No model training.** Sunn treats a general recognizer's consistent mistakes as the
  personal signal, so setup is a few recordings per phrase, and a new phrase can be added at
  any time by recording it.
- **It speaks back**, in a stock voice or the person's own cloned voice, so it works face to
  face as well as on screen.

The trade-off is real: Sunn only recognizes phrases the person has enrolled. It can't take
dictation or understand a new sentence.

## Results

We have not yet measured the current version on real or demo recordings, so we report no
accuracy numbers. `scripts/evaluate.py` runs held-out recordings through the same matching and
reports raw Prisma exact-match accuracy, Sunn's top-1 and top-3 accuracy, the effect of the
place context, and accuracy with 1 to 3 enrollment recordings per phrase, split by where the
speech came from (a consenting pilot user, the TORGO corpus, or simulated speech).

<!-- Replace this section with the real numbers from results/eval_<account>.csv once it has
been run. -->

## What's next

- Record with real dysarthric Hindi speakers, with consent, and publish whatever the numbers
  turn out to be.
- Screens for templates and slot words, so "{item} चाहिए" covers many needs with few
  recordings.
- More Indian languages that Prisma and Timbre support.
- Feedback from speech therapists. Sunn is a communication aid, not a medical device.

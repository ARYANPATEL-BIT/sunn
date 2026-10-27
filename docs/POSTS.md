# Social Announcements and Sharing Drafts

Before posting, replace each placeholder in brackets with your real submission links and handles:
- `[teammate name/handle]`: Your teammate or co-contributor handle
- `[live demo link]`: Your deployed demo URL (e.g. `https://<user>-sunn.hf.space`)
- `[demo video link]`: 3-minute video link (YouTube, Loom, or Google Drive)
- `[writeup link]`: GitHub writeup or blog post URL
- `[github repository link]`: Public GitHub repo URL

Add accuracy numbers only once `scripts/evaluate.py` has produced real ones, with their source
(pilot, TORGO or simulated speech) and the number of recordings.

## LinkedIn Post

I built Sunn with [teammate name/handle] for Gnani AI's Great Indian AI Internship Challenge.

Sunn is a speech aid for people with dysarthria, the slurred or uneven speech that can come after a stroke or with Parkinson's disease or cerebral palsy. Family often understands them. Strangers, nurses and speech recognition, which is trained mostly on typical speech, often don't.

Sunn doesn't try to fix the speech recognizer. It works like this:
1. You record each everyday phrase about three times.
2. Gnani's Prisma transcribes each recording, often not quite right. The bet is that it gets a person's phrase wrong in a similar way each time.
3. Sunn keeps those transcripts as that phrase's fingerprint.
4. When you speak later, Sunn compares the new transcript with the fingerprints, shows the three closest phrases, and Gnani's Timbre says the one you pick out loud. If Timbre can't be reached, the browser's own speech synthesis says it instead.

It works in Hindi and Indian English, needs no model training, and only knows the phrases you've taught it. That's the honest limit. You can save a caregiver's number for a ready WhatsApp link, and delete your account and recordings at any time. We haven't measured its accuracy with real users yet.

Watch our 3-minute demo video: [demo video link]
Try the live application: [live demo link]
Technical writeup and code: [writeup link]

Thanks to the Gnani AI team for the Prisma and Timbre APIs that this is built on.

#GnaniAI #Accessibility #VoiceAI #Dysarthria #AIForGood #SpeechRecognition #Inclusion

## X (Twitter) Post (Option A: Single Post)

Built Sunn for the @Gnani_AI Great Indian AI Internship Challenge: a speech aid for dysarthria.

Prisma tends to mishear a person's phrase the same way each time, so Sunn uses those mistakes as fingerprints to find which of their phrases they meant, and Timbre says it. Hindi + Indian English.

Video: [demo video link]
Demo: [live demo link]

## X (Twitter) Post (Option B: 2-Post Thread)

1/2
Speech recognition often fails on dysarthria (slurred or uneven speech after a stroke, or with cerebral palsy).

With [teammate name/handle], we built Sunn for @Gnani_AI's Great Indian AI Internship Challenge: a personal phrase speech aid for Hindi & Indian English.

2/2
Sunn keeps a fingerprint of each phrase from Prisma's transcripts of a few recordings, matches new ones against it, and says the phrase you pick with Timbre (or the browser's voice as a fallback).

No model training, no medical claims, and it only knows the phrases you've taught it.

Demo video: [demo video link]
Try demo: [live demo link]
Code: [github repository link]

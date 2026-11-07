"""The real test set: our own recordings, transcribed by Prisma once each -> ml/data/real_test.csv.

Reads ml/data/real_audio/<intended_in_latin>_<take>.(wav|m4a|webm), e.g. paani_chahiye_1.m4a,
where the name is a starter-bank phrase's Latin form (ml/RECORDING.md lists them). Converts each
to 16 kHz mono wav with the backend's ffmpeg helper and transcribes it with the backend's cached
Prisma client (src/prisma.py), which caches by the wav's hash, so a recording is sent once.
Files already in real_test.csv are skipped, so a run can be resumed.

At most CAP calls are ever sent by this script (counted in ml/data/real_test_calls.txt, retries
included), and it stops on the first Gnani error (auth, quota, rejected or unreachable).

    uv run run_real_test.py --dry-run   # converts and checks the files, sends nothing
    uv run run_real_test.py
"""
import csv
import os
import re
import sys

import rank
from textnorm import SRC

CAP = 60
AUDIO = os.path.join(rank.HERE, "data", "real_audio")
WAV16 = os.path.join(rank.HERE, "data", "real_audio_16k")
OUT = os.path.join(rank.HERE, "data", "real_test.csv")
CALLS = os.path.join(rank.HERE, "data", "real_test_calls.txt")  # one line per call sent to Gnani
NAME = re.compile(r"^(.+)_(\d+)\.(wav|m4a|webm)$", re.IGNORECASE)
SECONDS = (0.3, 15)  # the app's limits for a phrase recording (PHRASE_SECONDS in src/api.py)

os.chdir(os.path.dirname(SRC))  # the backend's data/ (database, Prisma cache) and logs/ are relative to the repo
import audio  # noqa: E402
import db  # noqa: E402
import gnani  # noqa: E402
import gnani_mock  # noqa: E402
import prisma  # noqa: E402


def file_key(latin):
    return re.sub(r"[^a-z0-9]+", "_", latin.lower()).strip("_")


def how_to_record(keys):
    print(f"No recordings in {AUDIO}. To make the real test set (see ml/RECORDING.md):\n"
          "  - record starter-bank phrases in Hindi, spoken slowly, slurred, quietly or mumbled, one per file\n"
          "  - name each file <phrase in latin>_<take>.m4a|wav|webm, e.g. paani_chahiye_1.m4a\n"
          f"  - at most {CAP} files: each one costs a Prisma call\n"
          "valid names:", ", ".join(f"{k}_1" for k in keys))


def sent_calls():
    """Calls to Gnani so far, from the backend's own api_calls table."""
    return db.row("SELECT COUNT(*) AS n FROM api_calls WHERE cached = 0")["n"]


def main():
    dry_run = "--dry-run" in sys.argv
    bank = rank.starter_bank()
    intended = {file_key(latin): hindi for hindi, latin in zip(bank.hindi, bank.latin)}
    files = sorted(os.listdir(AUDIO)) if os.path.isdir(AUDIO) else []
    if not files:
        how_to_record(intended)
        return
    if gnani_mock.on():
        raise SystemExit("GNANI_MOCK is on: these would be mock transcripts, not Prisma's. Turn it off in .env")
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            done = {r["file"] for r in csv.DictReader(f)}
    used = sum(1 for _ in open(CALLS)) if os.path.exists(CALLS) else 0

    os.makedirs(WAV16, exist_ok=True)
    plan = []
    for name in files:
        match = NAME.match(name)
        if name in done:
            continue
        if not match or match[1].lower() not in intended:
            print(f"skipped {name}: not <starter phrase in latin>_<take>.wav|m4a|webm (see ml/RECORDING.md)")
            continue
        wav = os.path.join(WAV16, os.path.splitext(name)[0] + ".wav")
        audio.to_wav(os.path.join(AUDIO, name), wav)
        seconds = audio.seconds(wav)
        if seconds is None or not SECONDS[0] <= seconds <= SECONDS[1]:
            print(f"skipped {name}: {seconds} s is outside {SECONDS} s")
            continue
        with open(wav, "rb") as f:
            cached = os.path.exists(prisma.cache_path(f.read(), "hi"))
        plan.append((name, intended[match[1].lower()], wav, cached))
    to_send = sum(not cached for *_, cached in plan)
    print(f"{len(done)} already in {OUT}; {len(plan)} to transcribe: {len(plan) - to_send} cached, {to_send} to send."
          f" Calls used so far {used} of {CAP}.")
    if dry_run or not plan:
        return

    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as f, open(CALLS, "a") as calls:
        writer = csv.writer(f)
        if new:
            writer.writerow(["file", "intended", "heard"])
        for name, text, wav, cached in plan:
            if not cached and used >= CAP:
                print(f"stopped: the cap of {CAP} Gnani calls is used up; {name} and the rest are not sent")
                break
            before = sent_calls()
            try:
                heard = prisma.transcribe(wav, "hi")
            except gnani.GnaniError as e:
                print(f"stopped at {name}: Gnani error {e.code}: {e.detail}")
                break
            finally:
                for _ in range(sent_calls() - before):  # a retry after a timeout is a second call
                    calls.write(f"{name}\n")
                    used += 1
                calls.flush()
            writer.writerow([name, text, heard])
            f.flush()
            print(f"{name}: {'cached' if cached else 'sent'} -> {heard}")
    print(f"calls used {used} of {CAP}; results in {OUT}")


if __name__ == "__main__":
    main()

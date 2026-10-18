import argparse
import csv
import sys
from collections import defaultdict

from matcher import normalize, recognize

PREDICTIONS = "results/prisma_predictions.csv"
BANK_SIZE = 2  # repetitions per prompt used for enrollment; the rest are held out


def load_predictions(speaker=None):
    with open(PREDICTIONS, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if speaker is None or r["speaker"] == speaker]
    return sorted(rows, key=lambda r: r["wav_path"])


def split_repetitions(rows):
    """Per prompt with 3+ repetitions: first BANK_SIZE go to the bank, the rest are held out."""
    by_phrase = defaultdict(list)
    for r in rows:
        by_phrase[normalize(r["reference"])].append(r)

    bank, held_out = [], []
    for phrase, reps in by_phrase.items():
        if len(reps) <= BANK_SIZE:
            continue
        bank += [{"phrase": phrase, "prisma_hypothesis": normalize(r["hypothesis"])} for r in reps[:BANK_SIZE]]
        held_out += reps[BANK_SIZE:]
    return bank, held_out


def enroll(speaker):
    return split_repetitions(load_predictions(speaker))[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--hypothesis", help="a prisma hypothesis to correct; omit to print the bank")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which can't print Devanagari

    bank = enroll(args.speaker)
    if args.hypothesis is None:
        for entry in bank:
            print(f"{entry['phrase']!r:30} <- {entry['prisma_hypothesis']!r}")
        print(f"{len(bank)} bank entries, {len({e['phrase'] for e in bank})} phrases")
    else:
        for phrase, score in recognize(args.hypothesis, bank):
            print(f"{score:5.1f}  {phrase}")

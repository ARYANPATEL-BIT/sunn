import csv
import functools
import glob
import os
import re
import unicodedata
from collections import Counter

from indic_transliteration import sanscript
from rapidfuzz.distance import Levenshtein

import languages

# Usage priors, added to the 0-100 similarity. Kept small so similarity always dominates:
# together they lift a phrase by at most 13 points, enough to settle a near tie between
# phrases that sound alike, never enough to beat a clearly closer match.
CONTEXT_BOOST = 6  # the phrase is tagged with the context the user chose (home, hospital, market)
FREQ_BOOST = 4  # × how often the phrase is used, 0..1 (1 = the user's most used phrase)
TIME_BOOST = 3  # × the same, counting only uses in the current time-of-day bucket

LOW_CONFIDENCE = 60  # best similarity (0-100) below this is flagged low_confidence
CLEAR_SIMILARITY = 90  # a raw hypothesis this close to the confirmed phrase needed no correcting

CONTEXTS = ("home", "hospital", "market", "any")
SLOTS = ("item", "person", "place")
SLOT = re.compile(r"\{(" + "|".join(SLOTS) + r")\}")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Hand-written Latin spellings and English meanings of the starter phrases and more.
GLOSSARY = os.path.join(ROOT, "ml", "phrases.csv")
# The other languages' starter phrases, each line "phrase | Latin spelling | English meaning".
STARTERS = os.path.join(ROOT, "data", "default_phrases_*.txt")
# Letters sanscript doesn't know (Malayalam chillus, Tamil's alveolar na), spelled out first,
# and the è and ò it writes for short e and o.
SPELLED_OUT = str.maketrans({"ൺ": "ണ്", "ൻ": "ന്", "ർ": "ര്", "ൽ": "ല്", "ൾ": "ള്", "ൿ": "ക്", "ன": "ந"})
PLAIN = str.maketrans("èò", "eo")


def has_devanagari(text):
    return languages.in_script(text, languages.DEVANAGARI)


def normalize(text):
    # Every Indic script goes to ITRANS, so it compares fairly with romanized Prisma output.
    # Only letters, digits and combining marks survive: ITRANS writes the danda as
    # "|" and chandrabindu as ".N", so dropping the rest keeps words in one piece.
    # Devanagari (Hindi, Marathi) goes as it always has; in the other scripts, what sanscript
    # leaves untouched (a nukta) is dropped.
    for block, scheme in languages.SCRIPTS:
        if not languages.in_script(text, block):
            continue
        if scheme == sanscript.DEVANAGARI:
            text = sanscript.transliterate(text, scheme, sanscript.ITRANS)
        else:
            text = sanscript.transliterate(text.translate(SPELLED_OUT), scheme, sanscript.ITRANS).translate(PLAIN)
            text = "".join(c for c in text if not block[0] <= c <= block[1])
    text = "".join(c for c in text.lower() if c.isspace() or unicodedata.category(c)[0] in "LNM")
    return " ".join(text.split())


@functools.cache
def glossary():
    """Phrase in an Indic script -> (Latin spelling, English meaning), from GLOSSARY and the
    STARTERS files; {} without them."""
    found = {}
    try:
        with open(GLOSSARY, encoding="utf-8") as f:
            found = {unicodedata.normalize("NFC", r["hindi"]): (r["latin"], r["meaning_en"]) for r in csv.DictReader(f)}
    except OSError:
        pass
    for path in glob.glob(STARTERS):
        with open(path, encoding="utf-8") as f:
            for parts in (line.split("|") for line in f if not line.startswith("#")):
                if len(parts) == 3:
                    found.setdefault(unicodedata.normalize("NFC", parts[0].strip()), (parts[1].strip(), parts[2].strip()))
    return found


def gloss(text):
    """(Latin spelling, English meaning) of a phrase, for the reranker and the judge: the
    glossary's, else its normalized ITRANS spelling and no meaning. A Latin phrase is both."""
    if languages.script_of(text) is None:
        return text, text
    return glossary().get(unicodedata.normalize("NFC", text), (normalize(text), ""))


def similarity(a, b):
    """0-100, higher = closer, after normalizing both."""
    return 100 * Levenshtein.normalized_similarity(normalize(a), normalize(b))


def recognize(hypothesis, bank, k=3):
    """Top k phrases as (phrase, score), score 0-100, higher = closer match.

    bank is a list of {"phrase": ..., "prisma_hypothesis": ...}; a phrase with
    several samples scores as its best one.
    """
    hyp = normalize(hypothesis)
    best = {}
    for entry in bank:
        score = 100 * Levenshtein.normalized_similarity(hyp, normalize(entry["prisma_hypothesis"]))
        best[entry["phrase"]] = max(score, best.get(entry["phrase"], 0.0))
    return sorted(best.items(), key=lambda item: item[1], reverse=True)[:k]


def time_bucket(when):
    """morning (5-12h), afternoon (12-17h), evening (17-21h) or night, in the server's local time."""
    hour = when.astimezone().hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def usage_priors(uses, bucket):
    """uses is [(key, datetime)], one per confirmed use. Returns {key: (freq, time)}: the key's
    uses as a share of the most used key's, overall and within bucket, each 0..1."""
    overall = Counter(key for key, _ in uses)
    in_bucket = Counter(key for key, when in uses if time_bucket(when) == bucket)
    top, top_in_bucket = max(overall.values(), default=0), max(in_bucket.values(), default=0)
    return {key: (overall[key] / top, in_bucket[key] / top_in_bucket if top_in_bucket else 0.0)
            for key in overall}


def rank(hypothesis, candidates, context=None, priors=None, k=3):
    """Top k candidates for a hypothesis, best first.

    Each candidate is a dict with "key" (for priors), "fingerprints" (Prisma hypotheses
    it was heard as; it scores as its closest one) and "contexts". Candidates without a
    fingerprint are skipped. Returns copies with "score" and its "parts": similarity,
    context, freq and time, which add up to score.
    """
    hyp, priors = normalize(hypothesis), priors or {}
    ranked = []
    for candidate in candidates:
        if not candidate["fingerprints"]:
            continue
        sim = max(100 * Levenshtein.normalized_similarity(hyp, normalize(f)) for f in candidate["fingerprints"])
        freq, time = priors.get(candidate["key"], (0.0, 0.0))
        parts = {
            "similarity": round(sim, 1),
            "context": CONTEXT_BOOST if context in candidate["contexts"] and context != "any" else 0,
            "freq": round(FREQ_BOOST * freq, 1),
            "time": round(TIME_BOOST * time, 1),
        }
        ranked.append({**candidate, "score": round(sum(parts.values()), 1), "parts": parts})
    return sorted(ranked, key=lambda c: c["score"], reverse=True)[:k]


def parse_template(text):
    """(slot, fixed_part, slot_first) for a template like "{item} चाहिए" or "Call {person}",
    or None unless it has exactly one slot, at its start or end, and some fixed words."""
    text = " ".join(text.split())
    slots = SLOT.findall(text)
    fixed = SLOT.sub("", text).strip()
    if len(slots) != 1 or not fixed or not (text.startswith("{") or text.endswith("}")):
        return None
    return slots[0], fixed, text.startswith("{")


def compose(slot_first, word, fixed):
    """Join a slot word and a fixed part in the template's word order. Used for the phrase
    text and, with their Prisma hypotheses, for the composed fingerprint."""
    return f"{word} {fixed}" if slot_first else f"{fixed} {word}"

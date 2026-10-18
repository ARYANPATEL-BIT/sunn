import unicodedata

from indic_transliteration import sanscript
from rapidfuzz.distance import Levenshtein

LOW_CONFIDENCE = 60  # best score (0-100) below this is flagged low_confidence


def has_devanagari(text):
    return any("ऀ" <= c <= "ॿ" for c in text)


def normalize(text):
    # Devanagari goes to ITRANS so it compares fairly with romanized Prisma output.
    # Only letters, digits and combining marks survive: ITRANS writes the danda as
    # "|" and chandrabindu as ".N", so dropping the rest keeps words in one piece.
    if has_devanagari(text):
        text = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    text = "".join(c for c in text.lower() if c.isspace() or unicodedata.category(c)[0] in "LNM")
    return " ".join(text.split())


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

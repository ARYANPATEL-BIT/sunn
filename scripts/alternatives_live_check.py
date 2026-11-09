"""Live check for Trainings Alternatives (docs/TRAININGS_CONTRACT.md).
Runs the 5 test sentences against the library and Groq assistant (when LLM_ENABLED=1 and LLM_API_KEY is set).
Prints a markdown table.

Usage:
    uv run scripts/alternatives_live_check.py
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import trainings
import matcher

TRICKY = ["p", "d"]
SENTENCES = [
    ("पानी चाहिए", "hi"),
    ("I need water", "en"),
    ("दर्द हो रहा है", "hi"),
    ("बेटे को बुलाओ", "hi"),
    ("कृपया खिड़की खोल दीजिए", "hi"),
]


def run_sentence(text: str, lang: str):
    norm_input = matcher.normalize(text)
    tricky_set = set(TRICKY)

    # 1. Check library
    best_meaning = None
    best_variant = None
    best_sim = 0.0

    for m in trainings.TAGGED_ALTERNATIVES:
        for v in m["variants"]:
            if norm_input == v["norm"] or norm_input == v["norm_latin"]:
                best_meaning = m
                best_variant = v
                best_sim = 1.0
                break
        if best_meaning:
            break

    if not best_meaning:
        for m in trainings.TAGGED_ALTERNATIVES:
            for v in m["variants"]:
                sim = max(
                    trainings.Levenshtein.normalized_similarity(norm_input, v["norm"]),
                    trainings.Levenshtein.normalized_similarity(norm_input, v["norm_latin"])
                )
                if sim > best_sim:
                    best_sim = sim
                    best_meaning = m
                    best_variant = v

    if best_meaning and best_sim >= 0.85:
        other_variants = [v for v in best_meaning["variants"] if v["text"] != text and v["norm"] != norm_input]
        if not other_variants:
            other_variants = best_meaning["variants"]

        def rank_key(v):
            return (len(v["sounds"] & tricky_set), len(v["text"]), v["index"])

        sorted_variants = sorted(other_variants, key=rank_key)
        results = []
        for v in sorted_variants[:4]:
            avoids = sorted([s for s in TRICKY if s not in v["sounds"]])
            results.append((v["text"], avoids, "library"))
        return results, best_meaning["meaning_en"]

    # 2. Assistant fallback via Groq
    if trainings.llm_judge.enabled():
        res = trainings.call_groq_alternatives(text, lang, TRICKY)
        if res and res.alternatives:
            return [(a.text, sorted(a.avoids), a.source) for a in res.alternatives], res.meaning_en

    # 3. Closest library match fallback (similarity >= 0.60)
    if best_meaning and best_sim >= 0.60:
        other_variants = [v for v in best_meaning["variants"] if v["text"] != text and v["norm"] != norm_input]
        if not other_variants:
            other_variants = best_meaning["variants"]

        def rank_key(v):
            return (len(v["sounds"] & tricky_set), len(v["text"]), v["index"])

        sorted_variants = sorted(other_variants, key=rank_key)
        results = []
        for v in sorted_variants[:4]:
            avoids = sorted([s for s in TRICKY if s not in v["sounds"]])
            results.append((v["text"], avoids, "library"))
        return results, best_meaning["meaning_en"]

    return [], "none"


def main():
    print(f"Tricky sounds assumed: {TRICKY}\n")
    print("| Input | Tricky Sounds | Returned Alternatives | Avoids | Source |")
    print("|---|---|---|---|---|")
    for text, lang in SENTENCES:
        alts, meaning_en = run_sentence(text, lang)
        if not alts:
            print(f"| {text} ({lang}) | {', '.join(TRICKY)} | (no alternative found) | - | - |")
        else:
            for alt_text, avoids, source in alts:
                avoids_str = ", ".join(avoids) if avoids else "none"
                print(f"| {text} ({lang}) | {', '.join(TRICKY)} | {alt_text} | {avoids_str} | {source} |")


if __name__ == "__main__":
    main()

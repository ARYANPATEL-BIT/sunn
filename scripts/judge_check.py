"""Hand-written Prisma-style hypotheses through the matcher and the judge (LLM_MODE=always), text
in: no Prisma, no Timbre, no database. The candidates are the Hindi starter phrases, each with its
own Devanagari and Latin text as its fingerprints, standing in for enrolled recordings, and its
place from ml/phrases.csv. At most one LLM call per line; prints a table.

    uv run scripts/judge_check.py
"""
import csv
import os
import sys
import time

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import llm_judge  # noqa: E402
import matcher  # noqa: E402

LINES = [("baani chaiye", "home"), ("darad ho ra", "hospital"), ("dabai do", "hospital"), ("bete ko bula", "home"),
         ("thand lag rai", "home"), ("pet me dard", "hospital"), ("bathroo jana", "home"), ("maa ko bulao", "home"),
         ("dawai kab", "hospital"), ("bahut tand", "home")]


def starter_candidates():
    with open(matcher.GLOSSARY, encoding="utf-8") as f:
        places = {r["hindi"]: r["place"] for r in csv.DictReader(f)}
    with open(os.path.join(ROOT, "data", "default_phrases_hi.txt"), encoding="utf-8") as f:
        texts = [" ".join(line.split()) for line in f if line.strip() and not line.startswith("#")]
    return [{"key": i, "phrase_id": i, "text": text, "contexts": [places.get(text, "any")], "urgent": False,
             "fingerprints": [text, matcher.gloss(text)[0]]} for i, text in enumerate(texts, 1)]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(os.path.join(ROOT, ".env"))
    os.environ.update(LLM_ENABLED="1", LLM_MODE="always", LLM_RATE_PER_MIN=str(len(LINES)))
    responses, post = [], llm_judge.httpx.post

    def counted(*args, **kwargs):  # the cap, and each response for its status, finish reason and tokens
        if len(responses) >= len(LINES):
            raise RuntimeError("more LLM calls than lines")
        responses.append(None)  # counted even when the call raises
        responses[-1] = post(*args, **kwargs)
        return responses[-1]

    llm_judge.httpx.post = counted
    candidates = starter_candidates()
    print(f"model {os.environ.get('LLM_MODEL')}, reasoning_effort {os.environ.get('LLM_REASONING_EFFORT') or '-'}\n")
    print("| heard | place | matcher top 3 (score) | judge choice | confidence | reason | used | match ms | llm ms | tokens |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for heard, place in LINES:
        started = time.monotonic()
        ranked = matcher.rank(heard, candidates, place, None, k=llm_judge.TOP_K)
        match_ms = round(1000 * (time.monotonic() - started))
        sent, started = len(responses), time.monotonic()
        result = llm_judge.judge(heard, ranked, place, [], {}, "judge-check")
        llm_ms = round(1000 * (time.monotonic() - started))
        response = responses[-1] if len(responses) > sent else None
        tokens = "-"
        if response is not None and response.status_code == 200:
            body = response.json()
            tokens = f"{body['usage']['completion_tokens']} ({body['choices'][0]['finish_reason']})"
        elif response is not None:
            tokens = f"HTTP {response.status_code} {response.json().get('error', {}).get('code', '')}"
            if len(responses) == 1 and 400 <= response.status_code < 500 and response.status_code != 429:
                sys.exit(f"the first call was refused ({tokens}): {response.json().get('error', {}).get('message')}")
        top3 = ", ".join(f"{c['text']} ({c['score']:.0f})" for c in ranked[:3])
        names = {llm_judge.candidate_id(c): c["text"] for c in ranked}
        verdict = result["verdict"] or {"choice": "(no valid answer)", "confidence": "-", "reason": "-"}
        used = "yes" if result["chosen_by"] == "judge" else "no"
        print(f"| {heard} | {place} | {top3} | {names.get(verdict['choice'], verdict['choice'])} | "
              f"{verdict['confidence']} | {verdict['reason']} | {used} | {match_ms} | {llm_ms} | {tokens} |")
    print(f"\n{len(responses)} LLM calls, 0 Prisma calls")


if __name__ == "__main__":
    main()

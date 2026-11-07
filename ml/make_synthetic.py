"""Synthetic Prisma mishearings of every phrase in phrases.csv -> ml/data/synthetic.csv.

Each rule below is one kind of mistake an STT makes on unclear Hindi speech, written for both
the Devanagari and the Latin form of a word. A variant gets 1 edit (mild), 2-3 (moderate) or
4-6 (severe), and is written mostly in Devanagari, sometimes in Latin or a mix, like Prisma.
The split is by phrase (80/10/10): test phrases never appear in training.
"""
import os
import random
import re
import unicodedata

import pandas as pd

from textnorm import has_devanagari, normalize

SEED = 7
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "synthetic.csv")
VARIANTS = {"clean": 1, "mild": 7, "moderate": 7, "severe": 5}  # 20 per phrase, 5 % clean
EDITS = {"clean": (0, 0), "mild": (1, 1), "moderate": (2, 3), "severe": (4, 6)}
SCRIPTS = {"devanagari": 0.7, "latin": 0.2, "mixed": 0.1}

# A word is split into units, so a rule swaps whole sounds: "chh" or "aa" in Latin, a letter
# with its nukta ("ड़") in Devanagari.
LATIN_UNIT = re.compile(r"chh|ch|kh|gh|th|dh|ph|bh|jh|sh|aa|ii|ee|uu|oo|.")
DEV_UNIT = re.compile(".़?")
LATIN_VOWELS = {"a", "e", "i", "o", "u", "aa", "ii", "ee", "uu", "oo"}
CONSONANTS = {chr(c) for c in range(0x915, 0x93A)}
MATRAS = {chr(c) for c in range(0x93E, 0x94D)}
HALANT, NASALS = "्", {"ँ", "ं"}
INDEPENDENT = dict(zip("ािीुूेैोौॉ", "आइईउऊएऐओऔऑ"))  # vowel sign -> the vowel on its own


def nfc(text):
    return unicodedata.normalize("NFC", text)


def pairs(*items):
    """pairs("p b", "t d") -> {"p": "b", "b": "p", "t": "d", "d": "t"}"""
    mapping = {}
    for item in items:
        a, b = nfc(item).split()
        mapping[a], mapping[b] = b, a
    return mapping


def is_consonant(unit, script):
    if script == "latin":
        return unit.isalpha() and unit not in LATIN_VOWELS
    return unit[0] in CONSONANTS


def is_vowel(unit, script):
    return unit in LATIN_VOWELS if script == "latin" else not is_consonant(unit, script) and unit not in NASALS


def swap(units, mapping, rng, where=lambda i: True):
    """Replace one unit found in mapping (a value of "" deletes it), or None if none is found."""
    spots = [i for i, u in enumerate(units) if u in mapping and where(i)]
    if not spots:
        return None
    i = rng.choice(spots)
    return units[:i] + [mapping[units[i]]] + units[i + 1:]


def table_rule(name, tables):
    """A rule that swaps one unit using the table for the word's script."""
    def rule(units, script, rng):
        return swap(units, tables.get(script, {}), rng)
    rule.__name__ = name
    return rule


# --- sound rules: one word's units in, changed units out (None if the rule doesn't fit) ---

voicing = table_rule("voicing", {
    "latin": pairs("p b", "t d", "k g", "ch j"),
    "dev": pairs("क ग", "प ब", "त द", "ट ड", "च ज")})
aspiration = table_rule("aspiration", {
    "latin": pairs("ph p", "bh b", "kh k", "gh g", "th t", "dh d", "chh ch", "jh j"),
    "dev": pairs("ख क", "घ ग", "थ त", "ध द", "फ प", "भ ब", "छ च", "झ ज", "ठ ट", "ढ ड")})
retroflex = table_rule("retroflex", {"dev": pairs("ट त", "ठ थ", "ड द", "ढ ध", "ण न")})  # Latin writes both as t, d, n
vowel_length = table_rule("vowel_length", {
    "latin": {"aa": "a", "a": "aa", "ii": "i", "ee": "i", "i": "ee", "uu": "u", "oo": "u", "u": "oo"},
    "dev": {"ा": "", **pairs("ी ि", "ू ु", "आ अ", "ई इ", "ऊ उ")}})
e_i = table_rule("e_i", {"latin": pairs("e i"), "dev": pairs("े ि", "ए इ")})
o_u = table_rule("o_u", {"latin": pairs("o u"), "dev": pairs("ो ु", "ओ उ")})
sh_s = table_rule("sh_s", {"latin": pairs("sh s"), "dev": {"श": "स", "स": "श", "ष": "स"}})
r_l = table_rule("r_l", {"latin": pairs("r l"), "dev": pairs("र ल")})
flap_r = table_rule("flap_r", {"dev": {"ड़": "र", "ढ़": "र", "र": "ड़"}})  # ड़ heard as र and back


def nasal_dropped(units, script, rng):
    if script == "dev":
        return swap(units, {"ं": "", "ँ": ""}, rng)
    return swap(units, {"n": ""}, rng, lambda i: i > 0 and units[i - 1] in LATIN_VOWELS
                and (i == len(units) - 1 or is_consonant(units[i + 1], script)))


def n_m_at_end(units, script, rng):
    return swap(units, pairs("n m") if script == "latin" else pairs("न म"), rng, lambda i: i == len(units) - 1)


def r_dropped(units, script, rng):
    if script == "latin":
        return swap(units, {"r": ""}, rng, lambda i: i > 0)
    spots = [i for i, u in enumerate(units) if u == "र" and i > 0 and (i + 1 == len(units) or units[i + 1] not in MATRAS)]
    if not spots:
        return None
    i = rng.choice(spots)
    start = i - 1 if units[i - 1] == HALANT else i  # प्र -> प
    end = i + 2 if i + 1 < len(units) and units[i + 1] == HALANT else i + 1  # र्द -> द
    return units[:start] + units[end:]


def schwa(units, script, rng):
    """Drop the short a between two consonants (garam -> garm) or add one (kamra -> kamara)."""
    inner = range(1, len(units) - 1)
    if script == "latin":
        drop = [i for i in inner if units[i] == "a" and is_consonant(units[i - 1], script) and is_consonant(units[i + 1], script)]
        add = [i for i in inner if is_consonant(units[i - 1], script) and is_consonant(units[i], script)]
        options = [("drop", i) for i in drop] + [("add", i) for i in add]
        if not options:
            return None
        kind, i = rng.choice(options)
        return units[:i] + units[i + 1:] if kind == "drop" else units[:i] + ["a"] + units[i:]
    drop = [i for i in range(len(units) - 1) if is_consonant(units[i], script) and is_consonant(units[i + 1], script) and i > 0]
    add = [i for i in inner if units[i] == HALANT and is_consonant(units[i + 1], script)]
    options = [("drop", i) for i in drop] + [("add", i) for i in add]
    if not options:
        return None
    kind, i = rng.choice(options)
    return units[:i + 1] + [HALANT] + units[i + 1:] if kind == "drop" else units[:i] + units[i + 1:]


def ending_chopped(units, script, rng):
    """chahiye -> chahi, बुलाओ -> बुला, दर्द -> दर"""
    if len(units) < 3:
        return None
    units = units[:-1]
    while units and units[-1] in ({"y", "h", "w"} if script == "latin" else {HALANT}):
        units = units[:-1]
    return units if len(units) >= 2 else None


def h_dropped(units, script, rng):
    """chahiye -> chaiye, चाहिए -> चाइए"""
    if script == "latin":
        return swap(units, {"h": ""}, rng, lambda i: i > 0)
    spots = [i for i, u in enumerate(units) if u == "ह" and i > 0 and (i + 1 == len(units) or units[i + 1] != HALANT)]
    if not spots:
        return None
    i = rng.choice(spots)
    if i + 1 < len(units) and units[i + 1] in INDEPENDENT and not is_consonant(units[i - 1], script):
        return units[:i] + [INDEPENDENT[units[i + 1]]] + units[i + 2:]  # चाहिए -> चाइए
    return units[:i] + units[i + 1:]  # कहाँ -> काँ


def first_consonant_dropped(units, script, rng):
    """paani -> aani, पानी -> आनी"""
    if len(units) < 3 or not is_consonant(units[0], script):
        return None
    if script == "latin":
        return units[1:]
    if units[1] in INDEPENDENT:
        return [INDEPENDENT[units[1]]] + units[2:]
    if units[1] == HALANT:
        return units[2:]
    return ["अ"] + units[1:]


SOUND_RULES = {voicing: 3, aspiration: 3, retroflex: 2, vowel_length: 3, e_i: 2, o_u: 2, schwa: 2,
               nasal_dropped: 2, n_m_at_end: 1, sh_s: 2, r_dropped: 1, r_l: 1, flap_r: 1,
               ending_chopped: 2, h_dropped: 1, first_consonant_dropped: 1}

# --- word rules: the list of (word, script) in, a changed list out ---

FILLERS = {"dev": ["हाँ", "उम", "अ"], "latin": ["haan", "um", "uh"]}
# Real words a misheard word turns into: (Devanagari, Latin) -> similar real words.
REAL_WORDS = {
    ("पानी", "paani"): [("बानी", "baani"), ("वाणी", "vaani")],
    ("दवाई", "dawai"): [("दबाई", "dabai"), ("कमाई", "kamai")],
    ("दर्द", "dard"): [("गर्द", "gard"), ("सर्द", "sard")],
    ("खाना", "khana"): [("काना", "kana"), ("गाना", "gaana")],
    ("चाय", "chai"): [("चार", "char"), ("गाय", "gaay")],
    ("दूध", "doodh"): [("दूर", "door"), ("दूत", "doot")],
    ("माँ", "maa"): [("मान", "maan"), ("मार", "maar")],
    ("पापा", "papa"): [("बाबा", "baba")],
    ("बेटे", "bete"): [("बेटी", "beti")],
    ("बेटी", "beti"): [("बेटे", "bete")],
    ("दीदी", "didi"): [("दादी", "dadi")],
    ("दादी", "dadi"): [("दीदी", "didi")],
    ("बुलाओ", "bulao"): [("भुलाओ", "bhulao"), ("सुलाओ", "sulao")],
    ("पंखा", "pankha"): [("पंजा", "panja")],
    ("लाइट", "light"): [("राइट", "right")],
    ("ठंड", "thand"): [("दंड", "dand")],
    ("गर्मी", "garmi"): [("नरमी", "narmi")],
    ("पेट", "pet"): [("पेड़", "ped"), ("बेट", "bet")],
    ("सांस", "saans"): [("सास", "saas")],
    ("चक्कर", "chakkar"): [("शक्कर", "shakkar")],
    ("भूख", "bhookh"): [("भूत", "bhoot")],
    ("नमक", "namak"): [("नमन", "naman")],
    ("मीठा", "meetha"): [("मिट्टी", "mitti")],
    ("नहीं", "nahin"): [("नई", "nai")],
    ("अच्छा", "achha"): [("बच्चा", "bachcha")],
    ("उठा", "utha"): [("उड़ा", "uda")],
    ("लिटा", "lita"): [("मिटा", "mita")],
    ("बदल", "badal"): [("बादल", "baadal")],
    ("रुको", "ruko"): [("रखो", "rakho")],
    ("छोड़ो", "chhodo"): [("जोड़ो", "jodo"), ("तोड़ो", "todo")],
    ("दो", "do"): [("तो", "to")],
    ("गरम", "garam"): [("करम", "karam")],
    ("बंद", "band"): [("मंद", "mand")],
    ("कंबल", "kambal"): [("कमल", "kamal")],
    ("तकिया", "takiya"): [("टिकिया", "tikiya")],
    ("खिड़की", "khidki"): [("झिड़की", "jhidki")],
    ("घर", "ghar"): [("पर", "par")],
    ("सोना", "sona"): [("रोना", "rona")],
    ("हाथ", "haath"): [("साथ", "saath"), ("बात", "baat")],
    ("पैर", "pair"): [("बैर", "bair")],
    ("चोट", "chot"): [("छोटा", "chhota")],
    ("बोलो", "bolo"): [("खोलो", "kholo")],
    ("खोल", "khol"): [("बोल", "bol")],
    ("चला", "chala"): [("जला", "jala")],
    ("जला", "jala"): [("चला", "chala")],
    ("आओ", "aao"): [("जाओ", "jaao")],
}
SIMILAR = {}
for (dev, latin), alts in REAL_WORDS.items():
    SIMILAR[nfc(dev)] = [nfc(d) for d, _ in alts]
    SIMILAR[latin] = [lat for _, lat in alts]


def words_merged(words, rng):
    if len(words) < 2:
        return None
    i = rng.randrange(len(words) - 1)
    return words[:i] + [(words[i][0] + words[i + 1][0], words[i][1])] + words[i + 2:]


def word_split(words, rng):
    options = []
    for w, (text, script) in enumerate(words):
        units = (LATIN_UNIT if script == "latin" else DEV_UNIT).findall(text)
        # In Devanagari, never split off a vowel sign, a halant or a nasal from its letter.
        options += [(w, i, units) for i in range(2, len(units) - 1)
                    if script == "latin" or is_consonant(units[i], script) or units[i] in INDEPENDENT.values()]
    if not options:
        return None
    w, i, units = rng.choice(options)
    script = words[w][1]
    return words[:w] + [("".join(units[:i]), script), ("".join(units[i:]), script)] + words[w + 1:]


def short_word_dropped(words, rng):
    spots = [i for i, (text, _) in enumerate(words) if len(text) <= 2]
    if len(words) < 2 or not spots:
        return None
    i = rng.choice(spots)
    return words[:i] + words[i + 1:]


def filler_added(words, rng):
    script = rng.choice(words)[1]
    i = rng.randint(0, len(words))
    return words[:i] + [(rng.choice(FILLERS[script]), script)] + words[i:]


def real_word_confusion(words, rng):
    spots = [i for i, (text, _) in enumerate(words) if text in SIMILAR]
    if not spots:
        return None
    i = rng.choice(spots)
    return words[:i] + [(rng.choice(SIMILAR[words[i][0]]), words[i][1])] + words[i + 1:]


WORD_RULES = {words_merged: 1, word_split: 1, short_word_dropped: 1, filler_added: 1, real_word_confusion: 2}
RULES = {**SOUND_RULES, **WORD_RULES}


def apply_one(words, rng):
    """Apply one randomly chosen rule that fits; returns (words, rule name)."""
    rules = list(RULES)
    weights = [RULES[r] for r in rules]
    for _ in range(50):
        rule = rng.choices(rules, weights)[0]
        if rule in WORD_RULES:
            changed = rule(words, rng)
        else:
            changed = None
            for w in rng.sample(range(len(words)), len(words)):
                text, script = words[w]
                units = rule((LATIN_UNIT if script == "latin" else DEV_UNIT).findall(text), script, rng)
                if units is not None and "".join(units) and "".join(units) != text:
                    changed = words[:w] + [("".join(units), script)] + words[w + 1:]
                    break
        if changed:
            return changed, rule.__name__
    return words, None


def start_words(phrase, rng):
    """The phrase's words, in the script Prisma would write this variant in."""
    clean = lambda text: [w.strip(",.?!") for w in text.split()]
    dev, latin = clean(phrase.hindi), clean(phrase.latin)
    mode = rng.choices(list(SCRIPTS), list(SCRIPTS.values()))[0]
    if mode == "mixed" and len(dev) > 1:
        picks = [rng.random() < 0.5 for _ in dev]
        picks[rng.randrange(len(dev))] = not picks[0] if all(p == picks[0] for p in picks) else picks[0]
        return [(lat, "latin") if p else (d, "dev") for d, lat, p in zip(dev, latin, picks)]
    if mode == "latin":
        return [(w, "latin") for w in latin]
    return [(w, "dev") for w in dev]


def script_of(text):
    words = text.split()
    dev = sum(has_devanagari(w) for w in words)
    return "devanagari" if dev == len(words) else "latin" if dev == 0 else "mixed"


def main():
    rng = random.Random(SEED)
    phrases = pd.read_csv(os.path.join(HERE, "phrases.csv"))
    phrases["hindi"] = phrases.hindi.map(nfc)

    ids = list(phrases.phrase_id)
    rng.shuffle(ids)
    n_train, n_val = round(0.8 * len(ids)), round(0.1 * len(ids))
    split = {pid: "train" if i < n_train else "val" if i < n_train + n_val else "test" for i, pid in enumerate(ids)}
    # A variant that reads exactly like some phrase is no mishearing of a different one.
    every_phrase = set(phrases.hindi.map(normalize)) | set(phrases.latin.map(normalize))

    rows, short = [], []
    for phrase in phrases.itertuples():
        seen = set()
        for severity, count in VARIANTS.items():
            made = 0
            for _ in range(300):
                if made == count:
                    break
                words = start_words(phrase, rng)
                errors = []
                for _ in range(rng.randint(*EDITS[severity])):
                    words, error = apply_one(words, rng)
                    if error:
                        errors.append(error)
                heard = " ".join(text for text, _ in words)
                if heard in seen or not heard.strip():
                    continue
                if severity != "clean" and (len(errors) < EDITS[severity][0] or normalize(heard) in every_phrase):
                    continue
                seen.add(heard)
                made += 1
                rows.append({"pair_id": len(rows) + 1, "phrase_id": phrase.phrase_id, "intended": phrase.hindi,
                             "intended_latin": phrase.latin, "meaning_en": phrase.meaning_en, "place": phrase.place,
                             "heard": heard, "script": script_of(heard), "severity": severity,
                             "error_types": ";".join(errors), "split": split[phrase.phrase_id]})
            if made < count:
                short.append((phrase.phrase_id, severity, made, count))

    data = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data.to_csv(OUT, index=False, encoding="utf-8")

    print(f"wrote {len(data)} pairs to {OUT}")
    if short:
        print("phrases with fewer unique variants than asked (phrase_id, severity, made, asked):", short)
    print(data.groupby("split").agg(pairs=("pair_id", "size"), phrases=("phrase_id", "nunique")).to_string())
    print("severity:", data.severity.value_counts().to_dict())
    print("script:", data.script.value_counts().to_dict())
    print("heard == intended:", int((data.heard == data.intended).sum() + (data.heard == data.intended_latin).sum()),
          f"of {len(data)}")
    errors = data.error_types[data.error_types != ""].str.split(";").explode()
    print("edits by rule:", errors.value_counts().to_dict())
    print("\n15 random rows:")
    for r in data.sample(15, random_state=SEED).itertuples():
        print(f"  [{r.split:5} {r.severity:8} {r.script:10}] {r.intended}  ->  {r.heard}    ({r.error_types or 'clean'})")


if __name__ == "__main__":
    main()

"""Generate synthetic STT mishearings for Hindi words spoken unclearly.

Each row: what the STT might write (heard) -> the word the person meant (intended).
Run: python make_word_variants.py  -> writes sunn_word_variants.csv
"""
import csv
import random
import re
import unicodedata
import zlib

rng = random.Random(42)

# hindi, casual latin, english meaning, category
WORDS = """
पानी|paani|water|needs
खाना|khaana|food|needs
भूख|bhookh|hunger|needs
प्यास|pyaas|thirst|needs
चाहिए|chahiye|need / want|needs
बाथरूम|bathroom|bathroom|needs
पेशाब|peshaab|urine|needs
टॉयलेट|toilet|toilet|needs
नींद|neend|sleep|needs
सोना|sona|to sleep|needs
आराम|aaraam|rest|needs
कंबल|kambal|blanket|needs
तकिया|takiya|pillow|needs
चादर|chaadar|bedsheet|needs
कपड़े|kapde|clothes|needs
चश्मा|chashma|glasses|needs
फोन|phone|phone|needs
चार्जर|charger|charger|needs
पंखा|pankha|fan|needs
लाइट|light|light|needs
गर्मी|garmi|heat / feeling hot|needs
ठंड|thand|cold / feeling cold|needs
नहाना|nahaana|to bathe|needs
कुर्सी|kursi|chair|needs
बिस्तर|bistar|bed|needs
दरवाज़ा|darwaaza|door|needs
खिड़की|khidki|window|needs
टीवी|tv|tv|needs
रिमोट|remote|remote|needs
दर्द|dard|pain|pain_health
दुखता|dukhta|it hurts|pain_health
जलन|jalan|burning|pain_health
चक्कर|chakkar|dizziness|pain_health
बुखार|bukhaar|fever|pain_health
खांसी|khaansi|cough|pain_health
उल्टी|ulti|vomiting|pain_health
सांस|saans|breath|pain_health
घबराहट|ghabraahat|panic / uneasiness|pain_health
कमज़ोरी|kamzori|weakness|pain_health
सूजन|soojan|swelling|pain_health
खुजली|khujli|itching|pain_health
चोट|chot|injury|pain_health
खून|khoon|blood|pain_health
पसीना|paseena|sweat|pain_health
सिरदर्द|sirdard|headache|pain_health
दवाई|dawaai|medicine|pain_health
दवा|dawa|medicine|pain_health
गोली|goli|tablet|pain_health
इंजेक्शन|injection|injection|pain_health
डॉक्टर|doctor|doctor|pain_health
नर्स|nurse|nurse|pain_health
अस्पताल|aspataal|hospital|pain_health
एम्बुलेंस|ambulance|ambulance|pain_health
मदद|madad|help|pain_health
बचाओ|bachaao|save me|pain_health
जल्दी|jaldi|quickly|pain_health
तकलीफ़|takleef|discomfort|pain_health
बीमार|beemaar|sick|pain_health
ठीक|theek|fine / okay|pain_health
बेहतर|behtar|better|pain_health
खराब|kharaab|bad / unwell|pain_health
ऑक्सीजन|oxygen|oxygen|pain_health
शुगर|sugar|blood sugar|pain_health
बीपी|bp|blood pressure|pain_health
सिर|sir|head|body
पेट|pet|stomach|body
पैर|pair|leg / foot|body
हाथ|haath|hand|body
कमर|kamar|lower back|body
पीठ|peeth|back|body
गला|gala|throat|body
दांत|daant|tooth|body
आंख|aankh|eye|body
कान|kaan|ear|body
नाक|naak|nose|body
मुंह|munh|mouth|body
छाती|chhaati|chest|body
दिल|dil|heart|body
घुटना|ghutna|knee|body
कंधा|kandha|shoulder|body
गर्दन|gardan|neck|body
उंगली|ungli|finger|body
पसली|pasli|rib|body
जीभ|jeebh|tongue|body
मम्मी|mummy|mom|family
पापा|papa|dad|family
माँ|maa|mother|family
बेटा|beta|son|family
बेटी|beti|daughter|family
भाई|bhai|brother|family
बहन|behen|sister|family
पत्नी|patni|wife|family
पति|pati|husband|family
दादी|daadi|grandmother|family
दादा|daada|grandfather|family
नानी|naani|maternal grandmother|family
बच्चे|bachche|children|family
बहू|bahu|daughter-in-law|family
दोस्त|dost|friend|family
पड़ोसी|padosi|neighbour|family
भैया|bhaiya|elder brother|family
दीदी|didi|elder sister|family
चाचा|chacha|uncle|family
आंटी|aunty|aunty|family
चाय|chaai|tea|food
दूध|doodh|milk|food
रोटी|roti|roti|food
चावल|chaawal|rice|food
दाल|daal|dal|food
सब्ज़ी|sabzi|vegetable|food
फल|phal|fruit|food
केला|kela|banana|food
सेब|seb|apple|food
जूस|juice|juice|food
बिस्किट|biscuit|biscuit|food
अंडा|anda|egg|food
दही|dahi|curd|food
नमक|namak|salt|food
चीनी|cheeni|sugar|food
खिचड़ी|khichdi|khichdi|food
सूप|soup|soup|food
मीठा|meetha|sweet|food
गरम|garam|hot|food
ठंडा|thanda|cold|food
कितना|kitna|how much|market
पैसे|paise|money|market
रुपये|rupaye|rupees|market
सस्ता|sasta|cheap|market
महंगा|mehenga|expensive|market
कम|kam|less|market
ज़्यादा|zyaada|more|market
थैला|thaila|bag|market
दुकान|dukaan|shop|market
किलो|kilo|kilo|market
आधा|aadha|half|market
छुट्टा|chhutta|change (coins)|market
बिल|bill|bill|market
वापस|waapas|back / return|market
दिखाओ|dikhaao|show me|market
लेना|lena|to take|market
देना|dena|to give|market
रखो|rakho|keep it|market
खुश|khush|happy|feelings
दुखी|dukhi|sad|feelings
डर|dar|fear|feelings
गुस्सा|gussa|angry|feelings
अकेला|akela|alone|feelings
परेशान|pareshaan|troubled|feelings
थकान|thakaan|tiredness|feelings
थका|thaka|tired|feelings
बोर|bore|bored|feelings
शुक्रिया|shukriya|thank you|feelings
धन्यवाद|dhanyavaad|thank you|feelings
माफ़ी|maafi|sorry|feelings
प्यार|pyaar|love|feelings
हाँ|haan|yes|basic
नहीं|nahi|no|basic
अच्छा|achha|okay / good|basic
रुको|ruko|wait|basic
बस|bas|enough / stop|basic
और|aur|more / and|basic
फिर|phir|again / then|basic
दोबारा|dobaara|once more|basic
समझे|samjhe|understood?|basic
सुनो|suno|listen|basic
कृपया|kripya|please|basic
ज़रूर|zaroor|sure|basic
मत|mat|don't|basic
सही|sahi|correct|basic
गलत|galat|wrong|basic
जाना|jaana|to go|actions
आना|aana|to come|actions
बैठना|baithna|to sit|actions
उठना|uthna|to get up|actions
लेटना|letna|to lie down|actions
चलना|chalna|to walk|actions
बुलाओ|bulaao|call (someone)|actions
उठाओ|uthaao|lift me|actions
पकड़ो|pakdo|hold me|actions
खोलो|kholo|open|actions
बंद|band|close / switch off|actions
चालू|chaalu|switch on|actions
बदलो|badlo|change|actions
पोंछो|ponchho|wipe|actions
धीरे|dheere|slowly|actions
ज़ोर|zor|loud / hard|actions
घुमाओ|ghumaao|turn me|actions
लाओ|laao|bring|actions
पिलाओ|pilaao|give me a drink|actions
खिलाओ|khilaao|feed me|actions
नहलाओ|nahlaao|bathe me|actions
करवट|karvat|turn on my side|actions
अभी|abhi|now|time
बाद|baad|later|time
सुबह|subah|morning|time
शाम|shaam|evening|time
रात|raat|night|time
दोपहर|dopahar|afternoon|time
कल|kal|tomorrow / yesterday|time
आज|aaj|today|time
समय|samay|time|time
घंटा|ghanta|hour|time
मिनट|minute|minute|time
घर|ghar|home|places
कमरा|kamra|room|places
रसोई|rasoi|kitchen|places
बाहर|baahar|outside|places
अंदर|andar|inside|places
ऊपर|upar|up|places
नीचे|neeche|down|places
मंदिर|mandir|temple|places
बाज़ार|baazaar|market|places
पार्क|park|park|places
छत|chhat|roof|places
एक|ek|one|numbers
दो|do|two|numbers
तीन|teen|three|numbers
चार|chaar|four|numbers
पांच|paanch|five|numbers
छह|chhah|six|numbers
सात|saat|seven|numbers
आठ|aath|eight|numbers
नौ|nau|nine|numbers
दस|das|ten|numbers
सौ|sau|hundred|numbers
"""

# ---------- devanagari rules ----------
CONS = set(chr(c) for c in range(0x0915, 0x093A))
MATRAS = set("ािीुूृॅॉेैोौ")
NUKTA, VIRAMA = "़", "्"
NASALS = set("ंँ")
VOWELS = set(chr(c) for c in range(0x0905, 0x0915))
TO_VOWEL = dict(zip("ािीुूेैोौृॉ", "आइईउऊएऐओऔऋऑ"))

D_VOICE = {"प": "ब", "ब": "प", "त": "द", "द": "त", "ट": "ड", "ड": "ट", "क": "ग", "ग": "क", "च": "ज", "ज": "च"}
D_ASP = {"फ": "प", "भ": "ब", "ख": "क", "घ": "ग", "थ": "त", "ध": "द", "ठ": "ट", "ढ": "ड", "छ": "च", "झ": "ज",
         "प": "फ", "ब": "भ", "क": "ख", "ग": "घ", "त": "थ", "द": "ध", "ट": "ठ", "ड": "ढ", "च": "छ", "ज": "झ"}
D_RETRO = {"ट": "त", "त": "ट", "ड": "द", "द": "ड", "ठ": "थ", "थ": "ठ", "ढ": "ध", "ध": "ढ", "ण": "न"}
D_SIB = {"श": "स", "स": "श", "ष": "स"}
D_LIQ = {"र": "ल", "ल": "र"}
D_VB = {"व": "ब", "ब": "व"}
D_YJ = {"य": "ज"}
D_MATRA = {"ा": ["", ], "ी": ["ि"], "ि": ["ी", "े"], "ू": ["ु"], "ु": ["ू", "ो"], "े": ["ि", "ै"],
           "ै": ["े"], "ो": ["ु", "ौ"], "ौ": ["ो"], "ॉ": ["ा", "ो"], "ृ": ["ि", "्र"]}


def d_valid(w):
    if not w or w[0] in MATRAS | NASALS | {NUKTA, VIRAMA}:
        return False
    for a, b in zip(w, w[1:]):
        if b in MATRAS and a not in CONS and a != NUKTA:
            return False
        if b == VIRAMA and a not in CONS and a != NUKTA:
            return False
        if b == NUKTA and a not in CONS:
            return False
        if b in NASALS and a in NASALS:
            return False
    return w[-1] != VIRAMA


def d_swap(w, table):
    idx = [i for i, ch in enumerate(w) if ch in table]
    if not idx:
        return None
    i = rng.choice(idx)
    rest = w[i + 1:]
    if rest.startswith(NUKTA):
        rest = rest[1:]
    return w[:i] + table[w[i]] + rest


def d_matra(w):
    idx = [i for i, ch in enumerate(w) if ch in D_MATRA]
    add = [i for i, ch in enumerate(w) if ch in CONS and (i + 1 == len(w) or w[i + 1] in CONS)]
    if idx and (not add or rng.random() < 0.7):
        i = rng.choice(idx)
        return w[:i] + rng.choice(D_MATRA[w[i]]) + w[i + 1:]
    if add:
        i = rng.choice(add)
        return w[:i + 1] + "ा" + w[i + 1:]
    return None


def d_nasal(w):
    idx = [i for i, ch in enumerate(w) if ch in NASALS]
    if idx and rng.random() < 0.75:
        i = rng.choice(idx)
        return w[:i] + ("" if rng.random() < 0.7 else ("ँ" if w[i] == "ं" else "ं")) + w[i + 1:]
    spots = [i for i, ch in enumerate(w[:-1]) if (ch in MATRAS or ch in CONS) and w[i + 1] in CONS]
    if not spots:
        return None
    i = rng.choice(spots)
    return w[:i + 1] + "ं" + w[i + 1:]


def d_virama(w):
    idx = [i for i, ch in enumerate(w) if ch == VIRAMA]
    if idx and rng.random() < 0.7:
        i = rng.choice(idx)
        return w[:i] + w[i + 1:]  # split the cluster: दर्द -> दरद
    spots = [i for i, ch in enumerate(w[:-1]) if ch in CONS and w[i + 1] in CONS and i > 0]
    if not spots:
        return None
    i = rng.choice(spots)
    return w[:i + 1] + VIRAMA + w[i + 1:]


def d_hdrop(w):
    idx = [i for i, ch in enumerate(w) if ch == "ह"]
    if not idx:
        return None
    i = rng.choice(idx)
    nxt = w[i + 1] if i + 1 < len(w) else ""
    if nxt in TO_VOWEL:
        return w[:i] + TO_VOWEL[nxt] + w[i + 2:]
    return w[:i] + w[i + 1:]


def d_nukta(w):
    if NUKTA in w:
        i = w.index(NUKTA)
        if w[i - 1] == "ड" and rng.random() < 0.5:
            return w[:i - 1] + "र" + w[i + 1:]
        return w[:i] + w[i + 1:]
    return d_swap(w, {"र": "ड" + NUKTA})


def d_endchop(w):
    if len(w) < 3:
        return None
    if w[-1] in MATRAS | NASALS:
        return w[:-1]
    cut = w[:-1]
    return cut[:-1] if cut.endswith(VIRAMA) else cut


def d_initdrop(w):
    if len(w) < 3 or w[0] not in CONS:
        return None
    if w[1] in TO_VOWEL:
        return TO_VOWEL[w[1]] + w[2:]
    if w[1] in CONS:
        return "अ" + w[1:]
    return None


def d_double(w):
    spots = [i for i, ch in enumerate(w) if ch in CONS and 0 < i and w[i - 1] not in (VIRAMA,)]
    if not spots:
        return None
    i = rng.choice(spots)
    return w[:i] + w[i] + VIRAMA + w[i:]


def first_akshara(w):
    m = re.match(r"[क-ह]़?[ा-ौ]?|[अ-औ]", w)
    return m.group(0) if m else None


def d_stutter(w):
    a = first_akshara(w)
    return f"{a} {w}" if a and len(w) > 2 else None


def d_split(w):
    spots = [i for i in range(2, len(w) - 1) if w[i] in CONS and w[i - 1] != VIRAMA]
    if not spots:
        return None
    i = rng.choice(spots)
    return w[:i] + " " + w[i:]


D_RULES = [
    ("voicing", lambda w: d_swap(w, D_VOICE), 3), ("aspiration", lambda w: d_swap(w, D_ASP), 3),
    ("retroflex_dental", lambda w: d_swap(w, D_RETRO), 2), ("vowel", d_matra, 3.5),
    ("nasal", d_nasal, 1.5), ("cluster", d_virama, 1.5), ("h_drop", d_hdrop, 1),
    ("sibilant", lambda w: d_swap(w, D_SIB), 1), ("r_l", lambda w: d_swap(w, D_LIQ), 0.8),
    ("v_b", lambda w: d_swap(w, D_VB), 0.8), ("y_j", lambda w: d_swap(w, D_YJ), 0.5),
    ("nukta", d_nukta, 0.8), ("end_chop", d_endchop, 2), ("initial_drop", d_initdrop, 0.6),
    ("doubling", d_double, 0.6), ("stutter", d_stutter, 0.4), ("word_split", d_split, 0.6),
]

# ---------- latin rules ----------
TOK = re.compile(r"chh|ch|kh|gh|ph|bh|th|dh|sh|jh|aa|ee|oo|ai|au|[a-z]")
L_VOWELS = {"a", "e", "i", "o", "u", "aa", "ee", "oo", "ai", "au"}
L_VOICE = {"p": "b", "b": "p", "t": "d", "d": "t", "k": "g", "g": "k", "ch": "j", "j": "ch", "s": "z", "z": "j"}
L_ASP = {"kh": "k", "gh": "g", "ph": "p", "bh": "b", "th": "t", "dh": "d", "chh": "ch", "jh": "j",
         "k": "kh", "p": "ph", "t": "th", "d": "dh", "b": "bh", "g": "gh", "f": "ph"}
L_VOWEL = {"aa": ["a"], "a": ["aa", "e", "u"], "ee": ["i", "e"], "i": ["ee", "e"], "oo": ["u", "o"],
           "u": ["oo", "o"], "e": ["i", "a"], "o": ["u", "au"], "ai": ["e", "ae"], "au": ["o"]}
L_MISC = {"sh": "s", "s": "sh", "r": "l", "l": "r", "v": "b", "w": "v", "y": "j", "ph": "f", "z": "j"}


def toks(w):
    return TOK.findall(w)


def l_map(w, table, multi=False):
    t = toks(w)
    idx = [i for i, x in enumerate(t) if x in table]
    if not idx:
        return None
    i = rng.choice(idx)
    t[i] = rng.choice(table[t[i]]) if multi else table[t[i]]
    return "".join(t)


def l_drop(w, which):
    t = toks(w)
    idx = [i for i, x in enumerate(t) if x in which and 0 < i]
    if not idx:
        return None
    del t[rng.choice(idx)]
    return "".join(t)


def l_nasal(w):
    t = toks(w)
    idx = [i for i, x in enumerate(t) if x == "n" and (i + 1 == len(t) or t[i + 1] not in L_VOWELS) and i > 0]
    if idx and rng.random() < 0.7:
        del t[rng.choice(idx)]
        return "".join(t)
    spots = [i for i, x in enumerate(t[:-1]) if x in L_VOWELS and t[i + 1] not in L_VOWELS]
    if not spots:
        return None
    t.insert(rng.choice(spots) + 1, "n")
    return "".join(t)


def l_endchop(w):
    t = toks(w)
    if len(t) < 3:
        return None
    return "".join(t[:-2] if len(t) > 5 and rng.random() < 0.4 else t[:-1])


def l_initdrop(w):
    t = toks(w)
    if len(t) < 3 or t[0] in L_VOWELS:
        return None
    return "".join(t[1:])


def l_double(w):
    t = toks(w)
    for i in range(len(t) - 1):
        if t[i] == t[i + 1] and t[i] not in L_VOWELS:
            return "".join(t[:i] + t[i + 1:])
    spots = [i for i, x in enumerate(t) if x not in L_VOWELS and i > 0]
    if not spots:
        return None
    i = rng.choice(spots)
    return "".join(t[:i] + [t[i]] + t[i:])


def l_stutter(w):
    t = toks(w)
    if len(t) < 3:
        return None
    head = t[0] + (t[1] if t[1] in L_VOWELS else "")
    return f"{head} {w}"


def l_split(w):
    t = toks(w)
    if len(t) < 4:
        return None
    i = rng.randint(2, len(t) - 2)
    return "".join(t[:i]) + " " + "".join(t[i:])


L_RULES = [
    ("voicing", lambda w: l_map(w, L_VOICE), 3), ("aspiration", lambda w: l_map(w, L_ASP), 3),
    ("vowel", lambda w: l_map(w, L_VOWEL, multi=True), 3.5), ("nasal", l_nasal, 1.5),
    ("h_drop", lambda w: l_drop(w, {"h"}), 1), ("r_drop", lambda w: l_drop(w, {"r"}), 0.8),
    ("misc_consonant", lambda w: l_map(w, L_MISC), 1.5), ("end_chop", l_endchop, 2),
    ("initial_drop", l_initdrop, 0.6), ("doubling", l_double, 0.8), ("stutter", l_stutter, 0.4),
    ("word_split", l_split, 0.6),
]


def l_valid(w):
    return bool(w) and re.search(r"[aeiou]", w) is not None


def mutate(word, rules, valid, n_ops):
    names, fns, weights = zip(*[(n, f, wt) for n, f, wt in rules])
    used, out = [], word
    tries = 0
    while len(used) < n_ops and tries < 25:
        tries += 1
        k = rng.choices(range(len(fns)), weights=weights)[0]
        # space-separated output: mutate one part
        parts = out.split(" ")
        j = rng.randrange(len(parts))
        new = fns[k](parts[j])
        if not new or new == parts[j]:
            continue
        parts[j] = new
        cand = " ".join(parts)
        if all(valid(p) for p in cand.split(" ")):
            out = cand
            used.append(names[k])
    return (out, used) if used else (None, [])


PLAN = [  # (script, severity, ops, count)
    ("devanagari", "mild", (1, 1), 6), ("devanagari", "moderate", (2, 2), 6), ("devanagari", "severe", (3, 4), 3),
    ("latin", "mild", (1, 1), 4), ("latin", "moderate", (2, 2), 4), ("latin", "severe", (3, 4), 2),
]


def consonants(word, script):
    if script == "devanagari":
        return sum(ch in CONS for ch in word)
    return sum(t not in L_VOWELS for t in toks(word))


def severity(n):
    return "mild" if n == 1 else "moderate" if n == 2 else "severe"


def split_for(word):
    h = zlib.crc32(word.encode()) % 10
    return "test" if h == 0 else "val" if h == 1 else "train"


def main():
    vocab = []
    for line in WORDS.strip().splitlines():
        hi, la, mean, cat = [x.strip() for x in line.split("|")]
        vocab.append((unicodedata.normalize("NFC", hi), la.lower(), mean, cat))

    intended_forms = {v[0] for v in vocab} | {v[1] for v in vocab}
    # latin spellings that are real english words with another meaning ("no" is not नौ)
    intended_forms |= {"no", "dad", "bad", "mom", "yes", "go", "to", "so", "me", "we", "he", "be", "an", "in",
                       "on", "at", "it", "is", "as", "or", "up", "us", "am", "aunt", "bat", "bet", "but", "cut"}
    seen_heard = {}
    rows = []
    for hi, la, mean, cat in vocab:
        own = set()
        rows_word = [(hi, "devanagari", "clean", ""), (la, "latin", "clean", "")]
        own.update([hi, la])
        for script, sev, (lo, hi_ops), count in PLAN:
            base, rules, valid = (hi, D_RULES, d_valid) if script == "devanagari" else (la, L_RULES, l_valid)
            made, attempts = 0, 0
            while made < count and attempts < 200:
                attempts += 1
                # short words can't take many edits and stay recognisable
                n_ops = min(rng.randint(lo, hi_ops), max(1, consonants(base, script)))
                heard, used = mutate(base, rules, valid, n_ops)
                if not heard or heard in own or heard in intended_forms:
                    continue
                if heard in seen_heard:  # another word already owns this spelling
                    continue
                own.add(heard)
                rows_word.append((heard, script, severity(len(used)), "+".join(used)))
                made += 1
        for heard, script, sev, errs in rows_word:
            seen_heard.setdefault(heard, hi)
            rows.append({"heard": heard, "script": script, "intended_hindi": hi, "intended_latin": la,
                         "meaning_en": mean, "category": cat, "severity": sev, "error_types": errs,
                         "split": split_for(hi)})

    with open("sunn_word_variants.csv", "w", newline="", encoding="utf-8-sig") as f:
        fields = ["id"] + list(rows[0].keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            w.writerow({"id": i, **r})

    print(f"words: {len(vocab)}  rows: {len(rows)}")
    for s in ("train", "val", "test"):
        print(s, sum(r["split"] == s for r in rows), "rows,", len({r["intended_hindi"] for r in rows if r["split"] == s}), "words")


if __name__ == "__main__":
    main()
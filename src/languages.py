"""The languages Sunn hears and speaks. Prisma and Timbre both take <code>-IN for all ten
(docs.gnani.ai/api/STT/languages.md, docs.gnani.ai/api/TTS/tts-inference.md)."""
from typing import NamedTuple

from indic_transliteration import sanscript


class Language(NamedTuple):
    name: str  # in English, for the judge
    script: str
    block: tuple[str, str] | None  # the script's Unicode block; None for Latin
    scheme: str | None  # its indic_transliteration.sanscript scheme


DEVANAGARI = ("ऀ", "ॿ")
LANGUAGES = {
    "en": Language("English", "Latin", None, None),
    "hi": Language("Hindi", "Devanagari", DEVANAGARI, sanscript.DEVANAGARI),
    "ta": Language("Tamil", "Tamil", ("஀", "௿"), sanscript.TAMIL),
    "te": Language("Telugu", "Telugu", ("ఀ", "౿"), sanscript.TELUGU),
    "kn": Language("Kannada", "Kannada", ("ಀ", "೿"), sanscript.KANNADA),
    "ml": Language("Malayalam", "Malayalam", ("ഀ", "ൿ"), sanscript.MALAYALAM),
    "mr": Language("Marathi", "Devanagari", DEVANAGARI, sanscript.DEVANAGARI),
    "gu": Language("Gujarati", "Gujarati", ("઀", "૿"), sanscript.GUJARATI),
    "bn": Language("Bengali", "Bengali", ("ঀ", "৿"), sanscript.BENGALI),
    "pa": Language("Punjabi", "Gurmukhi", ("਀", "੿"), sanscript.GURMUKHI),
}
CODES = tuple(LANGUAGES)
# Each Indic script once, Devanagari first: (block, scheme).
SCRIPTS = list(dict.fromkeys((lang.block, lang.scheme) for lang in LANGUAGES.values() if lang.block))


def in_script(text, block):
    return any(block[0] <= c <= block[1] for c in text)


def script_of(text):
    """The code of the first language whose script text is in (hi for Devanagari), else None."""
    return next((code for code, lang in LANGUAGES.items() if lang.block and in_script(text, lang.block)), None)

"""Tests for Speak screen reliability, candidate matching, and translation parity."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_speak_i18n_parity():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    hi_content = (ROOT / 'web/src/i18n/hi.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))
    hi_keys = set(re.findall(r"'([^']+)'\s*:", hi_content))

    assert en_keys == hi_keys, f'i18n mismatch: {en_keys ^ hi_keys}'
    speak_keys = [k for k in en_keys if k.startswith('speak.')]
    assert len(speak_keys) >= 15, f'Expected at least 15 speak keys, got {len(speak_keys)}'


def test_no_em_dashes_in_source():
    em_dash = '\u2014'
    for path in (ROOT / 'web/src').rglob('*'):
        if path.suffix in ('.js', '.jsx', '.css'):
            content = path.read_text(encoding='utf-8')
            assert em_dash not in content, f'Em dash found in {path}'


def test_candidate_key_uniqueness():
    def make_key(c, index):
        if c.get('composed'):
            return f"composed-{c.get('template_id')}-{c.get('slot_word_id')}-{index}"
        return f"phrase-{c.get('phrase_id', 'text')}-{c.get('text', '')}-{index}"

    candidates = [
        {'text': 'पानी चाहिए', 'phrase_id': 1},
        {'text': 'पानी चाहिए', 'phrase_id': None},
        {'text': 'पानी चाहिए', 'phrase_id': 1},
        {'composed': True, 'template_id': 2, 'slot_word_id': 3, 'text': 'खाना चाहिए'},
    ]

    keys = [make_key(c, i) for i, c in enumerate(candidates)]
    assert len(keys) == len(set(keys)), f'Duplicate candidate keys detected: {keys}'


if __name__ == '__main__':
    test_speak_i18n_parity()
    test_no_em_dashes_in_source()
    test_candidate_key_uniqueness()
    print('Baseline speak reliability tests passed!')

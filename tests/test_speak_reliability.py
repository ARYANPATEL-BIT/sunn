"""Tests for Speak screen reliability, candidate matching, playback lifecycle, and translation parity."""
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
    assert len(speak_keys) >= 20, f'Expected at least 20 speak keys, got {len(speak_keys)}'

    # Check status announcement keys
    expected_status_keys = [
        'speak.statusRecording',
        'speak.statusListening',
        'speak.statusPlaying',
        'speak.statusSpoke',
        'error.unsupported',
        'error.confirm_failed',
    ]
    for key in expected_status_keys:
        assert key in en_keys, f'Missing expected key {key} in en.js'


def test_speak_jsx_translation_calls():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))

    speak_code = (ROOT / 'web/src/Speak.jsx').read_text(encoding='utf-8')
    calls = re.findall(r"t\(\s*['\"]([a-zA-Z0-9_.]+)['\"]", speak_code)
    missing = [c for c in calls if c not in en_keys]
    assert not missing, f'Missing translation keys in Speak.jsx: {missing}'


def test_no_em_dashes_in_source():
    em_dash = '\u2014'
    for path in (ROOT / 'web/src').rglob('*'):
        if path.suffix in ('.js', '.jsx', '.css'):
            content = path.read_text(encoding='utf-8')
            assert em_dash not in content, f'Em dash found in {path}'


def test_candidate_key_uniqueness():
    def make_key(c, index=0):
        if not c:
            return f'candidate-empty-{index}'
        if c.get('composed'):
            t_id = c.get('template_id') or 't'
            w_id = c.get('slot_word_id') or 'w'
            return f'composed-{t_id}-{w_id}-{index}'
        if c.get('phrase_id') is not None:
            return f"phrase-{c.get('phrase_id')}-{index}"
        return f"text-{c.get('text', '')}-{index}"

    candidates = [
        {'text': 'पानी चाहिए', 'phrase_id': 1},
        {'text': 'पानी चाहिए', 'phrase_id': None},
        {'text': 'पानी चाहिए', 'phrase_id': 1},
        {'composed': True, 'template_id': 2, 'slot_word_id': 3, 'text': 'खाना चाहिए'},
    ]

    keys = [make_key(c, i) for i, c in enumerate(candidates)]
    assert len(keys) == len(set(keys)), f'Duplicate candidate keys detected: {keys}'


def test_candidate_matching_logic():
    def is_same_candidate(a, b):
        if not a or not b:
            return False
        if a.get('composed') or b.get('composed'):
            return bool(
                a.get('composed')
                and b.get('composed')
                and a.get('template_id') == b.get('template_id')
                and a.get('slot_word_id') == b.get('slot_word_id')
            )
        if a.get('phrase_id') is not None or b.get('phrase_id') is not None:
            return (
                a.get('phrase_id') is not None
                and b.get('phrase_id') is not None
                and a.get('phrase_id') == b.get('phrase_id')
            )
        return bool(a.get('text') and b.get('text') and a['text'].strip() == b['text'].strip())

    # Same phrase ID matches
    assert is_same_candidate({'phrase_id': 1, 'text': 'A'}, {'phrase_id': 1, 'text': 'A'})
    assert is_same_candidate({'phrase_id': 1, 'text': 'A'}, {'phrase_id': 1, 'text': 'B'})

    # Different phrase ID rejects
    assert not is_same_candidate({'phrase_id': 1, 'text': 'A'}, {'phrase_id': 2, 'text': 'A'})

    # Missing phrase ID on one must NOT match the other even with identical text
    assert not is_same_candidate({'phrase_id': 1, 'text': 'A'}, {'phrase_id': None, 'text': 'A'})
    assert not is_same_candidate({'phrase_id': None, 'text': 'A'}, {'phrase_id': 1, 'text': 'A'})

    # Both missing phrase ID matches by trimmed text
    assert is_same_candidate({'phrase_id': None, 'text': '  A  '}, {'phrase_id': None, 'text': 'A'})
    assert not is_same_candidate({'phrase_id': None, 'text': 'A'}, {'phrase_id': None, 'text': 'B'})

    # Composed matches only when both composed with same template and slot word
    assert is_same_candidate(
        {'composed': True, 'template_id': 1, 'slot_word_id': 2},
        {'composed': True, 'template_id': 1, 'slot_word_id': 2},
    )
    assert not is_same_candidate(
        {'composed': True, 'template_id': 1, 'slot_word_id': 2},
        {'composed': True, 'template_id': 1, 'slot_word_id': 3},
    )
    assert not is_same_candidate(
        {'composed': True, 'template_id': 1, 'slot_word_id': 2},
        {'composed': False, 'template_id': 1, 'slot_word_id': 2},
    )


def test_playback_cleanup_and_cancellation():
    api_code = (ROOT / 'web/src/api.js').read_text(encoding='utf-8')
    assert 'currentPlayId' in api_code, 'Expected currentPlayId token in api.js'
    assert 'URL.revokeObjectURL' in api_code, 'Expected URL.revokeObjectURL in api.js'
    assert 'stopAudio' in api_code, 'Expected stopAudio export in api.js'
    assert 'AbortError' in api_code, 'Expected AbortError handling in api.js'


def test_speak_screen_reliability_guards():
    speak_code = (ROOT / 'web/src/Speak.jsx').read_text(encoding='utf-8')
    assert 'activeRecordIdRef' in speak_code, 'Expected activeRecordIdRef in Speak.jsx'
    assert 'isMountedRef' in speak_code, 'Expected isMountedRef in Speak.jsx'
    assert 'confirmingSampleRef' in speak_code, 'Expected confirmingSampleRef in Speak.jsx'
    assert 'aria-live="polite"' in speak_code, 'Expected aria-live polite region in Speak.jsx'


if __name__ == '__main__':
    test_speak_i18n_parity()
    test_speak_jsx_translation_calls()
    test_no_em_dashes_in_source()
    test_candidate_key_uniqueness()
    test_candidate_matching_logic()
    test_playback_cleanup_and_cancellation()
    test_speak_screen_reliability_guards()
    print('All speak reliability verification tests passed!')

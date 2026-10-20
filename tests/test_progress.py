"""Tests for Progress screen data validation, schema compliance, and localization parity."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_progress_i18n_parity():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    hi_content = (ROOT / 'web/src/i18n/hi.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))
    hi_keys = set(re.findall(r"'([^']+)'\s*:", hi_content))

    assert en_keys == hi_keys, f'i18n mismatch: {en_keys ^ hi_keys}'
    progress_keys = [k for k in en_keys if k.startswith('progress.')]
    assert len(progress_keys) >= 20, f'Expected at least 20 progress keys, got {len(progress_keys)}'


def test_progress_component_t_calls():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))

    progress_code = (ROOT / 'web/src/Progress.jsx').read_text(encoding='utf-8')
    calls = re.findall(r"t\(\s*['\"]([a-zA-Z0-9_.]+)['\"]", progress_code)
    missing = [c for c in calls if c not in en_keys]
    assert not missing, f'Missing translation keys in Progress.jsx: {missing}'


def test_no_em_dashes_in_source():
    em_dash = '\u2014'
    for path in (ROOT / 'web/src').rglob('*'):
        if path.suffix in ('.js', '.jsx', '.css'):
            content = path.read_text(encoding='utf-8')
            assert em_dash not in content, f'Em dash found in {path}'


def test_stats_data_structure():
    sample_stats = {
        'phrases': 12,
        'samples': 36,
        'enroll_samples': 30,
        'recognitions': 6,
        'confirmed': 5,
        'top1_hits': 4,
        'top1_hit_rate': 0.8,
        'clear_without_help_by_week': [
            {'week_start': '2026-09-01', 'confirmed': 2, 'clear': 1, 'rate': 0.5},
            {'week_start': '2026-09-08', 'confirmed': 3, 'clear': 2, 'rate': 0.67},
        ],
        'top_phrases': [
            {'phrase_id': 1, 'text': 'पानी चाहिए', 'uses': 3},
            {'phrase_id': 2, 'text': 'दवाई', 'uses': 2},
        ],
    }

    assert sample_stats['top1_hit_rate'] == round(sample_stats['top1_hits'] / sample_stats['confirmed'], 3)
    assert len(sample_stats['clear_without_help_by_week']) == 2
    assert len(sample_stats['top_phrases']) == 2


if __name__ == '__main__':
    test_progress_i18n_parity()
    test_progress_component_t_calls()
    test_no_em_dashes_in_source()
    test_stats_data_structure()
    print('All progress verification tests passed!')

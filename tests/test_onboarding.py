"""Tests for Sunn onboarding flow, persistence, route registration, and localization parity."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_onboarding_i18n_parity():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    hi_content = (ROOT / 'web/src/i18n/hi.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))
    hi_keys = set(re.findall(r"'([^']+)'\s*:", hi_content))

    assert en_keys == hi_keys, f'i18n mismatch: {en_keys ^ hi_keys}'
    onboarding_keys = [k for k in en_keys if k.startswith('onboarding.')]
    assert len(onboarding_keys) >= 20, f'Expected at least 20 onboarding keys, got {len(onboarding_keys)}'


def test_onboarding_component_t_calls():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))

    onboarding_code = (ROOT / 'web/src/Onboarding.jsx').read_text(encoding='utf-8')
    calls = re.findall(r"t\(\s*['\"]([a-zA-Z0-9_.]+)['\"]", onboarding_code)
    missing = [c for c in calls if c not in en_keys]
    assert not missing, f'Missing translation keys in Onboarding.jsx: {missing}'

    settings_code = (ROOT / 'web/src/Settings.jsx').read_text(encoding='utf-8')
    settings_calls = [c for c in re.findall(r"t\(\s*['\"](onboarding\.[a-zA-Z0-9_.]+)['\"]", settings_code)]
    missing_settings = [c for c in settings_calls if c not in en_keys]
    assert not missing_settings, f'Missing translation keys in Settings.jsx: {missing_settings}'


def test_no_em_dashes_in_source():
    em_dash = '\u2014'
    for path in (ROOT / 'web/src').rglob('*'):
        if path.suffix in ('.js', '.jsx', '.css'):
            content = path.read_text(encoding='utf-8')
            assert em_dash not in content, f'Em dash found in {path}'


def test_onboarding_persistence_key():
    prefs_code = (ROOT / 'web/src/prefs.js').read_text(encoding='utf-8')
    assert 'sunn.onboarded.' in prefs_code, 'Expected sunn.onboarded. prefix in prefs.js'
    assert 'isOnboarded' in prefs_code, 'Expected isOnboarded export in prefs.js'
    assert 'setOnboarded' in prefs_code, 'Expected setOnboarded export in prefs.js'


def test_onboarding_route_registered():
    app_code = (ROOT / 'web/src/App.jsx').read_text(encoding='utf-8')
    assert "path: 'onboarding'" in app_code, 'Expected onboarding route in App.jsx'
    assert 'Onboarding' in app_code, 'Expected Onboarding component imported in App.jsx'


def test_onboarding_steps_and_accessibility():
    onboarding_code = (ROOT / 'web/src/Onboarding.jsx').read_text(encoding='utf-8')
    assert 'TOTAL_STEPS = 4' in onboarding_code, 'Expected 4 total steps'
    assert 'aria-live="polite"' in onboarding_code, 'Expected aria-live polite announcement'
    assert 'step-meter' in onboarding_code, 'Expected step-meter indicator'
    assert 'handleFinish' in onboarding_code, 'Expected handleFinish function'


if __name__ == '__main__':
    test_onboarding_i18n_parity()
    test_onboarding_component_t_calls()
    test_no_em_dashes_in_source()
    test_onboarding_persistence_key()
    test_onboarding_route_registered()
    test_onboarding_steps_and_accessibility()
    print('All onboarding verification tests passed!')

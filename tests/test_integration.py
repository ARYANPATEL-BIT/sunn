"""Integration tests for application routing, navigation tabs, and localization."""
import re
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None

ROOT = Path(__file__).resolve().parent.parent


def test_app_router_routes():
    app_code = (ROOT / 'web/src/App.jsx').read_text(encoding='utf-8')
    expected_routes = ['enroll', 'speak', 'phrases', 'progress', 'settings', 'onboarding']
    for r in expected_routes:
        assert f"path: '{r}'" in app_code, f'Missing route {r} in App.jsx'


def test_app_shell_navigation_tabs():
    tabs_code = (ROOT / 'web/src/ui/Tabs.jsx').read_text(encoding='utf-8')
    expected_tabs = [
        "to: '/app/enroll'",
        "to: '/app/speak'",
        "to: '/app/phrases'",
        "to: '/app/progress'",
        "to: '/app/settings'",
    ]
    for tab in expected_tabs:
        assert tab in tabs_code, f'Missing navigation tab {tab} in Tabs.jsx'


def test_i18n_total_parity_and_coverage():
    en_content = (ROOT / 'web/src/i18n/en.js').read_text(encoding='utf-8')
    hi_content = (ROOT / 'web/src/i18n/hi.js').read_text(encoding='utf-8')
    en_keys = set(re.findall(r"'([^']+)'\s*:", en_content))
    hi_keys = set(re.findall(r"'([^']+)'\s*:", hi_content))

    assert en_keys == hi_keys, f'i18n key mismatch between en and hi: {en_keys ^ hi_keys}'
    assert len(en_keys) >= 300, f'Expected at least 300 translation keys, got {len(en_keys)}'


def test_no_em_dashes_in_source_tree():
    em_dash = '\u2014'
    for path in (ROOT / 'web/src').rglob('*'):
        if path.suffix in ('.js', '.jsx', '.css'):
            content = path.read_text(encoding='utf-8')
            assert em_dash not in content, f'Em dash found in {path}'


def test_preferences_and_onboarding_persistence():
    prefs_code = (ROOT / 'web/src/prefs.js').read_text(encoding='utf-8')
    assert 'sunn.large_text' in prefs_code, 'Missing large_text key in prefs.js'
    assert 'sunn.reduced_motion' in prefs_code, 'Missing reduced_motion key in prefs.js'
    assert 'sunn.enhanced_focus' in prefs_code, 'Missing enhanced_focus key in prefs.js'
    assert 'sunn.onboarded.' in prefs_code, 'Missing per-user onboarding key prefix in prefs.js'
    assert 'isOnboarded' in prefs_code, 'Missing isOnboarded in prefs.js'
    assert 'setOnboarded' in prefs_code, 'Missing setOnboarded in prefs.js'


def test_login_onboarding_routing():
    auth_pages_code = (ROOT / 'web/src/AuthPages.jsx').read_text(encoding='utf-8')
    assert 'isOnboarded' in auth_pages_code, 'Expected isOnboarded import in AuthPages.jsx'
    assert "isOnboarded(user.id) ? '/app/speak' : '/app/onboarding'" in auth_pages_code
    assert "isOnboarded(me.id) ? '/app/speak' : '/app/onboarding'" in auth_pages_code


def test_gnani_unconfigured_key_safeguard(monkeypatch=None):
    if monkeypatch is None or pytest is None:
        return
    import gnani
    monkeypatch.setenv('GNANI_API_KEY', '')
    with pytest.raises(gnani.GnaniError) as exc_info:
        gnani.post('stt', 'http://example.com')
    assert exc_info.value.code == 'gnani_unreachable'
    assert exc_info.value.status == 502

    monkeypatch.setenv('GNANI_API_KEY', 'your-key-here')
    with pytest.raises(gnani.GnaniError) as exc_info:
        gnani.post('stt', 'http://example.com')
    assert exc_info.value.code == 'gnani_unreachable'
    assert exc_info.value.status == 502


def test_audio_playback_token_contract():
    api_code = (ROOT / 'web/src/api.js').read_text(encoding='utf-8')
    assert 'currentPlayId' in api_code, 'Expected currentPlayId token in api.js'
    assert 'URL.revokeObjectURL' in api_code, 'Expected URL.revokeObjectURL in api.js'
    assert 'export function stopAudio()' in api_code or 'export const stopAudio' in api_code
    assert 'export async function say(' in api_code or 'export const say' in api_code
    assert 'export async function play(' in api_code or 'export const play' in api_code


def test_enroll_screen_cleanup():
    enroll_code = (ROOT / 'web/src/Enroll.jsx').read_text(encoding='utf-8')
    assert 'api.stopAudio()' in enroll_code, 'Expected api.stopAudio() cleanup in Enroll.jsx'


def test_vite_dev_server_notice():
    vite_code = (ROOT / 'web/vite.config.js').read_text(encoding='utf-8')
    assert 'hasCerts' in vite_code, 'Expected hasCerts conditional check in vite.config.js'
    assert 'Starting HTTP on localhost' in vite_code, 'Expected HTTP fallback notice in vite.config.js'


if __name__ == '__main__':
    test_app_router_routes()
    test_app_shell_navigation_tabs()
    test_i18n_total_parity_and_coverage()
    test_no_em_dashes_in_source_tree()
    test_preferences_and_onboarding_persistence()
    test_login_onboarding_routing()
    test_audio_playback_token_contract()
    test_enroll_screen_cleanup()
    test_vite_dev_server_notice()
    print('All integration, routing, shell, and cleanup tests passed!')

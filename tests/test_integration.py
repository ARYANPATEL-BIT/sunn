"""Integration tests for application routing, navigation tabs, and localization."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_app_router_routes():
    app_code = (ROOT / 'web/src/App.jsx').read_text(encoding='utf-8')
    expected_routes = ['enroll', 'speak', 'phrases', 'progress', 'settings', 'onboarding']
    for r in expected_routes:
        assert f"path: '{r}'" in app_code, f'Missing route {r} in App.jsx'


def test_app_shell_navigation_tabs():
    shell_code = (ROOT / 'web/src/AppShell.jsx').read_text(encoding='utf-8')
    expected_tabs = [
        "to: '/app/enroll'",
        "to: '/app/speak'",
        "to: '/app/phrases'",
        "to: '/app/progress'",
        "to: '/app/settings'",
    ]
    for tab in expected_tabs:
        assert tab in shell_code, f'Missing navigation tab {tab} in AppShell.jsx'


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


if __name__ == '__main__':
    test_app_router_routes()
    test_app_shell_navigation_tabs()
    test_i18n_total_parity_and_coverage()
    test_no_em_dashes_in_source_tree()
    test_preferences_and_onboarding_persistence()
    test_login_onboarding_routing()
    print('Routing, shell, and persistence integration tests passed!')

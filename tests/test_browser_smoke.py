"""Browser smoke checks on running local server, opt-in via BROWSER_BASE_URL."""
import os
import pytest


@pytest.mark.skipif(not os.environ.get('BROWSER_BASE_URL'), reason='BROWSER_BASE_URL not set')
def test_public_navigation_and_mobile_layout():
    from playwright.sync_api import sync_playwright
    base = os.environ['BROWSER_BASE_URL']
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
        for width in (390, 768, 1366):
            page = browser.new_page(viewport={'width': width, 'height': 850})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.get_by_role('link', name='Mulai Analisis').click()
            assert page.url.endswith('/login')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.get_by_role('link', name='Daftar').click()
            assert page.url.endswith('/register')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.close()
        browser.close()
    assert not errors

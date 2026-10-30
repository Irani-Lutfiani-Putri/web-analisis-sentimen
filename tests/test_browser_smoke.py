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
            login_styles = page.evaluate("""() => {
                const header = getComputedStyle(document.querySelector('.public-header'));
                const body = getComputedStyle(document.body);
                const button = getComputedStyle(document.querySelector('.public-login-link'));
                const card = getComputedStyle(document.querySelector('.login-card'));
                return {
                    headerBackground: header.backgroundColor,
                    bodyBackground: body.backgroundColor,
                    buttonBackground: button.backgroundColor,
                    buttonMinHeight: button.minHeight,
                    cardShadow: card.boxShadow,
                    registerPrompt: document.body.textContent.includes('Belum punya akun?'),
                };
            }""")
            assert login_styles['headerBackground'] == 'rgb(249, 208, 205)'
            assert login_styles['bodyBackground'] == 'rgb(255, 255, 255)'
            assert login_styles['buttonBackground'] == 'rgb(241, 62, 147)'
            assert float(login_styles['buttonMinHeight'].removesuffix('px')) >= 44
            assert login_styles['cardShadow'] != 'none'
            assert login_styles['registerPrompt'] is False
            page.locator('#email').fill('invalid')
            page.locator('#password').evaluate("input => input.removeAttribute('required')")
            with page.expect_navigation():
                page.locator('form').evaluate('form => form.requestSubmit()')
            assert page.locator('#email-error').is_visible()
            assert page.locator('#password-error').is_visible()
            assert page.locator('#email').get_attribute('aria-invalid') == 'true'
            assert page.locator('#password').get_attribute('aria-invalid') == 'true'
            assert page.locator('#email').evaluate('node => node === document.activeElement')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.goto(base + '/register')
            assert page.url.endswith('/register')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            page.close()
        browser.close()
    assert not errors

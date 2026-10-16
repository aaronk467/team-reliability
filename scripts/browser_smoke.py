"""Exercise real dashboard analysis and the browser-local open-call lifecycle.

Requires Playwright and Chromium. Run against a locally started production app:
  python scripts/browser_smoke.py --url http://127.0.0.1:8002
Use --ca-forward only in TLS-inspecting workspaces whose Chromium trust store
lacks the installed proxy CA. Every forwarded request retains TLS verification.
"""
import argparse
import ssl
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8002')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--ca-forward', action='store_true')
parser.add_argument('--screenshot')
args = parser.parse_args()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, timezone_id='UTC')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    if args.ca_forward:
        context = ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
        def forward(route):
            req = route.request
            headers = {k: v for k, v in req.headers.items() if k.lower() not in {'host', 'content-length', 'accept-encoding'}}
            request = urllib.request.Request(req.url, data=req.post_data_buffer, headers=headers, method=req.method)
            try:
                response = urllib.request.urlopen(request, context=context, timeout=55)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                data = response.read()
                headers = {k: v for k, v in response.headers.items() if k.lower() not in {'content-length', 'content-encoding', 'transfer-encoding', 'connection'}}
                route.fulfill(status=response.code, headers=headers, body=data)
        page.route('**/*', forward)
    def analyze_response(action):
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/analyze'), timeout=60000) as pending:
            action()
        response = pending.value
        assert response.status == 200, response.text()
        return response.json()
    initial = analyze_response(lambda: page.goto(args.url, wait_until='networkidle', timeout=60000))
    assert initial['priority'] == 'high' and initial['imr_scale'] == 'log' and initial['aggregation_days'] == 7
    assert initial['summary']['count'] == 720
    assert page.locator('svg[role=img]').count() == 3
    for name, late_rate, signals in [('stable', .46, 0), ('improvement', .06, 3), ('south_shift', 1., 4)]:
        result = analyze_response(lambda: page.locator('#dataset').select_option(name))
        south = next(z for z in result['zones'] if z['zone'] == 'South')
        assert south['comparison']['monitoring']['late_rate'] == late_rate
        assert sum(p['signal'] for p in south['p_chart']['points'] if not p['in_baseline']) == signals
    daily = analyze_response(lambda: page.locator('#aggregation').select_option('1'))
    assert not any(p['signal'] for z in daily['zones'] if z['zone'] == 'South' for p in z['p_chart']['points'] if not p['in_baseline'])
    analyze_response(lambda: page.locator('#aggregation').select_option('7'))
    page.get_by_role('button', name='Start dispatch', exact=True).click()
    form = page.locator('form.open-form')
    form.locator('[name=id]').fill('SMOKE-OPEN')
    form.locator('[name=zone]').fill('South')
    past = page.evaluate('new Date(Date.now()-20*60000).toISOString().slice(0,16)')
    form.locator('[name=dispatched_at]').fill(past)
    form.get_by_role('button', name='Start dispatch', exact=True).click()
    page.get_by_text('1 high open · 1 overdue', exact=True).wait_for()
    assert page.get_by_text('720', exact=True).is_visible(), 'Open call must not enter completed denominator'
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    page.get_by_text('1 high open · 1 overdue', exact=True).wait_for()
    page.get_by_role('button', name='Log completed call', exact=True).click()
    modal = page.get_by_role('dialog')
    modal.locator('[name=id]').fill(' SMOKE-OPEN ')
    modal.locator('[name=zone]').fill('South')
    modal.locator('[name=dispatched_at]').fill(past)
    modal.locator('[name=arrived_at]').fill(page.evaluate('new Date().toISOString().slice(0,16)'))
    modal.get_by_role('button', name='Add completed call', exact=True).click()
    modal.get_by_role('alert').filter(has_text='belongs to an open dispatch').wait_for()
    modal.get_by_role('button', name='Close', exact=True).click()
    row = page.locator('.open-row').filter(has_text='SMOKE-OPEN')
    row.get_by_role('button', name='Use now', exact=True).click()
    analyze_response(lambda: row.get_by_role('button', name='Record arrival', exact=True).click())
    page.get_by_text('0 high open · 0 overdue', exact=True).wait_for()
    page.get_by_text('721', exact=True).wait_for()
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    page.get_by_text('721', exact=True).wait_for()
    page.get_by_text('0 high open · 0 overdue', exact=True).wait_for()
    with page.expect_download() as download:
        page.get_by_title('Export records').click()
    assert download.value.suggested_filename.endswith('.csv')
    page.locator('input[type=file]').set_input_files({'name': 'bad.csv', 'mimeType': 'text/csv', 'buffer': b'wrong,header\n1,2\n'})
    page.get_by_role('alert').filter(has_text='CSV needs').wait_for()
    page.evaluate("localStorage.setItem('responsewatch:pending:south_shift', '{unreadable')")
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    page.get_by_role('alert').filter(has_text='Saved open calls could not be read').wait_for()
    assert page.evaluate("localStorage.getItem('responsewatch:pending:south_shift')") == '{unreadable'
    assert page.get_by_role('button', name='Start dispatch', exact=True).is_disabled()
    page.once('dialog', lambda dialog: dialog.accept())
    page.get_by_role('button', name='Clear saved open calls', exact=True).click()
    assert page.evaluate("localStorage.getItem('responsewatch:pending:south_shift')") is None
    page.set_viewport_size({'width': 390, 'height': 844})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Mobile page overflows'
    assert not errors, errors
    if args.screenshot:
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.reload(wait_until='networkidle')
        page.screenshot(path=args.screenshot, full_page=True)
    browser.close()
print('PASS: exact/log defaults, all demo outcomes, daily/weekly controls, open→overdue→arrival lifecycle, reload persistence, denominator integrity, duplicate-ID rejection, corrupt-storage preservation/recovery, CSV export/error and mobile layout; no page errors.')

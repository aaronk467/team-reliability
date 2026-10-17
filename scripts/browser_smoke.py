"""Exercise dashboard tabs, real analysis, and the browser-local open-call lifecycle.

Requires Playwright and Chromium. Run against a locally started production app:
  python scripts/browser_smoke.py --url http://127.0.0.1:8002
Use --ca-forward only in TLS-inspecting workspaces whose Chromium trust store
lacks the installed proxy CA. Every forwarded request retains TLS verification.
"""
import argparse
import csv
import io
import ssl
import urllib.error
import urllib.request
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8002')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--ca-forward', action='store_true')
parser.add_argument('--screenshot')
args = parser.parse_args()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=None if args.browser=='auto' else args.browser, headless=True, args=['--no-sandbox'])
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
    def go_tab(name):
        tab = page.get_by_role('tab', name=name, exact=True)
        tab.click()
        assert tab.get_attribute('aria-selected') == 'true', name
    initial = analyze_response(lambda: page.goto(args.url, wait_until='networkidle', timeout=60000))
    assert initial['priority'] == 'high' and initial['imr_scale'] == 'log' and initial['aggregation_days'] == 7
    assert initial['summary']['count'] == 845
    assert initial['p_method']=='beta_binomial'
    assert initial['delay_patterns']['reason_recorded_count'] > 0
    assert page.get_by_role('tab', name='Key statistics', exact=True).get_attribute('aria-selected') == 'true'
    assert page.locator('svg[role=img]:visible').count() == 3
    assert not page.get_by_role('button', name='Start dispatch', exact=True).is_visible()
    assert not page.get_by_role('heading', name='Delay patterns · investigation context').is_visible()
    for key, expected in [('ArrowRight', 'Dispatch workspace'), ('ArrowRight', 'Supporting analysis'), ('Home', 'Key statistics'), ('End', 'Supporting analysis'), ('ArrowRight', 'Key statistics'), ('ArrowLeft', 'Supporting analysis')]:
        page.locator('[role=tab][aria-selected=true]').press(key)
        selected_tab = page.get_by_role('tab', name=expected, exact=True)
        assert selected_tab.get_attribute('aria-selected') == 'true', f'{key} must select {expected}'
        assert selected_tab.evaluate('(element) => element === document.activeElement'), 'Keyboard navigation must move focus'
    page.locator('#focus-zone').select_option('North')
    for name in ['Key statistics', 'Dispatch workspace', 'Supporting analysis']:
        go_tab(name)
        assert page.locator('#focus-zone').input_value() == 'North', 'Focus zone must be shared across tabs'
    page.locator('#focus-zone').select_option('South')
    go_tab('Key statistics')
    for name, late_rate, signals in [('stable', 50/107, 0), ('improvement', 10/107, 2), ('south_shift', 1., 4)]:
        result = analyze_response(lambda: page.locator('#dataset').select_option(name))
        south = next(z for z in result['zones'] if z['zone'] == 'South')
        assert south['comparison']['monitoring']['late_rate'] == late_rate
        assert sum(p['signal'] for p in south['p_chart']['points'] if not p['in_baseline']) == signals
    daily = analyze_response(lambda: page.locator('#aggregation').select_option('1'))
    assert daily['aggregation_days']==1
    analyze_response(lambda: page.locator('#aggregation').select_option('7'))
    go_tab('Supporting analysis')
    assert page.get_by_role('heading',name='Delay patterns · investigation context').is_visible()
    page.get_by_label('Delay patterns scope').select_option('all')
    page.get_by_label('Delay patterns scope').select_option('zone')
    analyze_response(lambda: page.locator('#p-method').select_option('exact_binomial'))
    analyze_response(lambda: page.locator('#p-method').select_option('beta_binomial'))
    go_tab('Dispatch workspace')
    page.locator('[name=review-owner]').fill('reviewer-01')
    page.locator('[name=review-action]').fill('Unsaved review draft')
    go_tab('Key statistics')
    assert not page.locator('[name=review-owner]').is_visible()
    go_tab('Supporting analysis')
    go_tab('Dispatch workspace')
    assert page.locator('[name=review-owner]').input_value() == 'reviewer-01', 'Tab switching must preserve unsaved review owner'
    assert page.locator('[name=review-action]').input_value() == 'Unsaved review draft', 'Tab switching must preserve unsaved review action'
    page.locator('[name=review-action]').fill('')
    page.locator('[name=review-status]').select_option('resolved')
    page.get_by_role('button',name='Save review',exact=True).click()
    page.get_by_role('alert').filter(has_text='Document the action').wait_for()
    page.locator('[name=review-action]').fill('Audit timestamps and review available units')
    page.get_by_role('button',name='Save review',exact=True).click()
    page.get_by_role('status').filter(has_text='Browser-local review saved').wait_for()
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    assert page.get_by_role('tab', name='Dispatch workspace', exact=True).get_attribute('aria-selected') == 'true', 'Refresh must retain the active tab'
    go_tab('Dispatch workspace')
    page.locator('#focus-zone').select_option('South')
    expect(page.locator('[name=review-status]')).to_have_value('resolved')
    page.get_by_role('button', name='Start dispatch', exact=True).click()
    form = page.locator('form.open-form')
    form.locator('[name=id]').fill('SMOKE-OPEN')
    form.locator('[name=zone]').fill('South')
    past = page.evaluate('new Date(Date.now()-20*60000).toISOString().slice(0,16)')
    form.locator('[name=dispatched_at]').fill(past)
    go_tab('Key statistics')
    go_tab('Dispatch workspace')
    assert form.locator('[name=id]').input_value() == 'SMOKE-OPEN', 'Tab switching must preserve unsaved dispatch ID'
    assert form.locator('[name=zone]').input_value() == 'South'
    assert form.locator('[name=dispatched_at]').input_value() == past
    form.get_by_role('button', name='Start dispatch', exact=True).click()
    page.get_by_text('1 high open · 1 overdue', exact=True).wait_for()
    go_tab('Key statistics')
    assert page.get_by_text('845', exact=True).is_visible(), 'Open call must not enter completed denominator'
    go_tab('Dispatch workspace')
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    go_tab('Dispatch workspace')
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
    arrival_draft = row.locator('[name=arrived_at]').input_value()
    row.locator('[name=delay_reason]').fill('Smoke review context')
    go_tab('Supporting analysis')
    go_tab('Key statistics')
    go_tab('Dispatch workspace')
    assert row.locator('[name=arrived_at]').input_value() == arrival_draft, 'Tab switching must preserve arrival draft'
    assert row.locator('[name=delay_reason]').input_value() == 'Smoke review context'
    arrived = analyze_response(lambda: row.get_by_role('button', name='Record arrival', exact=True).click())
    page.get_by_text('0 high open · 0 overdue', exact=True).wait_for()
    point = next(p for z in arrived['zones'] if z['zone'] == 'South' for p in z['imr']['points'] if p['id'] == 'SMOKE-OPEN')
    assert not point['in_baseline']
    page.get_by_label('Find completed call', exact=True).fill('SMOKE-OPEN')
    page.get_by_label('Completed response to inspect', exact=True).select_option('SMOKE-OPEN')
    inspected = page.get_by_label('Selected completed response', exact=True)
    assert inspected.get_by_text(f"{point['minutes']:.2f} min", exact=True).is_visible()
    assert inspected.get_by_text('Above service target', exact=True).is_visible()
    assert inspected.get_by_text('South · high priority · Monitoring period', exact=True).is_visible()
    assert inspected.get_by_text('Outside individual limits' if point['signal'] else 'Inside individual limits', exact=True).is_visible()
    go_tab('Key statistics')
    go_tab('Dispatch workspace')
    assert page.get_by_label('Completed response to inspect', exact=True).input_value() == 'SMOKE-OPEN', 'Tab switching must preserve selected-call inspection'
    go_tab('Key statistics')
    page.get_by_text('846', exact=True).wait_for()
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    go_tab('Key statistics')
    page.get_by_text('846', exact=True).wait_for()
    go_tab('Dispatch workspace')
    page.get_by_text('0 high open · 0 overdue', exact=True).wait_for()
    with page.expect_download() as download:
        page.get_by_title('Export records').click()
    assert download.value.suggested_filename.endswith('.csv')
    exported=open(download.value.path()).read()
    exported_rows=list(csv.DictReader(io.StringIO(exported)))
    assert all(field in exported_rows[0] for field in ['shift','traffic','units_available'])
    assert any(r['shift']=='day' for r in exported_rows)
    page.locator('input[type=file]').set_input_files({'name': 'bad.csv', 'mimeType': 'text/csv', 'buffer': b'wrong,header\n1,2\n'})
    page.get_by_role('alert').filter(has_text='CSV needs').wait_for()
    page.evaluate("localStorage.setItem('responsewatch:pending:south_shift', '{unreadable')")
    analyze_response(lambda: page.reload(wait_until='networkidle'))
    go_tab('Dispatch workspace')
    page.get_by_role('alert').filter(has_text='Saved open calls could not be read').wait_for()
    assert page.evaluate("localStorage.getItem('responsewatch:pending:south_shift')") == '{unreadable'
    assert page.get_by_role('button', name='Start dispatch', exact=True).is_disabled()
    page.once('dialog', lambda dialog: dialog.accept())
    page.get_by_role('button', name='Clear saved open calls', exact=True).click()
    assert page.evaluate("localStorage.getItem('responsewatch:pending:south_shift')") is None
    edge_csv = b'id,zone,priority,dispatched_at,arrived_at\nEDGE-BASE,Edge,high,2026-01-01T00:00:00Z,2026-01-01T00:08:00Z\nEDGE-MONITOR,Edge,high,2026-01-21T00:00:00Z,2026-01-21T00:08:00Z\n'
    edge = analyze_response(lambda: page.locator('input[type=file]').set_input_files({'name': 'edge.csv', 'mimeType': 'text/csv', 'buffer': edge_csv}))
    assert edge['zones'][0]['imr']['ucl'] is None, 'One baseline call cannot establish I-MR limits'
    go_tab('Dispatch workspace')
    page.get_by_label('Find completed call', exact=True).fill('EDGE-MONITOR')
    page.get_by_label('Completed response to inspect', exact=True).select_option('EDGE-MONITOR')
    inspected = page.get_by_label('Selected completed response', exact=True)
    assert inspected.get_by_text('At service target', exact=True).is_visible(), 'Exactly eight minutes meets the target'
    assert inspected.get_by_text('Individual limits unavailable', exact=True).is_visible(), 'Missing limits must not produce an inside/outside classification'
    page.set_viewport_size({'width': 390, 'height': 844})
    for name in ['Key statistics', 'Dispatch workspace', 'Supporting analysis']:
        go_tab(name)
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Mobile page overflows on {name}'
    assert not errors, errors
    if args.screenshot:
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.reload(wait_until='networkidle')
        go_tab('Key statistics')
        page.screenshot(path=args.screenshot, full_page=True)
    browser.close()
print('PASS: accessible mouse/keyboard tab navigation, shared focus zone, sparse-baseline and exact-target inspection, unsaved dispatch/arrival/review draft preservation across tabs, completed-call placement matched to API flags, predictive/log defaults, model switching, delay context, review workflow, optional-column export, all demo outcomes, daily/weekly controls, open→overdue→arrival lifecycle, reload persistence, denominator integrity, duplicate-ID rejection, corrupt-storage preservation/recovery, CSV export/error and mobile layout; no page errors.')

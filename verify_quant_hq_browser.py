"""Read-only live browser acceptance. Fault injection is test-only, never server data.
Run: TMPDIR=<scratch> PYTHONPATH= python3 verify_quant_hq_browser.py
"""
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'agent-reports' / 'quant-hq-browser'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://127.0.0.1:8490'
report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'checks': [], 'screenshots': [], 'console_errors': [], 'page_errors': [], 'fault_injection': 'Browser routes only. Not production feeds.'}


def check(name, condition, detail=None):
    report['checks'].append({'name': name, 'passed': bool(condition), 'detail': detail})
    if not condition:
        raise AssertionError(name + ': ' + str(detail))


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    page = context.new_page()
    page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
    # Failed HTTP responses during deliberate failure injection are expected;
    # collect unexpected JS console exceptions, not Chromium network diagnostics.
    page.on('console', lambda msg: report['console_errors'].append(msg.text) if msg.type == 'error' and 'Failed to load resource' not in msg.text else None)
    try:
        page.goto(BASE, wait_until='networkidle')
        page.wait_for_function("document.querySelector('#equity').textContent!=='Unavailable'", timeout=30000)
        page.wait_for_function("document.querySelector('#overview-chart-message').textContent.includes('real MT5 bars')", timeout=30000)
        real_state = page.request.get(BASE + '/api/state').json()
        report['account_scope'] = {'login': real_state['account']['login'], 'server': real_state['account']['server'], 'trade_mode': real_state['account']['trade_mode']}
        report['snapshot'] = {key: real_state[key] for key in ('observed_at', 'account', 'mt5', 'day_pl')}
        check('demo account scope', real_state['account']['trade_mode'] == 0)
        check('real equity rendered', abs(float(page.locator('#equity').inner_text().replace(',', '')) - real_state['account']['equity']) < .02)
        check('real position count', int(page.locator('#position-count').inner_text()) == len(real_state['positions']))
        check('currency rendered', real_state['account']['currency'] in page.locator('.currency').first.inner_text())
        check('chart rendered accessible description', 'broker candles' in page.locator('#overview-chart').get_attribute('aria-label'))
        page.keyboard.press('Tab')
        check('keyboard focus visible', page.evaluate("getComputedStyle(document.activeElement).outlineStyle !== 'none'"))
        page.locator('#positions th button').filter(has_text='P/L').click()
        pl = page.locator('#positions tbody tr td:nth-child(6)').all_text_contents()
        check('position table numeric sort', [float(x) for x in pl] == sorted(float(x) for x in pl))
        page.locator('#positions tbody button').first.click()
        page.wait_for_function("!document.querySelector('#trace').hidden && !document.querySelector('#trace-body').textContent.includes('Loading recorded')")
        check('real ticket evidence drawer', len(page.locator('#trace-body').inner_text()) > 20)
        check('drawer keyboard focus', page.locator('#trace-close').evaluate('(e)=>e===document.activeElement'))
        page.keyboard.press('Escape')
        check('drawer escape closes and restores focus', page.locator('#trace').is_hidden() and page.locator('#positions tbody button').first.evaluate('(e)=>e===document.activeElement'))
        page.locator('#view-overview .positions-panel details > summary').click()
        check('risk methodology expanded', 'Mark-to-stop estimate' in page.locator('#risk-summary').inner_text())
        page.locator('#view-overview .positions-panel details > summary').click()
        for name, width, height in [('desktop',1440,1000), ('tablet',820,1180), ('phone',390,844)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_timeout(200)
            measure = page.evaluate('({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})')
            check(name + ' no page-wide overflow', measure['width'] == measure['scroll'], measure)
            check(name + ' chart has usable size', page.locator('#overview-chart').bounding_box()['width'] > 240)
            if name == 'phone':
                check('phone position summaries', page.locator('.position-cards').is_visible() and not page.locator('.position-table').is_visible())
                page.locator('.position-cards button').first.click()
                page.wait_for_timeout(200)
                check('phone detail sheet', page.locator('#trace').is_visible())
                page.keyboard.press('Escape')
            path = OUT / (name + '.png')
            page.screenshot(path=str(path), full_page=True)
            report['screenshots'].append(str(path))
        page.set_viewport_size({'width':1440,'height':1000})
        # Actual shell navigation and editor import, with no Pine execution.
        page.locator('#main-nav button[data-view="chart"]').click()
        page.wait_for_function("!document.querySelector('#view-chart').hidden")
        check('Pine simulation disabled with explanation', page.locator('#compile').is_disabled() and 'OS-isolated' in page.locator('#pine-boundary').inner_text())
        page.locator('#pine-file').set_input_files({'name':'browser-test.pine', 'mimeType':'text/plain', 'buffer':b'//@version=5\nindicator("browser test")\nplot(close)'})
        page.wait_for_timeout(500)
        check('local source import works', 'browser test' in (page.locator('#pine-editor').input_value() or ''))
        page.locator('#symbol').fill('EURUSD')
        page.locator('#chart-form button[type="submit"]').click()
        page.wait_for_function("document.querySelector('#chart-title').textContent==='EURUSD · H1'")
        check('chart symbol selection uses real broker data', 'real MT5 bars' in page.locator('#chart-message').inner_text())
        page.locator('#main-nav button[data-view="signals"]').click()
        page.wait_for_function("!document.querySelector('#view-signals').hidden")
        check('Signals reachable', page.locator('#inbox-table').is_visible())
        page.locator('#main-nav button[data-view="system"]').click()
        page.wait_for_function("document.querySelector('#system-content').textContent.includes('Process')")
        check('System real contract rendered', 'Loading' not in page.locator('#system-content').inner_text())
        page.locator('#main-nav button[data-view="overview"]').click()
        # Reviewed/deployed source identity; nonce is intentionally per-request.
        for name in ('hq-tokens.css','hq-shell.css','quant-matrix.css','quant-client.js','quant.js'):
            response = page.request.get(BASE + '/assets/' + name)
            check('deployed source ' + name, response.status == 200 and hashlib.sha256(response.body()).digest() == hashlib.sha256((ROOT/'cockpit_assets'/name).read_bytes()).digest())
        served_html = page.request.get(BASE).body().decode('utf-8')
        served_html = re.sub(r'<script>window\.__hqBootstrap="[a-f0-9]+";</script>', '', served_html)
        check('deployed HTML equals reviewed template', served_html == (ROOT/'cockpit_ui.html').read_text(encoding='utf-8'))
        for endpoint in ('state','events?limit=30&exclude=pnl_update','quant','health'):
            response = page.request.get(BASE+'/api/'+endpoint)
            check('live read-only '+endpoint, response.status == 200)
        check('authenticated unknown API is 404', page.request.get(BASE+'/api/does-not-exist').status == 404)
        response = page.request.post(BASE+'/api/pine/compile', data={'script':'//@version=5\nindicator("test")'}, headers={'Origin':BASE})
        check('live Pine fail-closed 503', response.status == 503 and 'OS-isolated' in response.json()['error'])
        # Only this browser sees these explicit fixtures.
        page.route('**/api/state', lambda route: route.fulfill(status=503, json={'ok':False,'error':'Intentional browser fault injection'}))
        page.locator('#refresh').click()
        page.wait_for_function("document.querySelector('#view-status').textContent.includes('Intentional browser fault injection')")
        check('failure visible and not healthy', page.locator('#connection').inner_text() == 'Degraded')
        page.unroute('**/api/state')
        fixture = json.loads(json.dumps(real_state))
        fixture['observed_at'] = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        page.route('**/api/state', lambda route: route.fulfill(json=fixture))
        page.locator('#refresh').click()
        page.wait_for_function("document.querySelector('#connection').textContent==='Stale'")
        check('stale observation visible', page.locator('#connection').inner_text() == 'Stale')
        page.unroute('**/api/state')
        fixture['observed_at'] = datetime.now(timezone.utc).isoformat()
        fixture['positions'] = []
        page.route('**/api/state', lambda route: route.fulfill(json=fixture))
        page.locator('#refresh').click()
        page.wait_for_function("document.querySelector('#positions').textContent.includes('No open positions')")
        check('confirmed empty differs from unavailable', 'No open positions' in page.locator('#positions').inner_text())
        page.unroute('**/api/state')
        fixture['mt5']['account_available'] = False
        fixture['mt5']['positions_available'] = False
        page.route('**/api/state', lambda route: route.fulfill(json=fixture))
        page.locator('#refresh').click()
        page.wait_for_function("document.querySelector('#equity').textContent==='Unavailable'")
        check('broker unavailability not zero', page.locator('#equity').inner_text()=='Unavailable' and 'unavailable' in page.locator('#positions').inner_text())
        page.unroute('**/api/state')
        page.locator('#refresh').click()
        page.wait_for_function("document.querySelector('#equity').textContent!=='Unavailable'")
        page.locator('#logout').click()
        page.wait_for_function("document.querySelector('#app').hidden")
        check('logout revokes authenticated requests', page.request.get(BASE+'/api/state').status==401)
        page.reload(wait_until='networkidle')
        page.wait_for_function("document.querySelector('#equity').textContent!=='Unavailable'")
        check('local reload auto-login recovers', not page.locator('#app').is_hidden())
        check('no JS page errors', not report['page_errors'], report['page_errors'])
        check('no unexpected console errors', not report['console_errors'], report['console_errors'])
    except Exception as exc:
        report['failure'] = str(exc)
        page.screenshot(path=str(OUT/'failure.png'), full_page=True)
        raise
    finally:
        report['passed'] = sum(item['passed'] for item in report['checks'])
        report['total'] = len(report['checks'])
        (OUT/'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        browser.close()
print(json.dumps({'passed':report['passed'],'total':report['total'],'evidence':str(OUT/'results.json')}))

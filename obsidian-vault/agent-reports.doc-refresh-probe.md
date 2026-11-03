---
slug: agent-reports.doc-refresh-probe
type: note
graph: gitnexus
---

"""Read-only loopback probes; no broker mutations or credential output."""
import http.cookiejar
import json
from pathlib import Path
import re
import urllib.request
from datetime import datetime, timezone

base = 'http://localhost:8490'
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
page = opener.open(base + '/').read().decode()
nonce = re.search(r'window\.__hqBootstrap="([0-9a-f]{32})"', page).group(1)
response = opener.open(urllib.request.Request(base + '/api/bootstrap', data=json.dumps({'nonce': nonce}).encode(), headers={'Content-Type': 'application/json', 'Origin': base}, method='POST'))
print('bootstrap', response.status, 'cookie flags', '; '.join(response.headers.get('Set-Cookie','').split(';')[1:]))
results = {'observed_at': datetime.now(timezone.utc).isoformat(), 'endpoints': {}}
for name in ['state', 'neural', 'identity', 'portfolio', 'candles?count=20', 'events?limit=30&exclude=pnl_update']:
    try:
        response = opener.open(base + '/api/' + name, timeout=20)
        data = json.loads(response.read())
        if name == 'state':
            data = {'account_mode': (data.get('account') or {}).get('trade_mode'), 'position_count': len(data.get('positions') or [])}
        elif name.startswith('events'):
            data = {'rows': len(data), 'pnl_update_rows': sum(e.get('type') == 'pnl_update' for e in data)}
        elif name.startswith('candles'):
            data = {k:v for k,v in data.items() if k != 'candles'} | {'bar_count':len(data.get('candles', []))}
        results['endpoints'][name] = {'http': response.status, 'data': data}
    except Exception as exc:
        results['endpoints'][name] = {'error': str(exc)}
print(json.dumps(results, indent=2))
Path(__file__).with_name('doc-refresh-live-probes.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


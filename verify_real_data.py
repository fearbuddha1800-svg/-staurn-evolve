"""Read-only live-source check. Never prints credentials or submits orders."""
from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
import re
from datetime import datetime, timezone
import urllib.error
import urllib.request


def verify(base='http://localhost:8490'):
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with client.open(base + '/', timeout=10) as response:
        page = response.read().decode('utf-8')
    match = re.search(r'window\.__hqBootstrap="([0-9a-f]{32})"', page)
    if not match:
        raise RuntimeError('Auto-login nonce unavailable')
    request = urllib.request.Request(base + '/api/bootstrap',
        data=json.dumps({'nonce': match.group(1)}).encode(), method='POST',
        headers={'Content-Type': 'application/json', 'Origin': base})
    with client.open(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError('Auto-login failed')
    records = []
    captured = {}
    paths = ['state', 'journal', 'mobile', 'neural', 'identity', 'portfolio', 'attribution',
             'inbox', 'health', 'strategies', 'events?limit=3&exclude=pnl_update',
             'candles?symbol=XAUUSD&timeframe=H1&count=30']
    for path in paths:
        try:
            with client.open(base + '/api/' + path, timeout=20) as response:
                payload = response.read()
                content_type = response.headers.get('Content-Type', '')
                value = json.loads(payload) if 'json' in content_type else payload.decode('utf-8')
                records.append({'path': path, 'status': response.status,
                                'content_type': content_type, 'bytes': len(payload)})
                captured[path] = value
        except urllib.error.HTTPError as exc:
            records.append({'path': path, 'status': exc.code})
        except Exception as exc:
            records.append({'path': path, 'error': type(exc).__name__})
    state = captured.get('state', {})
    journal = captured.get('journal', {})
    mobile = captured.get('mobile', '')
    mobile_text = mobile.get('html', '') if isinstance(mobile, dict) else str(mobile)
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'base': base,
            'requested': len(paths), 'ok': sum(r.get('status') == 200 for r in records),
            'records': records,
            'account_snapshot': {k: state.get('account', {}).get(k) for k in
                                 ('balance', 'equity', 'profit', 'trade_mode')},
            'positions_count': len(state.get('positions', [])),
            'journal_snapshot': journal if isinstance(journal, dict) else
                                {'legacy_list': True, 'records': len(journal)},
            'mobile_fiction_detected': [s for s in ('FX Flow', '10:42', 'EUR/USD Momentum',
                                                   'Paper Mode', '+0.4%') if s in mobile_text],
            'mobile_has_freshness_warning': 'freshness' in mobile_text.lower(),
            'portfolio_snapshot': captured.get('portfolio'),
            'note': 'Read-only API checks verify snapshots, not fresh weekend prices, fills, or live LLM availability.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='agent-reports/parent-live-real-data.json')
    args = parser.parse_args()
    result = verify()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('captured_at', 'requested', 'ok', 'account_snapshot',
                     'positions_count', 'mobile_fiction_detected', 'mobile_has_freshness_warning')}, indent=2))
    print('Evidence:', path.resolve())
    raise SystemExit(0 if result['ok'] == result['requested'] else 1)

"""Read-only LuxAlgo Whale Options adapter; never starts a synthetic feed."""
import json
from datetime import datetime, timezone
from urllib.request import urlopen

BASE_URL = 'http://127.0.0.1:8787'
MAX_RESPONSE = 2 * 1024 * 1024


def _get(path):
    with urlopen(BASE_URL + path, timeout=3) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError('Whale response exceeds limit')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('Invalid Whale response')
    return result


def whale_data():
    """Keep feed provenance intact, including an explicitly synthetic source."""
    result = {'package': 'whale-options', 'available': False, 'rows': [],
              'source_url': BASE_URL, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'broker_orders_enabled': False}
    try:
        status = _get('/api/status')
        events = _get('/api/events?limit=20')
        rows = events.get('events')
        if not isinstance(rows, list):
            raise ValueError('Invalid Whale events')
        result.update(available=True, status=status, rows=rows,
                      provenance='Upstream feed metadata retained in status; synthetic feeds are not market observations')
    except Exception as exc:
        result['reason'] = 'Whale Options service unavailable (' + type(exc).__name__ + '); configure a market-data feed at localhost:8787'
    return result

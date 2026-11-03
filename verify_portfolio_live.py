"""Read-only curl verification using the dashboard's loopback bootstrap flow."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    base = 'http://localhost:8490'
    with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as scratch:
        cookie = str(Path(scratch) / 'cockpit-cookie.txt')
        def curl(*args):
            return subprocess.check_output(['curl.exe', '--silent', '--show-error', '--fail',
                                            '--max-time', '30', *args], text=True)
        page = curl(base + '/')
        nonce = re.search(r'window\.__hqBootstrap="([0-9a-f]{32})"', page).group(1)
        auth = curl('-c', cookie, '-H', 'Origin: ' + base, '-H', 'Content-Type: application/json',
                    '--data', json.dumps({'nonce': nonce}), base + '/api/bootstrap')
        assert json.loads(auth)['ok']
        results = {}
        for route in ('portfolio', 'attribution'):
            raw = curl('-b', cookie, base + '/api/' + route)
            results[route] = json.loads(raw)
            print('GET /api/' + route + '\n' + raw)
        report = Path(__file__).parent / 'agent-reports' / 'portfolio-live-responses.json'
        report.parent.mkdir(exist_ok=True)
        report.write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

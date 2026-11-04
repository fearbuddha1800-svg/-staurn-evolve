"""Bounded, opt-in public page metadata collection; no content persistence."""

import argparse
import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

HOSTS = frozenset({'www.mql5.com', 'mql5.com', 'www.tradingview.com',
                   'docs.freqtrade.io', 'nautilustrader.io', 'www.quantconnect.com'})
MAX_BYTES = 1024 * 1024
USER_AGENT = 'PublicMetadataCollector/1.0'


def validate_url(url: str) -> str:
    """Accept only explicit HTTPS URLs on the fixed public host allowlist."""
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError('URL contains whitespace or control characters')
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname not in HOSTS
            or parts.netloc.lower() != parts.hostname or '#' in url or '\\' in url):
        raise ValueError('URL must use HTTPS and an allowed host, without credentials, port or fragment')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, timeout: float):
    """No proxy environment or redirects; each request has a socket timeout."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity',
    })
    try:
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        return error


class Title(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'title':
            self.active = True

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def read_response(response):
    try:
        status = response.status
        if status != 200:
            return status, None
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Response exceeds 1 MiB')
        if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('Encoded response rejected')
        return status, body
    finally:
        response.close()


def collect(urls, *, transport=fetch, timeout=10.0, interval=1.0,
            clock=time.monotonic, sleep=time.sleep):
    """Return metadata rows; cache robots successes and failures per host."""
    urls = list(urls)
    if not 1 <= len(urls) <= 20:
        raise ValueError('Supply between 1 and 20 approved URLs')
    if not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise ValueError('Timeout must be greater than 0 and at most 30 seconds')
    if not math.isfinite(interval) or interval < 1:
        raise ValueError('Per-host interval must be at least one second')
    for url in urls:
        validate_url(url)
    robots, last, delays, rows = {}, {}, {}, []

    def request(url, host):
        if host in last:
            sleep(max(0, delays.get(host, interval) - (clock() - last[host])))
        last[host] = clock()
        return read_response(transport(url, timeout))

    for url in urls:
        host = urlsplit(url).hostname
        row = {'title': None, 'url': url,
               'fetched_at': datetime.now(timezone.utc).isoformat(),
               'status': None, 'sha256': None,
               'public_page': 'Not fetched: robots unavailable or denied'}
        if host not in robots:
            robots[host] = None
            try:
                status, body = request(f'https://{host}/robots.txt', host)
                if status == 200 and body is not None:
                    parser = RobotFileParser()
                    parser.parse(body.decode('utf-8', errors='strict').splitlines())
                    robots[host] = parser
                    rate = parser.request_rate(USER_AGENT)
                    delays[host] = max(interval, parser.crawl_delay(USER_AGENT) or 0,
                                       rate.seconds / rate.requests if rate else 0)
            except (OSError, ValueError, urllib.error.URLError):
                pass
        parser = robots[host]
        if parser is not None and parser.can_fetch(USER_AGENT, url):
            try:
                row['status'], body = request(url, host)
                if body is not None:
                    title = Title()
                    title.feed(body.decode('utf-8', errors='replace'))
                    row.update(title=' '.join(''.join(title.parts).split())[:500] or None,
                               sha256=hashlib.sha256(body).hexdigest(),
                               public_page='Public page metadata only; no training-data claim')
                else:
                    row['public_page'] = 'Not collected: HTTP failure or redirect'
            except (OSError, ValueError, urllib.error.URLError):
                row['public_page'] = 'Not collected: transport, encoding or size failure'
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-url', action='append', required=True,
                        help='Explicitly approved HTTPS URL; repeat up to 20 times')
    parser.add_argument('--timeout', type=float, default=10, help='Socket timeout, 0 < seconds <= 30')
    parser.add_argument('--interval', type=float, default=1, help='Minimum per-host seconds (>= 1)')
    args = parser.parse_args()
    try:
        rows = collect(args.approved_url, timeout=args.timeout, interval=args.interval)
    except ValueError as error:
        parser.error(str(error))
    for row in rows:
        print(json.dumps(row, ensure_ascii=True))


if __name__ == '__main__':
    main()

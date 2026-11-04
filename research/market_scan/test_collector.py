import hashlib
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collector.py'))
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)
URL = 'https://www.mql5.com/en/market'


class Response:
    def __init__(self, body=b'', status=200, headers=None):
        self.body, self.status, self.headers = body, status, headers or {}

    def read(self, size):
        return self.body[:size]

    def close(self):
        pass


class Transport:
    def __init__(self, robots=b'User-agent: *\nAllow: /', page=None):
        self.robots, self.page, self.calls = robots, page or Response(b'<title>A &amp; B</title>'), []

    def __call__(self, url, timeout):
        self.calls.append((url, timeout))
        if url.endswith('/robots.txt'):
            if isinstance(self.robots, Exception):
                raise self.robots
            return self.robots if isinstance(self.robots, Response) else Response(self.robots)
        if isinstance(self.page, Exception):
            raise self.page
        return self.page


def run(transport, urls=None, **kwargs):
    return collector.collect(urls or [URL], transport=transport, sleep=lambda _: None, **kwargs)


@pytest.mark.parametrize('url', [
    'http://www.mql5.com/', 'https://user@www.mql5.com/',
    'https://www.mql5.com:443/', 'https://www.mql5.com/#x',
    'https://127.0.0.1/', 'https://localhost/', 'https://evil.com/',
    'https://www.mql5.com.evil.com/', 'https://www.mql5.com/\\evil',
    'https://www.mql5.com/#', 'https://www.mql5.com:/',
])
def test_invalid_url(url):
    with pytest.raises(ValueError):
        collector.validate_url(url)


def test_metadata_and_cached_robots():
    transport = Transport()
    rows = run(transport, [URL, URL + '/2'])
    assert len(transport.calls) == 3
    assert rows[0]['title'] == 'A & B'
    assert rows[0]['sha256'] == hashlib.sha256(transport.page.body).hexdigest()
    assert rows[0]['status'] == 200
    assert rows[0]['public_page']
    assert set(rows[0]) == {'title', 'url', 'fetched_at', 'status', 'sha256', 'public_page'}


@pytest.mark.parametrize('robots', [OSError('offline'), b'User-agent: *\nDisallow: /',
                                     Response(status=404), Response(status=302)])
def test_robots_fail_closed(robots):
    transport = Transport(robots=robots)
    rows = run(transport, [URL, URL + '/2'])
    assert all(row['sha256'] is None for row in rows)
    assert len(transport.calls) == 1


@pytest.mark.parametrize('location', ['https://evil.com/', '/safe', 'http://www.mql5.com/'])
def test_redirects_never_followed(location):
    transport = Transport(page=Response(status=302, headers={'Location': location}))
    assert run(transport)[0]['sha256'] is None
    assert len(transport.calls) == 2
    request = collector.urllib.request.Request(URL)
    assert collector.NoRedirect().redirect_request(request, None, 302, '', {}, location) is None


def test_size_limit():
    assert run(Transport(page=Response(b'x' * (collector.MAX_BYTES + 1))))[0]['sha256'] is None
    assert run(Transport(robots=b'x' * (collector.MAX_BYTES + 1)))[0]['sha256'] is None


@pytest.mark.parametrize('page', [OSError('failed'), Response(status=403), Response(status=500)])
def test_failed_pages(page):
    row = run(Transport(page=page))[0]
    assert row['sha256'] is None
    assert row['title'] is None


def test_limits_and_prevalidation():
    transport = Transport()
    for urls in [[URL] * 21, [URL, 'http://evil.com/']]:
        with pytest.raises(ValueError):
            run(transport, urls)
    assert not transport.calls
    for timeout in [0, 31, float('nan')]:
        with pytest.raises(ValueError):
            run(transport, timeout=timeout)


def test_polite_rate_limit():
    pauses = []
    collector.collect([URL, URL + '/2'], transport=Transport(),
                      clock=lambda: 0, sleep=pauses.append)
    assert pauses == [1.0, 1.0]


def test_robot_delay():
    pauses = []
    collector.collect([URL], transport=Transport(robots=b'User-agent: *\nCrawl-delay: 3'),
                      clock=lambda: 0, sleep=pauses.append)
    assert pauses == [3.0]

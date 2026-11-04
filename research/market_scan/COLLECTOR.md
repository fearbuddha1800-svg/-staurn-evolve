# Public metadata collector

Uses Python's standard library. Supply each explicitly approved page URL:

```sh
python research/market_scan/collector.py \
  --approved-url https://docs.freqtrade.io/en/stable/ \
  --timeout 10 --interval 2 > metadata.jsonl
```

This example makes network requests only when you run it. There is no discovery,
link following, scheduler, login, challenge bypass, or training-data export.
Approve the specific URLs yourself before running. Do not use it to bypass site
restrictions; public access does not grant reuse rights.

Only HTTPS URLs on these exact hosts are accepted: `www.mql5.com`, `mql5.com`,
`www.tradingview.com`, `docs.freqtrade.io`, `nautilustrader.io`, and
`www.quantconnect.com`. Credentials, explicit ports (including 443), fragments,
backslashes, whitespace, IP literals, and other hosts are rejected before any
request. All redirects, including robots redirects, are disabled. Environment
HTTP proxies are disabled. Normal system DNS and TLS verification apply.

Each invocation accepts 1–20 pages. Each response, including robots.txt, is read
with a 1 MiB limit plus one detection byte. Encoded responses are rejected.
The socket timeout defaults to 10 seconds and cannot exceed 30 seconds; this is
a socket-operation timeout, not a total invocation deadline. Requests to each
host start at least one second apart, with longer robots crawl-delay or
request-rate spacing respected. Robots is fetched once per host per invocation;
unavailable, oversized, undecodable, non-200, redirected, or denying robots
fails closed. No retry is attempted. At most 20 robots requests plus 20 page
requests can occur. Robots matching uses `PublicMetadataCollector/1.0`.

Output is one JSON object per input URL, in input order, containing only:

- `title`: normalized HTML title, truncated to 500 characters, or null.
- `url`: approved input URL.
- `fetched_at`: UTC attempt timestamp, including skipped pages.
- `status`: page HTTP status when available, otherwise null.
- `sha256`: SHA-256 of the fetched response bytes, or null on failure.
- `public_page`: collection outcome note; it does not certify licensing,
  rights, or suitability for training.

HTML is held transiently in memory and never stored. Failure rows have null
title/hash; redirects retain their HTTP status. A size/transport failure may
have null status. Failures do not prevent later approved pages being attempted.
CLI validation errors exit nonzero; individual page failures appear in JSONL
and do not change the exit status. Inspect each row's outcome.

Offline verification (no network):

```sh
rtk proxy python -m pytest research/market_scan/test_collector.py -q
rtk proxy ruff check research/market_scan/collector.py research/market_scan/test_collector.py
```

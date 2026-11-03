---
slug: live_server_check
type: note
graph: gitnexus
---

"""Exercise every API endpoint on the live server using the auto-login cookie path."""
import urllib.request
import urllib.parse
import http.cookiejar
import json
import re
import sys
import socket

# Set a global timeout to avoid hanging on slow endpoints
socket.setdefaulttimeout(10)

BASE = "http://localhost:8490"

# Create a cookie jar and opener
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Step 1: GET / to extract the nonce
resp = opener.open(BASE + "/")
html = resp.read().decode("utf-8")
match = re.search(r'window\.__hqBootstrap="([0-9a-f]{32})"', html)
if not match:
    print("FAIL: Could not extract nonce from page")
    sys.exit(1)
nonce = match.group(1)
print(f"Extracted nonce: {nonce}")

# Step 2: POST /api/bootstrap with the nonce
req = urllib.request.Request(
    BASE + "/api/bootstrap",
    data=json.dumps({"nonce": nonce}).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Origin": BASE,
    },
    method="POST"
)
resp = opener.open(req)
print(f"Bootstrap status: {resp.status}")

# Check we got a session cookie
cookies = [c for c in cj if c.name == "cockpit_session"]
if not cookies:
    print("FAIL: No session cookie received")
    sys.exit(1)
print(f"Session cookie obtained: {cookies[0].value[:30]}...")

# Step 3: Exercise every API endpoint
endpoints = [
    ("GET", "/api/state"),
    ("GET", "/api/inbox"),
    ("GET", "/api/journal"),
    ("GET", "/api/mobile"),
    ("GET", "/api/neural"),
    ("GET", "/api/latency"),
    ("GET", "/api/lineage"),
    ("GET", "/api/pine"),
    ("GET", "/api/strategies"),
    ("GET", "/api/health"),
    ("GET", "/api/channels"),
    ("GET", "/api/news"),
    ("GET", "/api/luxalgo"),
    ("GET", "/api/edge"),
    ("GET", "/api/quant"),
    ("GET", "/api/token"),
    ("GET", "/api/candles"),
    ("GET", "/api/pine_series"),
    ("GET", "/api/prop_sim"),
    ("GET", "/api/market_intel"),
    ("GET", "/api/events"),
    ("GET", "/api/events?limit=500"),
    ("GET", "/api/events?limit=501"),
    ("GET", "/api/events?stream=1"),
    ("GET", "/api/trace/123"),
    ("GET", "/assets/quant.css"),
    ("GET", "/assets/quant.js"),
    ("GET", "/vela/vela.global.js"),
    ("GET", "/"),
]

results = []
for method, path in endpoints:
    try:
        req = urllib.request.Request(BASE + path, method=method)
        resp = opener.open(req)
        status = resp.status
        body_preview = resp.read(200).decode("utf-8", errors="replace")[:100]
    except urllib.error.HTTPError as e:
        status = e.code
        body_preview = e.read(200).decode("utf-8", errors="replace")[:100]
    except Exception as e:
        status = f"ERR: {e}"
        body_preview = ""
    results.append((method, path, status, body_preview))
    print(f"{method:6s} {path:40s} -> {status}")

# Also test unauthenticated access to /api/token
print("\n--- Unauthenticated tests ---")
try:
    req = urllib.request.Request(BASE + "/api/token", method="GET")
    resp = urllib.request.urlopen(req)
    print(f"GET /api/token (no auth) -> {resp.status}")
except urllib.error.HTTPError as e:
    print(f"GET /api/token (no auth) -> {e.code}")

# Test bootstrap with GET method
try:
    req = urllib.request.Request(BASE + "/api/bootstrap", method="GET")
    resp = opener.open(req)
    print(f"GET /api/bootstrap -> {resp.status}")
except urllib.error.HTTPError as e:
    print(f"GET /api/bootstrap -> {e.code}")

# Test bootstrap with unknown nonce
unknown_nonce = "b" * 32
try:
    req = urllib.request.Request(
        BASE + "/api/bootstrap",
        data=json.dumps({"nonce": unknown_nonce}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": BASE},
        method="POST"
    )
    resp = opener.open(req)
    print(f"POST /api/bootstrap (unknown nonce) -> {resp.status}")
except urllib.error.HTTPError as e:
    print(f"POST /api/bootstrap (unknown nonce) -> {e.code}")

print("\n--- Summary ---")
print(f"Total endpoints tested: {len(results)}")
passed = sum(1 for _, _, s, _ in results if isinstance(s, int) and 200 <= s < 300)
print(f"2xx responses: {passed}")
non_2xx = [(m, p, s) for m, p, s, _ in results if not (isinstance(s, int) and 200 <= s < 300)]
if non_2xx:
    print("Non-2xx responses:")
    for m, p, s in non_2xx:
        print(f"  {m} {p} -> {s}")


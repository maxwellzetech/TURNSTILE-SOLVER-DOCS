# Cloudflare Turnstile solver

**Hosted endpoint:** `https://solver.maxwell.deals`


| Capability                                                                 | Endpoint              |
| -------------------------------------------------------------------------- | --------------------- |
| Earn a Cloudflare `cf_clearance` cookie you can replay from your own stack | `POST /v1/solver`     |
| IP intelligence: ASN, ISP, hostname, geo for any address                   | `POST`/`GET` `/v1/ip` |
| Turnstile widget token (legacy)                                            | `POST /v1/turnstile`  |

All request and response bodies are JSON.

---

## Authentication (Optional)

(Keep your key secret — requests made with it draw from **your** quota. If a
key leaks, ask [support](https://t.me/cloutmaxwell) to rotate it.)(it's optional but unathenticated requests may subject to rate limits)
Send your key as a bearer token on every request:

```
Authorization: Bearer <YOUR_API_KEY>
```

Missing or wrong key → `401`. Disabled or expired key → `403`.

---

## 1. POST /v1/solver — earn a cf_clearance

Loads the real target URL in a real (cleared) browser, passes the Cloudflare
challenge, and returns a ready-to-replay session.

Request:

```json
{"url": "https://your-target-site.com/login", "proxy": "http://user:pass@host:port"}
```

| Field   | Required        | Description                                                                                                                          |
| ------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `url`   | yes             | Target URL (http/https). The clearance is for this site.                                                                             |
| `proxy` | **recommended** | Your **residential** proxy: `http://user:pass@host:port`, `socks5://…`, `socks4://…`. The clearance is earned *through this egress*. |

Response `200`:

```json
{
  "headers": {
    "Cookie": "cf_clearance=155jEz2BCC8oFRCOu0x8...",
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 ..."
  },
  "ip": "203.0.113.7",
  "elapsed": "2.87s",
  "status": "completed"
}
```

> ⏱ Solves are real-browser solves — allow **up to 60 s** client timeout.

---

## Replaying the session — read this or you'll get 403s

`cf_clearance` is **bound to the exact User-Agent and egress IP that earned
it**. Cloudflare checks all of it on every replay:

1. **Same User-Agent** — send the exact `headers.User-Agent` string from the
   response. Any other UA invalidates the cookie.
2. **Same IP** — send your requests through the **same proxy you passed in the
   solve request** (your residential proxy). The `ip` field echoes the egress
   that earned it.

   * Solving without a proxy means the clearance was earned on **our server's
     IP** — replaying from your own IP will not match and Cloudflare will
     re-challenge you. **Always pass your own proxy for hosted use.**
3. **Browser-like TLS fingerprint** — replay with a client that impersonates a
   real browser (`curl_cffi`, `tls-client`, or a real browser automation).
   Plain `requests`/`curl` can re-trigger the challenge even with the right
   cookie.

If you follow all three, you're making requests that look exactly like the
session that earned the clearance — no re-challenges, no `403`s.

When you *do* get re-challenged later (cookies expire, sites tighten rules),
just solve again.

### Python example (curl_cffi)

```python
from curl_cffi import requests as cffi

API   = "https://solver.maxwell.deals"
KEY   = "<YOUR_API_KEY>"
PROXY = "http://user:pass@residential-proxy:port"
TARGET = "https://your-target-site.com/"


r = cffi.post(f"{API}/v1/solver",
              headers={"Authorization": f"Bearer {KEY}",
                       "content-type": "application/json"},
              json={"url": TARGET, "proxy": PROXY}, timeout=60)
s = r.json()


page = cffi.get(TARGET,
                headers={"User-Agent": s["headers"]["User-Agent"],
                         "Cookie": s["headers"]["Cookie"]},
                proxy=PROXY, impersonate="chrome", timeout=30)
print(page.status_code)  # 200 — no challenge
```

### curl example

```bash
curl -X POST https://solver.maxwell.deals/v1/solver \
  -H "Authorization: Bearer $KEY" \
  -H "content-type: application/json" \
  -d '{"url":"https://your-target-site.com/login","proxy":"http://user:pass@host:port"}'
```

---

## 2. POST /turnstile — Turnstile token (legacy)

Solves a Cloudflare Turnstile widget and returns the Turnstile token.

**Endpoint:**

```text
POST https://solver.maxwell.deals/turnstile
```

### Request

Send a JSON body with the Turnstile widget details:

```json
{
  "url": "https://nowsecure.nl",
  "sitekey": "0x4AAAAAAA...",
  "cdata": "optional",
  "action": "optional",
  "proxy": "http://user:pass@host:port"
}
```

### Parameters

| Field     | Required | Description                                                                                                                                                                             |
| --------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`     | yes      | Target URL you want to solve (e.g: https://example.com/login).                                                                                                                                        |
| `sitekey` | yes      | Turnstile sitekey (`0x...`).                                                                                                                                                            |
| `cdata`   | optional | Custom Turnstile data.                                                                                                                                                                  |
| `action`  | optional | Turnstile action associated with the widget.                                                                                                                                            |
| `proxy`   | optional | Proxy used to earn the clearance/token. Supported formats: `http://user:pass@host:port`, `socks5://user:pass@host:port`, `socks4://host:port` — earn the clearance through this egress. |

### Response

The endpoint returns the Turnstile token only.

```text
<TURNSTILE_TOKEN>
```

Use the returned value as the Turnstile response token in the target
application's Turnstile verification flow.

## 3. POST / GET /v1/ip — IP intelligence

I took a test on [whatismyipaddress.com](https://whatismyipaddress.com/) where they use turnstile for ip lookup. I was able to use extract data like: ASN, ISP, hostname, country,
region, city, coordinates with a few lines of code. Results are cached, so repeat lookups are fast.

### scrape whatismyipaddress.com yourself, using the solver (example)

Create your own self-hosted ip lookup from [whatismyipaddress.com](https://whatismyipaddress.com/) data. This illustrate how you can solve turnstile easily with a few lines of code. Earn a `cf_clearance` for
whatismyipaddress.com through your proxy, replay it with a browser-impersonated
client, and parse the page. The clearance is reusable for ~25 min — cache it
and re-solve only when Cloudflare challenges you again, so you spend little
quota.

```python
import time
import requests
from curl_cffi import requests as cffi
from bs4 import BeautifulSoup

API   = "https://solver.maxwell.deals"
KEY   = "<YOUR_API_KEY>"
PROXY = "http://user:pass@residential-proxy:port"   # same proxy for solve + scrape


def earn_clearance(url: str) -> dict:
    r = requests.post(
        f"{API}/v1/solver",
        headers={"Authorization": f"Bearer {KEY}"},
        json={"url": url, "proxy": PROXY},
        timeout=90,
    )
    r.raise_for_status()
    hdrs = r.json()["headers"]          # {"Cookie": "cf_clearance=…", "User-Agent": "…"}
    if not hdrs.get("Cookie"):
        raise RuntimeError(f"no cookie in solve response: {r.json()}")
    return hdrs


def page_get(url: str, hdrs: dict):
    ua = hdrs["User-Agent"]
    imp = "chrome_android" if ("Mobile" in ua or "Android" in ua) else "chrome"
    return cffi.get(
        url,
        headers={"Cookie": hdrs["Cookie"]},   
        impersonate=imp,
        proxy=PROXY,                          
        timeout=30,
    )

# 3) fetch with retry: re-solve once if Cloudflare re-challenges
_cache = {"hdrs": None, "at": 0.0}
def fetch_page(url: str) -> str:
    for attempt in range(2):
        if _cache["hdrs"] and time.time() - _cache["at"] < 1500:   # ~25 min
            hdrs = _cache["hdrs"]
        else:
            hdrs = earn_clearance(url)
            _cache.update(hdrs=hdrs, at=time.time())
        resp = page_get(url, hdrs)
        if resp.status_code == 200:
            return resp.text
        _cache["hdrs"] = None                 
    raise RuntimeError(f"whatismyipaddress kept challenging: HTTP {resp.status_code}")


def parse_ip_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    vals = {}
    for row in soup.select(".ip-information .information"):
        spans = row.find_all("span")
        if len(spans) >= 2:
            vals[spans[0].get_text(" ", strip=True).rstrip(":")] = spans[1].get_text(" ", strip=True)
    label = soup.select_one(".ip-information .label")
    ip = label.get_text(" ", strip=True).split(":", 1)[1].strip() if label and ":" in label.get_text() else None
    def num(name, cast):
        try:
            return cast(vals[name].split()[0])       
        except (KeyError, ValueError, IndexError):
            return None
    services = vals.get("Services", "")
    return {
        "ip": ip,
        "decimal": num("Decimal", int),
        "hostname": vals.get("Hostname"),
        "asn": num("ASN", int),
        "isp": vals.get("ISP"),
        "services": [] if services.lower() in ("", "none detected") else [s.strip() for s in services.split(",")],
        "country": vals.get("Country"),
        "region": vals.get("State/Region"),
        "city": vals.get("City"),
        "latitude": num("Latitude", float),
        "longitude": num("Longitude", float),
    }

def self_hosted_lookup(ip: str) -> dict:
    return parse_ip_details(fetch_page(f"https://whatismyipaddress.com/ip/{ip}"))

print(self_hosted_lookup("197.157.xx.xx"))
```

This returns the same fields as `/v1/ip` — pick it only if you need the
raw HTML or want the lookup running on your own infrastructure;
Request — JSON body or query string, both work:

```json
{"ip": "197.157.165.49"}
```

```
GET /v1/ip?ip=197.157.165.49
```

Response `200`:

```json
{
  "ip": "197.157.165.49",
  "decimal": 3315442993,
  "hostname": "49-165-157-197.r.airtel.co.rw",
  "asn": 327707,
  "isp": "Airtel Rwanda Ltd",
  "services": [],
  "country": "Rwanda",
  "region": "Ville de Kigali",
  "city": "Kigali",
  "latitude": -1.9501,
  "longitude": 30.0588,
  "cached": false,
  "source": "miss"
}
```

# Or use or hosted endpoint

```python
import requests

API = "https://solver.maxwell.deals"
KEY = "<YOUR_API_KEY>"

def ip_lookup(ip: str) -> dict:
    r = requests.post(
        f"{API}/v1/ip",
        headers={"Authorization": f"Bearer {KEY}"},
        json={"ip": ip},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()   # ip, hostname, asn, isp, country, region, city, lat/lon …

print(ip_lookup("197.157.165.49"))
```

---

## Quotas & rate limits

* Your key has a **daily quota: requests per rolling 24 h** (your plan; some
  keys are unlimited).
* Unauthenticated requests subject to rate limits back off when you get `429`.
* Need more capacity? Contact [support](https://t.me/cloutmaxwell)

---

## Errors

All errors share one shape:

```json
{"success": false, "message": "why it failed", "upgrade": "@support-handle"}
```

| Status | Meaning                                                          |
| ------ | ---------------------------------------------------------------- |
| `400`  | Malformed body / missing or invalid field                        |
| `401`  | Missing or wrong API key                                         |
| `403`  | Key disabled or expired — contact support                        |
| `404`  | Unknown path                                                     |
| `429`  | Quota exhausted or rate limit hit — slow down or upgrade         |
| `500`  | Solve failed / internal error — retry once, then contact support |
| `502`  | Upstream fetch failed after retries — retry shortly              |

---

That's All I can Explain!


## Best practices & FAQ

* **Always pass a residential proxy(Datacenter ip also works but not recommended) on `/v1/solver`** — hosted solves without
  one are earned on our IP and won't replay from yours.
* **One solve per browsing session.** Reuse the cookie for many requests, but
  re-solve when Cloudflare starts challenging again.
* **Don't hammer on `429`.** Back off; quota resets on a rolling 24 h window.
* **Keep the UA + cookie pair together.** Don't mix a cookie from one solve
  with a UA from another.
* **Datacenter proxies often fail** — Cloudflare pre-flags many of them.
  Residential/mobile works best.

---

## Support

Questions, quota upgrades, key rotation: reach out via [@cloutmaxwell](https://t.me/cloutmaxwell) on [Telegram](https://web.telegram.org/k/#@cloutmaxwell)

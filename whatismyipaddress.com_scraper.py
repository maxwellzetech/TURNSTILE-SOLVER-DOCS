"""
Scrape whatismyipaddress.com with just a few lines of code. pure requests, no browsers, no plawright. MIT licence.
This is an example illustration on how you can use Turnstile solver bypass antibot and automate requests.
Response Takes 3-15 seconds, with 5 seconds the peak response time.
Telegram @cloutmaxwell
"""




import time
import requests
from curl_cffi import requests as cffi
from bs4 import BeautifulSoup





API   = "https://solver.maxwell.deals"
KEY   = "<YOUR_API_KEY>" # (OPTIONAL) Leave empty if you don't have one but requests get a cooldown
PROXY = "http://user:pass@residential-proxy:port"   


def earn_clearance(url: str) -> dict:
    r = requests.post(
        f{API}/v1/solver",
        headers={"Authorization": f"Bearer {KEY}"},
        json={"url": url, "proxy": PROXY},
        timeout=90,
    )
    r.raise_for_status()
    hdrs = r.json()["headers"]          
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
        if _cache["hdrs"] and time.time() - _cache["at"] < 1500:   
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




"""
Example response:


{
  "ip": "197.157.xx.xx",
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
}
"""


"""



feel free to star 

Happy Coding!

"""

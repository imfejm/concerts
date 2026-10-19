"""Vytvoří na Spotify jeden playlist na každý den z interpretů v concerts.json.

Použití:
    set SPOTIFY_CLIENT_ID=...
    set SPOTIFY_CLIENT_SECRET=...
    python spotify_playlists.py              # nejbližších 14 dnů s koncerty
    python spotify_playlists.py --days 0     # všechny budoucí dny
    python spotify_playlists.py --dry-run    # jen vypíše interprety po dnech, bez Spotify

V nastavení Spotify aplikace musí být Redirect URI přesně: http://127.0.0.1:8888/callback

Výsledek: playlists.json  {"2026-10-05": {"name", "id", "url", "artists", "missing"}}
Soubor pak čte web (embed playlistu u daného dne).
"""
import argparse
import base64
import json
import os
import re
import sys
import threading
import time
import unicodedata
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

sys.stdout.reconfigure(encoding="utf-8")

CONCERTS = "concerts.json"
OUT = "playlists.json"
CACHE = "spotify_cache.json"  # interpret -> URI skladby (nebo null), šetří požadavky
REDIRECT = "http://127.0.0.1:8888/callback"
SCOPE = "playlist-modify-public playlist-read-private"
API = "https://api.spotify.com/v1"

# Události, které nejsou koncert konkrétního interpreta
SKIP_RE = re.compile(
    r"\b(dj|party|video party|jam session|jam|open mic|quiz|kvíz|karaoke|festival|fest|"
    r"vstupenk|ticket|dárkov|voucher|koncert|special new year|silvestr)\b",
    re.I,
)


COUNTRY_RE = re.compile(
    r"\s*/\s*(?:DE|US|BG|RU|CA|JP|UK|GB|FR|IT|ES|PL|SK|AT|AU|SE|NO|FI|NL|HU|CH|BE|IE|IS|DK|CZ|HR|RS|UA|"
    r"CN|KR|BR|MX|AR|SI|RO|LT|LV|EE|PT|GR|TR|IL|NZ|ZA|IN)\s*$")
# koncovky, které na Spotify obvykle nejsou součástí jména interpreta
SUFFIX_RE = re.compile(r"\s+(?:trio|quartet|quintet|band|big band|orchestra|group|duo|live|tribute|revival)$", re.I)

STOP = {"band", "kapela", "support", "cabaret", "natural", "after", "early show", "live nation",
        "klub zadan", "hallelujah", "melodic journey", "ambient session", "trubku", "no", "es", "au",
        "gr", "swe", "rattle", "skyline", "orion", "stress", "revo", "sloth", "protimluv",
        "rfp concerts", "rock for people", "selection", "fource", "soul", "pop 80s", "gershwin", "adventures",
        "dalsi", "zruseno", "filharmoniste", "romanticke melodie", "swinging melodies"}


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def extract_artists(title):
    """Z názvu akce vytáhne pravděpodobné jména interpretů (heuristika)."""
    if SKIP_RE.search(title) and len(title.split()) < 3:
        return []
    t = re.sub(r"https?://\S+", " ", title)
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", t)                # (CZ), (AUS) ...
    t = re.sub(r"^keltsk[ée] [úu]ter[ýy]\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"(?<=[a-zá-ž])(?=(?:Ned[ěe]ln[íi]|K[řr]est))", " ", t)  # slepené "...MalinováNedělní Dixie"
    t = re.split(r"\s[-–—:]\s|:\s| – | — |(?<=\S)[-–—]\s+", t)[0]   # podtitul za pomlčkou/dvojtečkou
    t = re.split(r"\s(?:k[řr]est|narozeninov|pro[šs]li|celebrating|live at|ned[ěe]ln[íi])\b", t, flags=re.I)[0]
    t = re.sub(r"^.*?\bpresents?\s+", "", t, flags=re.I)          # "RFP CONCERTS present X" -> X
    parts = re.split(r"\s*(?:\+|,|\s/\s|//|☆|★|\sa\s|\sand\s|\swith\s|\sw/\s|\s&\s|\sx\s|\smeets\s|"
                     r"\sinvites\s|\sfeat\.?\s|\sfeaturing\s)\s*", t, flags=re.I)
    out = []
    for p in parts:
        p = COUNTRY_RE.sub("", p).strip(" .-–—#")
        if len(p) < 3 or len(p) > 50 or SKIP_RE.fullmatch(p.lower()) or norm(p) in STOP:
            continue
        if re.search(r"special guests?|hosté|host", p, re.I):
            continue
        out.append(p)
    return out


def is_special_venue(v):
    """Stejné pravidlo jako isSpecialVenue v index.js: kostely apod. jdou na web (a do playlistu) na konec."""
    return bool(v) and v != "Palác Akropolis" and bool(
        re.search(r"kostel|palác|purkrabství|synagog|kapl[ei]|humanitních studií", v, re.I))


def load_days(today):
    events = json.load(open(CONCERTS, encoding="utf-8"))["events"]
    days = {}
    for e in events:
        if e.get("category") != "hudba":
            continue
        try:
            d = datetime.strptime(e["date"], "%d.%m.%Y").date()
        except (KeyError, ValueError):
            continue
        if d < today:
            continue
        days.setdefault(d.isoformat(), []).append(e)
    # pořadí jako na webu: pořadí akcí v concerts.json, kostely apod. (stabilně) na konec dne
    out = {}
    for key, evs in sorted(days.items()):
        evs = [e for e in evs if not is_special_venue(e.get("venue"))] + \
              [e for e in evs if is_special_venue(e.get("venue"))]
        artists = {}
        for e in evs:
            for a in extract_artists(e["title"]):
                artists.setdefault(norm(a), a)  # první výskyt určuje pořadí
        out[key] = list(artists.values())
    return out


# ---------- Spotify ----------

def get_token(cid, secret):
    code_box = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            code_box["code"] = q.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Hotovo, můžeš zavřít toto okno.".encode("utf-8"))

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 8888), H)
    t = threading.Thread(target=srv.handle_request)
    t.start()
    webbrowser.open("https://accounts.spotify.com/authorize?" + urlencode(
        {"client_id": cid, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPE}))
    t.join()
    srv.server_close()
    if not code_box.get("code"):
        sys.exit("Autorizace se nezdařila.")
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post("https://accounts.spotify.com/api/token",
                      headers={"Authorization": f"Basic {basic}"},
                      data={"grant_type": "authorization_code", "code": code_box["code"],
                            "redirect_uri": REDIRECT})
    if not r.ok:
        sys.exit(f"Spotify odmítl token ({r.status_code}): {r.text}")
    return r.json()["access_token"]


def call(method, path, token, **kw):
    for _ in range(5):
        r = requests.request(method, API + path, headers={"Authorization": f"Bearer {token}"}, **kw)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "2")) + 1
            if wait > 120:
                sys.exit(f"Spotify omezil počet požadavků, chce čekat {wait} s (~{wait // 60} min). "
                         "Zkus to později, průběh je uložený v playlists.json.")
            print(f"  limit Spotify, čekám {wait} s ...")
            time.sleep(wait)
            continue
        if r.status_code in (502, 503, 504):
            print(f"  Spotify {r.status_code}, zkouším znovu ...")
            time.sleep(3)
            continue
        return r
    return r


def find_cached(name, token, cache):
    key = norm(name)
    if not cache.get(key):  # chybějící i dřívější nenalezené (prázdný seznam) zkusit znovu
        cache[key] = find_tracks(name, token)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return cache[key]


def same_artist(spotify_name, want):
    a, b = norm(spotify_name), want
    return a == b or re.sub(r"^the ", "", a) == re.sub(r"^the ", "", b)


def find_tracks(name, token):
    """Vrátí URI nejpopulárnější skladby interpreta, jehož jméno přesně odpovídá (jinak nic).

    Zkouší postupně: hledání skladeb podle interpreta, hledání interpreta + jeho top skladby,
    a totéž bez koncovky typu Trio/Band/Quartet.
    """
    variants = [name]
    short = SUFFIX_RE.sub("", name).strip()
    if short and short != name:
        variants.append(short)
    for v in variants:
        want = norm(v)
        time.sleep(1)  # šetrně k limitu Spotify
        r = call("GET", "/search", token, params={"q": f'artist:"{v}"', "type": "track", "limit": 10})
        if r.status_code == 200:
            hits = [t for t in r.json().get("tracks", {}).get("items", [])
                    if any(same_artist(a["name"], want) for a in t["artists"])]
            if hits:
                return [max(hits, key=lambda t: t.get("popularity", 0))["uri"]]
        time.sleep(1)
        r = call("GET", "/search", token, params={"q": v, "type": "artist", "limit": 10})
        if r.status_code != 200:
            continue
        arts = [a for a in r.json().get("artists", {}).get("items", []) if same_artist(a["name"], want)]
        if not arts:
            continue
        best = max(arts, key=lambda a: a.get("popularity", 0))
        time.sleep(1)
        r = call("GET", f"/artists/{best['id']}/top-tracks", token, params={"market": "CZ"})
        tracks = r.json().get("tracks", []) if r.status_code == 200 else []
        if tracks:
            return [tracks[0]["uri"]]
        r = call("GET", "/search", token, params={"q": f"artist:{best['name']}", "type": "track", "limit": 10})
        items = r.json().get("tracks", {}).get("items", []) if r.status_code == 200 else []
        items = [t for t in items if any(a["id"] == best["id"] for a in t["artists"])]
        if items:
            return [items[0]["uri"]]
    return []


def add_items(pid, uris, token):
    for i in range(0, len(uris), 100):
        chunk = uris[i:i + 100]
        r = call("POST", f"/playlists/{pid}/items", token, json={"uris": chunk})
        if r.status_code == 404:  # starší verze API
            r = call("POST", f"/playlists/{pid}/tracks", token, json={"uris": chunk})
        r.raise_for_status()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--days", type=int, default=14, help="kolik nejbližších dnů s koncerty (0 = všechny)")
    ap.add_argument("--skip-existing", action="store_true",
                    help="dny, které už mají playlist v playlists.json, nechat beze změny (zachová ruční úpravy)")
    ap.add_argument("--recover", action="store_true",
                    help="najít na Spotify už vytvořené playlisty (podle názvu 'D. M. RRRR') a doplnit je do playlists.json")
    args = ap.parse_args()

    days = load_days(date.today())
    if args.days:
        days = dict(list(days.items())[:args.days])

    if args.dry_run:
        for k, v in days.items():
            print(f"{k} ({len(v)}): {', '.join(v)}")
        return

    cid, secret = os.environ.get("SPOTIFY_CLIENT_ID"), os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("Nastav SPOTIFY_CLIENT_ID a SPOTIFY_CLIENT_SECRET.")
    token = get_token(cid, secret)

    result = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if args.recover:
        by_name, url = {}, "/me/playlists?limit=50"
        while url:
            r = call("GET", url, token)
            r.raise_for_status()
            j = r.json()
            for pl in j.get("items", []):
                if pl:
                    by_name.setdefault(pl["name"], []).append(pl["id"])
            url = j["next"].replace(API, "") if j.get("next") else None
        for key, artists in days.items():
            d = date.fromisoformat(key)
            name = f"{d.day}. {d.month}. {d.year}"
            ids = by_name.get(name, [])
            if key in result or not ids:
                continue
            if len(ids) > 1:
                print(f"{key}: na Spotify je {len(ids)}x '{name}', beru první (zkontroluj duplicity)")
            result[key] = {"name": name, "id": ids[0], "url": f"https://open.spotify.com/playlist/{ids[0]}",
                           "artists": 0, "missing": []}
            print(f"{key}: doplněno")
        json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    for key, artists in days.items():
        if args.skip_existing and key in result:
            print(f"{key}: už existuje, přeskakuji")
            continue
        uris, missing = [], []
        for a in artists:
            found = find_cached(a, token, cache)
            (uris.extend(found) if found else missing.append(a))
        if not uris:
            print(f"{key}: nic nenalezeno, přeskakuji")
            continue
        d = date.fromisoformat(key)
        name = f"{d.day}. {d.month}. {d.year}"
        if key in result:
            pid = result[key]["id"]
            call("PUT", f"/playlists/{pid}/items", token, json={"uris": []})  # vyprázdnit
        else:
            r = call("POST", "/me/playlists", token,
                     json={"name": name, "public": True,
                           "description": "Interpreti z pražských koncertů tohoto dne"})
            r.raise_for_status()
            pid = r.json()["id"]
            # uložit hned, aby se při pádu playlist při dalším běhu nevytvářel znovu
            result[key] = {"name": name, "id": pid, "url": f"https://open.spotify.com/playlist/{pid}",
                           "artists": 0, "missing": []}
            json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        add_items(pid, uris, token)
        result[key] = {"name": name, "id": pid, "url": f"https://open.spotify.com/playlist/{pid}",
                       "artists": len(artists) - len(missing), "missing": missing}
        print(f"{key}: {len(uris)} skladeb, {len(missing)} interpretů nenalezeno")
        json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

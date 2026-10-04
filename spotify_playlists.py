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

CONCERTS = "concerts.json"
OUT = "playlists.json"
CACHE = "spotify_cache.json"  # interpret -> URI skladby (nebo null), šetří požadavky
REDIRECT = "http://127.0.0.1:8888/callback"
SCOPE = "playlist-modify-public"
API = "https://api.spotify.com/v1"

# Události, které nejsou koncert konkrétního interpreta
SKIP_RE = re.compile(
    r"\b(dj|party|video party|jam session|jam|open mic|quiz|kvíz|karaoke|festival|fest|"
    r"vstupenk|ticket|dárkov|voucher|koncert|special new year|silvestr)\b",
    re.I,
)


STOP = {"band", "kapela", "support", "cabaret", "natural", "after", "early show", "live nation",
        "klub zadan", "hallelujah", "melodic journey", "ambient session", "trubku", "no", "es", "au",
        "gr", "swe", "rattle", "skyline", "orion", "stress", "revo", "sloth", "protimluv"}


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def extract_artists(title):
    """Z názvu akce vytáhne pravděpodobné jména interpretů (heuristika)."""
    if SKIP_RE.search(title) and len(title.split()) < 3:
        return []
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", title)          # (CZ), (AUS) ...
    t = re.split(r"\s[-–—:]\s|:\s| – | — ", t)[0]               # podtitul za pomlčkou/dvojtečkou
    t = re.split(r"\s(?:k[řr]est|narozeninov|pro[šs]li|celebrating|live at)\b", t, flags=re.I)[0]
    parts = re.split(r"\s*(?:\+|,|\s/\s|\sa\s|\sand\s|\swith\s|\s&\s|\sfeat\.?\s|\sfeaturing\s)\s*", t)
    out = []
    for p in parts:
        p = p.strip(" .-–—")
        if len(p) < 3 or len(p) > 50 or SKIP_RE.fullmatch(p.lower()) or norm(p) in STOP:
            continue
        if re.search(r"special guests?|hosté|host", p, re.I):
            continue
        out.append(p)
    return out


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
        key = d.isoformat()
        for a in extract_artists(e["title"]):
            days.setdefault(key, {})[norm(a)] = a
    return {k: sorted(v.values(), key=str.lower) for k, v in sorted(days.items())}


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
        return r
    return r


def find_cached(name, token, cache):
    key = norm(name)
    if key not in cache:
        cache[key] = find_tracks(name, token)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return cache[key]


def find_tracks(name, token):
    """Vrátí URI nejpopulárnější skladby, jejíž interpret přesně odpovídá názvu (jinak nic)."""
    time.sleep(1)  # šetrně k limitu Spotify
    r = call("GET", "/search", token, params={"q": f'artist:"{name}"', "type": "track", "limit": 10})
    if r.status_code != 200:
        return []
    want = norm(name)
    hits = [t for t in r.json().get("tracks", {}).get("items", [])
            if any(norm(a["name"]) == want for a in t["artists"])]
    if not hits:
        return []
    return [max(hits, key=lambda t: t.get("popularity", 0))["uri"]]


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
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    for key, artists in days.items():
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
        add_items(pid, uris, token)
        result[key] = {"name": name, "id": pid, "url": f"https://open.spotify.com/playlist/{pid}",
                       "artists": len(artists) - len(missing), "missing": missing}
        print(f"{key}: {len(uris)} skladeb, {len(missing)} interpretů nenalezeno")
        json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

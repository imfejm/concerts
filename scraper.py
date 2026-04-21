#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Praha Koncerty — Scraper
========================
Stahuje program z pražských klubů a ukládá do concerts.json.

Spuštění:
    pip install requests beautifulsoup4
    python scraper.py

Pro automatické spouštění každý den:
  - Linux/Mac: přidej do cronu:  0 6 * * * python3 /cesta/ke/scraper.py
  - Windows:   nastav v Task Scheduleru
"""

import json
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def get_soup(url, timeout=15):
    """Stáhne stránku a vrátí BeautifulSoup objekt."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [WARN] Chyba při stahování {url}: {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────
#  ŽÁNRY — pomocné funkce
# ─────────────────────────────────────────────────────────────

# Klíčová slova řazená od delších po kratší, aby "black metal" > "metal"
GENRE_KEYWORDS = [
    "drum and bass", "drum & bass", "black metal", "death metal", "hard rock",
    "heavy metal", "post-rock", "post rock", "post punk", "post-punk",
    "post-metal", "post metal", "noise rock", "dark ambient",
    "indie pop", "indie rock", "art rock", "nu metal", "glam rock",
    "singer-songwriter", "world music", "latin jazz", "vocal jazz",
    "trip-hop", "trip hop", "hip hop", "hip-hop", "r&b", "rnb", "electric blues",
    "electro-pop", "electro pop",
    "psychedelic rock", "psychedelic", "alternative rock", "alternativní rock",
    "alternativa", "alternative", "alternativní",
    "electronica", "electronic", "elektronika",
    "psytrance", "hardstyle", "hardcore", "techno", "house", "trance",
    "dubstep", "breakbeat", "ambient", "dnb",
    "prog", "progressive", "fusion",
    "industrial", "noise rock", "shoegaze", "drone",
    "stoner", "sludge", "doom", "grindcore", "grind", "thrash", "screamo",
    "metal", "rock", "punk", "indie", "pop", "jazz", "blues", "soul",
    "funk", "swing", "bebop", "dixieland",
    "folk", "country", "reggae", "ska", "celtic",
    "písničkářství", "písničkář", "šanson", "chanson",
    "klasika", "classical", "noise", "experimental",
    "electro", "rap", "trap", "grime",
]

# URL venues kde žánr není dostupný — přeskočit detail fetch
_GENRE_SKIP_URLS = {
    "https://www.vagon.cz/dnes.php",
}

# Slova která nejsou žánr — výsledek se nahradí prázdným stringem
_GENRE_BLACKLIST = {
    "concert", "koncert", "koncertní", "festival / koncertní přehlídka",
    "literárně-hudební večer", "benefit",
}

# Normalizace variant na kanonický tvar
_GENRE_NORMALIZE = {
    "hip hop":          "hip-hop",
    "hiphop":           "hip-hop",
    "drum and bass":    "drum & bass",
    "drum&bass":        "drum & bass",
    "dnb":              "drum & bass",
    "electronic":       "elektronika",
    "elektronické":     "elektronika",
    "elektronická":     "elektronika",
    "elektronická hudba": "elektronika",
    "alternative":      "alternativa",
    "alternativní rock": "alternativa",
    "alternativní":     "alternativa",
    "post punk":        "post-punk",
    "post rock":        "post-rock",
    "post metal":       "post-metal",
    "trip hop":         "trip-hop",
    "electro-pop":      "electro",
    "electro pop":      "electro",
    "grind":            "grindcore",
    "písničkář":        "písničkářství",
    "klasická hudba":   "klasika",
    "r&b":              "r&b",
    "rnb":              "r&b",
}


def normalize_genre(genre_str):
    """Normalizuje žánrový string — sloučí varianty, odstraní false positives."""
    if not genre_str:
        return ""
    parts = [p.strip().lower() for p in genre_str.split(",") if p.strip()]
    normalized = []
    for part in parts:
        # Blacklist
        if part in _GENRE_BLACKLIST:
            continue
        # Přeskoč příliš dlouhé nebo nesmyslné hodnoty
        if len(part) > 50:
            continue
        # Normalizuj varianty
        part = _GENRE_NORMALIZE.get(part, part)
        if part and part not in normalized:
            normalized.append(part)
    return ", ".join(normalized)


def extract_genre_from_text(text):
    """Najde žánrová klíčová slova v textu, vrátí normalizovaný string."""
    if not text:
        return ""
    text_lower = text.lower()
    found = []
    for kw in GENRE_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower) and kw not in found:
            found.append(kw)
        if len(found) >= 4:
            break
    return normalize_genre(", ".join(found))


def load_existing_genres():
    """Načte stávající concerts.json a vrátí dva slovníky pro cache žánrů.
    Vrací: (url_cache, key_cache)
    - url_cache:  url -> genre
    - key_cache:  (title_lower, date, venue) -> genre
    """
    url_cache = {}
    key_cache = {}
    try:
        with open("concerts.json", encoding="utf-8") as f:
            data = json.load(f)
        for e in data.get("events", []):
            genre = e.get("genre", "").strip()
            if not genre:
                continue
            url = e.get("url", "")
            if url:
                url_cache[url] = genre
            k = (e.get("title", "").lower().strip(), e.get("date", ""), e.get("venue", ""))
            key_cache[k] = genre
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return url_cache, key_cache


def fetch_genre_from_detail(url):
    """Stáhne detail stránku akce a extrahuje žánr. Vrátí string nebo ''."""
    if not url or url in _GENRE_SKIP_URLS:
        return ""

    # Facebook blokuje boty — popis akce je za přihlášením, zbytečné zkoušet
    if "facebook.com" in url or "fb.me" in url:
        return ""

    import time
    time.sleep(0.3)  # zdvořilostní pauza

    soup = get_soup(url)
    if not soup:
        return ""

    # Odstraň navigaci a boilerplate
    for tag in soup(["nav", "header", "footer", "script", "style", "noscript"]):
        tag.decompose()

    # Speciální případ: Roxy — hashtags (#house #techno)
    if "roxy.cz" in url:
        tags = soup.find_all(string=re.compile(r"#\w+"))
        if tags:
            raw = " ".join(str(t) for t in tags)
            genres = re.findall(r"#(\w[\w&-]*)", raw)
            # Odfiltruj ne-žánrové tagy (live, dj, free...)
            skip = {"live", "dj", "free", "mondays", "club", "event"}
            genres = [g for g in genres if g.lower() not in skip]
            if genres:
                return ", ".join(genres[:4])

    # Speciální případ: MeetFactory — popis je v #text_equal uvnitř .main-detail
    if "meetfactory.cz" in url:
        el = soup.select_one("#text_equal") or soup.select_one(".main-detail .md-right")
        if el:
            return extract_genre_from_text(el.get_text(" ", strip=True))

    # Speciální případ: Forum Karlín — "Hudba / Pop / Rock"
    if "forumkarlin.cz" in url:
        for el in soup.find_all(string=re.compile(r"Hudba\s*/", re.I)):
            text = el.strip()
            # Vrať jen část za "Hudba / "
            parts = re.split(r"Hudba\s*/\s*", text, flags=re.I)
            if len(parts) > 1:
                return parts[1].strip()[:80]

    # Obecný přístup — najdi hlavní textový obsah
    description = ""
    for selector in [
        ".event-description", ".description", ".perex", ".about",
        "[class*='description']", "[class*='perex']", "[class*='event-text']",
        "article p", ".event-detail p", ".content p", "main p",
    ]:
        els = soup.select(selector)
        if els:
            candidate = " ".join(el.get_text(" ", strip=True) for el in els[:5])
            if len(candidate) > 80:
                description = candidate
                break

    if not description:
        main = (soup.find("main") or soup.find("article")
                or soup.find(id=re.compile(r"content|main", re.I)))
        if main:
            description = main.get_text(" ", strip=True)[:800]

    if not description:
        description = soup.get_text(" ", strip=True)[:800]

    return extract_genre_from_text(description)


# ─────────────────────────────────────────────────────────────
#  ROCK CAFÉ  (rockcafe.cz)
# ─────────────────────────────────────────────────────────────
def scrape_rockcafe():
    print("* Rock Café...")
    soup = get_soup("https://rockcafe.cz/cs/program/")
    if not soup:
        return []

    events = []
    base = "https://rockcafe.cz"
    cards = soup.select("a[href*='/program/']")

    for card in cards:
        # Karty mají obrázek + h2 + text s datem
        h2 = card.find("h2")
        img = card.find("img")
        if not h2 or not img:
            continue

        title = h2.get_text(strip=True)
        # Datum je v textu karty — formát "Pátek 17.4.2026, 16:30"
        text = card.get_text(" ", strip=True)
        date_match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", text)
        time_match = re.search(r"(\d{2}:\d{2})", text)

        # Kategorie
        category = "hudba"
        for cat in ["divadlo", "galerie", "hudba"]:
            if cat in text.lower():
                category = cat
                break

        href = card.get("href", "")
        if not href.startswith("http"):
            href = base + href

        events.append({
            "title": title,
            "date": date_match.group(1) if date_match else "",
            "time": time_match.group(1) if time_match else "",
            "venue": "Rock Café",
            "category": category,
            "url": href,
            "image": img.get("src", ""),
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  LUCERNA MUSIC BAR  (musicbar.cz)
# ─────────────────────────────────────────────────────────────
def scrape_musicbar():
    print("* Lucerna Music Bar...")
    soup = get_soup("https://musicbar.cz/cs/program/")
    if not soup:
        return []

    events = []
    base = "https://musicbar.cz"
    cards = soup.select("a[href*='/program/']")

    for card in cards:
        img = card.find("img")
        if not img:
            continue
        text = card.get_text(" ", strip=True)
        if not text:
            continue

        # Datum — formát "10/4" nebo "11/4" v textu
        date_match = re.search(r"(\d{1,2}/\d{1,2})", text)
        time_match = re.search(r"(\d{2}:\d{2})", text)

        # Název — většinou největší blok textu bez datumu
        title_raw = re.sub(r"(Dnes|Zítra|Pondělí|Úterý|Středa|Čtvrtek|Pátek|Sobota|Neděle)", "", text)
        title_raw = re.sub(r"\d{1,2}/\d{1,2}", "", title_raw)
        title_raw = re.sub(r"\d{2}:\d{2}", "", title_raw)
        title_raw = re.sub(r"(Koupit vstupenky|Vstupenky na pokladně|Vyprodáno|Více informací)", "", title_raw)
        title = " ".join(title_raw.split()).strip()

        if not title or len(title) < 3:
            continue

        href = card.get("href", "")
        if not href.startswith("http"):
            href = base + href

        events.append({
            "title": title,
            "date": date_match.group(1).replace("/", ".") + f".{datetime.now().year}" if date_match else "",
            "time": time_match.group(1) if time_match else "",
            "venue": "Lucerna Music Bar",
            "category": "hudba",
            "url": href,
            "image": img.get("src", ""),
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  KLUB 007 STRAHOV  (klub007strahov.cz)
# ─────────────────────────────────────────────────────────────
def scrape_klub007():
    print("* Klub 007 Strahov...")
    soup = get_soup("https://klub007strahov.cz/program/")
    if not soup:
        return []

    events = []
    
    # Czech month mapping — nominative i genitiv, červenec musí být před červen
    czech_months = {
        'leden': '01', 'ledna': '01',
        'únor': '02', 'února': '02',
        'březen': '03', 'března': '03',
        'duben': '04', 'dubna': '04',
        'květen': '05', 'května': '05',
        'červenec': '07', 'července': '07',
        'červen': '06', 'června': '06',
        'srpen': '08', 'srpna': '08',
        'září': '09',
        'říjen': '10', 'října': '10',
        'listopad': '11', 'listopadu': '11',
        'prosinec': '12', 'prosince': '12',
    }
    # Pořadí důležité: červenec před červen
    month_pattern = re.compile(
        r'(leden|ledna|únor|února|březen|března|duben|dubna|května|květen'
        r'|červenec|července|červen|června|srpen|srpna|září|října|říjen'
        r'|listopad|listopadu|prosinec|prosince)', re.I
    )

    # Každá akce je v elementu s třídou .event
    event_divs = soup.select('.event')

    for event_div in event_divs:
        # Získej URL z prvního <a> tagu
        link = event_div.find('a', href=True)
        url = link.get('href', '') if link else ''

        image = ''  # klub007strahov.cz blokuje hotlinking

        # Získej den z <em class="date">
        date_elem = event_div.find('em', class_='date')
        day = date_elem.get_text(strip=True) if date_elem else ''

        # Získej celý text na analýzu
        text = event_div.get_text(' ', strip=True)

        # Extrahuj měsíc
        month_match = month_pattern.search(text)
        month_val = ''
        if month_match:
            month_name = month_match.group(1).lower()
            month_val = czech_months.get(month_name, '')
        
        # Extrahuj čas (první výskyt HH:MM)
        time_match = re.search(r'(\d{2}):(\d{2})', text)
        time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ''
        
        # Extrahuj titul - text mezi "HH:MM HH:MM " a " Detail akce" nebo konec
        title = ""
        event_genre = ""
        title_match = re.search(r'\d{2}:\d{2}\s+\d{2}:\d{2}\s+(.+?)(?:\s+Detail akce|$)', text)
        if title_match:
            title = title_match.group(1)
            
            # Odstraň kódy zemí: (de), (cz), (fi/gr), (uk/us), atd.
            title = re.sub(r'\s*\([a-z]{2}(?:/[a-z]{2})*\)\s*', ' ', title, flags=re.I)
            
            # Zachyť žánr před odstraněním
            genre_pattern = r'(?:\s|(?<=[A-Z]))+(metal|rock|punk|indie|pop|jazz|electronic|sludge|stoner|doom|grind|hardcore|folk|blues|reggae|rap|hip|house|techno|trance|dubstep|drum|bass|country|gospel|classical|experimental|noise|ambient|synth|alternative|screamo|prog|fusion|groove|funk|soul|disco|latin|salsa|tango|world|gothic|industrial|death|post|psychedelic|power|speed|black|heavy|crust|ska|rockroll|soulfunk|psychobilly|benefit).*$'
            genre_match = re.search(genre_pattern, title, flags=re.I)
            event_genre = genre_match.group(0).strip().strip('/').strip() if genre_match else ''
            # Odstraň žánry z titulu
            title = re.sub(genre_pattern, '', title, flags=re.I)
            
            # Odstraň všechno po "/"
            title = re.sub(r'\s*/.*$', '', title)
            
            # Vyčisti: normalizuj mezery
            title = ' '.join(title.split()).strip()
        
        # Sestav datum — pokud měsíc je dřívější než aktuální, patří do příštího roku
        if day and month_val:
            from datetime import date as _date
            today_d = _date.today()
            year = today_d.year
            if int(month_val) < today_d.month:
                year += 1
            date_str = f"{day.zfill(2)}.{month_val}.{year}"
        else:
            date_str = ''
        
        # Přidej akci pokud máme titul a datum
        if title and date_str and len(title) > 2 and len(title) < 300:
            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "Klub 007 Strahov",
                "category": "hudba",
                "url": url,
                "image": image,
                "genre": event_genre,
            })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  CROSS CLUB  (crossclub.cz)
# ─────────────────────────────────────────────────────────────
def scrape_crossclub():
    print("* Cross Club...")
    soup = get_soup("https://www.crossclub.cz/cs/program/")
    if not soup:
        return []

    events = []
    base = "https://www.crossclub.cz"

    # Akce jsou v článcích nebo divcích s odkazem na program
    items = soup.select("a[href*='/program/']")

    for item in items:
        h2 = item.find(["h2", "h3"])
        img = item.find("img")
        if not h2:
            continue

        title = h2.get_text(strip=True)
        text = item.get_text(" ", strip=True)

        # Datum — formát "10.04.2026" nebo "10.04."
        date_match = re.search(r"(\d{1,2}\.\d{2}\.(?:\d{4})?)", text)
        date_text = date_match.group(1) if date_match else ""
        if date_text and not re.search(r"\d{4}", date_text):
            date_text += str(datetime.now().year)

        href = item.get("href", "")
        if not href.startswith("http"):
            href = base + href

        events.append({
            "title": title,
            "date": date_text,
            "time": "",
            "venue": "Cross Club",
            "category": "hudba",
            "url": href,
            "image": img.get("src", "") if img else "",
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  PALÁC AKROPOLIS  (palacakropolis.cz)
# ─────────────────────────────────────────────────────────────
def scrape_akropolis():
    print("* Palác Akropolis...")
    try:
        # ✨ Parsujeme HTML tabulku bez Playwright — mnohem rychlejší!
        soup = get_soup("https://palacakropolis.cz/work/33298")
        if not soup:
            return []
        
        events = []
        year = datetime.now().year
        
        # Odstraň script a style tagy
        for tag in soup(['script', 'style']):
            tag.decompose()
        
        # Hledej VŠECHNY TR s event_id — tabulka obsahuje Seznam akcí  
        all_trs = soup.find_all('tr')
        seen = set()
        
        # Postranní: Najdi Default image pro Akropolis (všechny eventy mají stejný)
        default_image = ""
        for tr in all_trs:
            imgs = tr.find_all('img')
            if imgs:
                for img in imgs:
                    src = img.get('src', '')
                    if src and ('lead_photo' in src or 'cover' in src.lower()):
                        if src.startswith('/'):
                            default_image = f"https://palacakropolis.cz{src}"
                        else:
                            default_image = src
                        break
                if default_image:
                    break
        
        # Vytvoř mapování obrázků -> event_id z .image_box_auto prvků (featured události v horní části)
        image_map = {}  # event_id -> image_url
        image_boxes = soup.find_all(True, class_='image_box_auto')
        for img in image_boxes:
            src = img.get('src', '')
            if not src:
                continue

            # Projdi nadřazené prvky a hledej event_id
            current = img.parent
            for _ in range(10):
                if not current:
                    break

                parent_html = str(current)
                event_match = re.search(r'event_id=(\d+)', parent_html)

                if event_match:
                    event_id = event_match.group(1)
                    # Vytvoř absolutní URL
                    if src.startswith('/'):
                        image_map[event_id] = f"https://palacakropolis.cz{src}"
                    else:
                        image_map[event_id] = src
                    break

                current = current.parent

        for tr in all_trs:
            tr_html = str(tr)
            
            # Hledej event_id
            if 'event_id=' not in tr_html:
                continue
            
            event_match = re.search(r'event_id=(\d+)', tr_html)
            if not event_match:
                continue
            
            event_id = event_match.group(1)
            if event_id in seen:
                continue
            seen.add(event_id)
            
            # Hledej datum v TD se třídou banner_popup_date
            popup_date_td = tr.find('td', class_='banner_popup_date')
            date_str = ""
            
            if popup_date_td:
                date_text = popup_date_td.get_text(strip=True)
                date_match = re.search(r'(\d{1,2})\.\s*(\d{1,2})', date_text)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month = date_match.group(2).zfill(2)
                    try:
                        m = int(month)
                        if 1 <= m <= 12:
                            date_str = f"{day}.{month}.{year}"
                    except:
                        pass
            
            # Fallback: hledáme datum v textu TR pokud jsme nenašli
            if not date_str:
                tr_text = tr.get_text(strip=True)
                date_matches = list(re.finditer(r'(\d{1,2})\.\s*(\d{1,2})', tr_text))
                
                for match in date_matches:
                    day = match.group(1).zfill(2)
                    month = match.group(2).zfill(2)
                    try:
                        m = int(month)
                        if 1 <= m <= 12:
                            date_str = f"{day}.{month}.{year}"
                            break
                    except:
                        continue
            
            # Hledej název v <a> tagu s event_id
            a_tag = tr.find('a', href=re.compile(r'event_id'))
            title = a_tag.get_text(strip=True) if a_tag else ""
            
            # Očisti název
            title = re.sub(r'[►◄▄✓✗]', '', title)
            title = " ".join(title.split()).strip()
            
            # Hledej čas v textu TR
            tr_text = tr.get_text(strip=True)
            time_match = re.search(r'(\d{2}):(\d{2})', tr_text)
            time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ""
            
            # Vyber obrázek z featured sekce (pokud existuje)
            event_image = image_map.get(event_id, "")

            # Přijmi event
            if title and len(title) > 2 and len(title) < 300 and date_str:
                # Přeskoč nežádoucí akce
                if "nebojsy" in title.lower() or "divadlo" in title.lower():
                    continue
                category = "hudba"
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Palác Akropolis",
                    "category": category,
                    "url": f"https://palacakropolis.cz/work/33298?event_id={event_id}&no=62&page_id=33824",
                    "image": event_image,
                    "_event_id": event_id,  # dočasně pro stahování obrázků
                })

        # Pro události bez obrázku stáhni detailní stránku
        missing = [e for e in events if not e.get("image")]
        if missing:
            print(f"   Stahuji obrázky pro {len(missing)} akcí z detailních stránek...")
            for event in missing:
                eid = event.get("_event_id")
                if not eid:
                    continue
                detail_url = f"https://palacakropolis.cz/work/33298?event_id={eid}&no=62&page_id=33824"
                detail_soup = get_soup(detail_url)
                if detail_soup:
                    img_tag = detail_soup.find('img', class_='galery_out_img')
                    if img_tag:
                        src = img_tag.get('src', '')
                        if src:
                            if src.startswith('/'):
                                event["image"] = f"https://palacakropolis.cz{src}"
                            else:
                                event["image"] = src

        # Odstraň dočasný klíč _event_id ze všech eventů
        for event in events:
            event.pop("_event_id", None)

        print(f"   [OK] {len(events)} akcí")
        return events

    except Exception as e:
        print(f"  [WARN] Chyba Akropolis: {e}", file=sys.stderr)
        return []


# ─────────────────────────────────────────────────────────────
#  VAGON  (vagon.cz)
# ─────────────────────────────────────────────────────────────
def scrape_vagon():
    print("* Vagon...")
    soup = get_soup("https://www.vagon.cz/dnes.php")
    if not soup:
        return []

    events = []
    
    # Najdi tabulku s program
    table = soup.find('table')
    if not table:
        print(f"   [WARN] Tabulka nenalezena")
        return []

    rows = table.find_all('tr')
    if not rows:
        print(f"   [WARN] Žádné řádky v tabulce")
        return []

    # Hledej měsíc/rok v nadpisu stránky
    month, year = 4, datetime.now().year  # Default: duben letošního roku
    h3_tag = soup.find('h3')
    if h3_tag:
        text = h3_tag.get_text(strip=True)
        # Pokus se parsovat měsíc a rok (např. "duben 2026")
        year_match = re.search(r'(\d{4})', text)
        if year_match:
            year = int(year_match.group(1))

    # Parsuj řádky (přeskoč header)
    for row in rows[1:]:
        try:
            cols = row.find_all('td')
            if len(cols) < 5:
                continue

            # Extrahuj pole
            cena = cols[0].get_text(strip=True)
            den_tydne = cols[1].get_text(strip=True)
            den_cislo = cols[2].get_text(strip=True)
            nazev = cols[3].get_text(strip=True)
            cas_info = cols[4].get_text(strip=True)

            # Filtruj ZAVŘENO
            if not nazev or nazev.upper() == "ZAVŘENO":
                continue

            # Parsuj čas
            time_match = re.search(r'(\d{2}):(\d{2})', cas_info)
            time_str = time_match.group(0) if time_match else ""

            # Vytvoř datum (den_cislo.4.year)
            try:
                day_num = int(den_cislo)
                date_str = f"{day_num}.4.{year}"
            except:
                continue

            # Pokud je název jen čas (např. "20:00 MUSIC VIDEO PARTY"), 
            # extrahuj správný název (bez času)
            if re.match(r'^\d{2}:\d{2}', nazev):
                # Název začíná časem, vezmi všechno za prvním časem
                nazev = re.sub(r'^\d{2}:\d{2}\s*', '', nazev).strip()

            events.append({
                "title": nazev,
                "date": date_str,
                "time": time_str,
                "venue": "Vagon",
                "category": "hudba",
                "url": "https://www.vagon.cz/dnes.php",
                "image": "",
            })
        except Exception as e:
            continue

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  CAFE V LESE  (cafevlese.cz)
# ─────────────────────────────────────────────────────────────
def scrape_cafevlese():
    print("* Cafe v lese...")

    czech_months_short = {
        'led': '01', 'úno': '02', 'břě': '03', 'dub': '04',
        'kvě': '05', 'čvn': '06', 'čer': '06', 'čvc': '07', 'srp': '08',
        'zář': '09', 'říj': '10', 'lis': '11', 'pro': '12'
    }

    events = []
    seen_urls = set()

    # Stáhni hlavní stránku a vytáhni MEC skin ID + atts pro AJAX
    home_soup = get_soup("https://cafevlese.cz/")
    if not home_soup:
        return []

    home_html = str(home_soup)
    atts_match = re.search(r'atts: "([^"]+)"', home_html)
    if not atts_match:
        print("  [WARN] Cafe v lese: nelze najít MEC atts", file=sys.stderr)
        return []

    atts = atts_match.group(1)
    ajax_url = "https://cafevlese.cz/wp-admin/admin-ajax.php"

    def parse_articles(soup, year):
        for article in soup.find_all('article', class_='mec-event-article'):
            url = article.get('data-href', '')
            if url in seen_urls:
                continue
            seen_urls.add(url)

            style = article.get('style', '')
            image_url = ''
            if style:
                img_match = re.search(r"url\('([^']+)'\)", style)
                if img_match:
                    image_url = img_match.group(1)

            title_link = article.find('a', class_='mec-color-hover')
            title = title_link.get_text(strip=True) if title_link else ''

            date_label = article.find('span', class_='mec-start-date-label')
            date_text = date_label.get_text(strip=True) if date_label else ''

            time_div = article.find('div', class_='mec-event-time')
            time_str = ''
            if time_div:
                time_match = re.search(r'(\d{2}:\d{2})', time_div.get_text())
                if time_match:
                    time_str = time_match.group(1)

            date_str = ''
            if date_text:
                parts = date_text.split()
                if len(parts) == 2:
                    day = parts[0].zfill(2)
                    month_short = parts[1].lower()[:3]
                    for short, month_num in czech_months_short.items():
                        if short in month_short:
                            date_str = f"{day}.{month_num}.{year}"
                            break

            if title and date_str:
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Café v lese",
                    "category": "hudba",
                    "url": url,
                    "image": image_url,
                })

    # Parsuj aktuální měsíc z hlavní stránky
    from datetime import date
    today = date.today()
    parse_articles(home_soup, today.year)

    # Načti další měsíce přes AJAX (stejně jako klik na šipku)
    months_to_fetch = []
    for i in range(1, 9):
        m = (today.month - 1 + i) % 12 + 1
        y = today.year + ((today.month - 1 + i) // 12)
        months_to_fetch.append((y, m))

    for (year, month) in months_to_fetch:
        try:
            post_data = f"action=mec_tile_load_month&mec_year={year}&mec_month={month:02d}&{atts}&apply_sf_date=1"
            r = requests.post(ajax_url, data=post_data, headers={
                **HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://cafevlese.cz/",
            }, timeout=15)
            r.raise_for_status()
            resp = r.json()
            month_html = resp.get("month", "")
            if month_html:
                month_soup = BeautifulSoup(month_html, "html.parser")
                parse_articles(month_soup, year)
        except Exception as e:
            print(f"  [WARN] Cafe v lese AJAX {year}-{month:02d}: {e}", file=sys.stderr)

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  FUTURUM  (futurum.musicbar.cz)
# ─────────────────────────────────────────────────────────────
def scrape_futurum():
    print("* Futurum Music Bar...")
    soup = get_soup("https://futurum.musicbar.cz/program/")
    if not soup:
        return []

    events = []
    base = "https://futurum.musicbar.cz"
    cards = soup.select("a[href*='/program/']")

    for card in cards:
        img = card.find("img")
        if not img:
            continue

        # Extrahuj datum z <div class="line-date"> prvku
        date_div = card.find("div", class_="line-date")
        date_str = ""
        if date_div:
            # Hledej datum s tečkami přímý pattern (Pátek10.04.2026)
            match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', date_div.get_text(strip=True))
            if match:
                date_str = match.group(1)

        # Extrahuj čas z textu
        time_match = re.search(r"(\d{2}:\d{2})", card.get_text())
        time_str = time_match.group(1) if time_match else ""

        # Extrahuj název akce - všechno po času v textu
        text = card.get_text(" ", strip=True)
        
        # Odstraň den v týdnu
        title_raw = re.sub(r"(Dnes|Zítra|Pondělí|Úterý|Středa|Čtvrtek|Pátek|Sobota|Neděle)", "", text)
        
        # Odstraň datum
        title_raw = re.sub(r"\d{1,2}\.\d{1,2}\.\d{4}", "", title_raw)
        
        # Odstraň čas
        title_raw = re.sub(r"\d{2}:\d{2}", "", title_raw)
        
        # Odstraň specifické texty
        title_raw = re.sub(r"(Koupit vstupenky|Vstupenky na pokladně|Vyprodáno|Více informací)", "", title_raw)
        
        # Vyčisti: normalizuj mezery
        title = " ".join(title_raw.split()).strip()

        if not title or len(title) < 3:
            continue

        href = card.get("href", "")
        if not href.startswith("http"):
            href = base + href

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Futurum Music Bar",
            "category": "hudba",
            "url": href,
            "image": img.get("src", ""),
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  GOOUT  (goout.net)
# ─────────────────────────────────────────────────────────────
def scrape_goout():
    """
    GoOut je single-page aplikace (React) — čistý requests/BS4 nestačí.
    Ale GoOut má veřejné API! Používáme ho místo scrapování.
    """
    print("* GoOut (Praha - koncerty)...")
    url = "https://goout.net/services/feeder/v2/schedules"
    params = {
        "category": "concert",
        "locality": "prague",
        "lang": "cs",
        "limit": 50,
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [WARN] GoOut API chyba: {e}", file=sys.stderr)
        return []

    events = []
    for item in data.get("schedules", []):
        event = item.get("event", {})
        performance = item.get("performance", {})
        venue = item.get("venue", {})

        start = item.get("startAt", "")
        date_text = ""
        time_text = ""
        if start:
            try:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                date_text = dt.strftime("%-d.%-m.%Y")
                time_text = dt.strftime("%H:%M")
            except Exception:
                pass

        events.append({
            "title": performance.get("name") or event.get("name", ""),
            "date": date_text,
            "time": time_text,
            "venue": venue.get("name", "Praha"),
            "category": "hudba",
            "url": f"https://goout.net{item.get('url', '')}",
            "image": (event.get("images") or [{}])[0].get("url", ""),
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  ROXY  (roxy.cz)
# ─────────────────────────────────────────────────────────────
def scrape_roxy():
    """Scraper pro Roxy.cz - čte items z event-list"""
    print("* Roxy...")
    
    soup = get_soup("https://www.roxy.cz/#program")
    if not soup:
        return []
    
    events = []
    
    # Najdi event-list (hlavní seznam s data-date atributy)
    event_list = soup.find('div', class_='event-list')
    if not event_list:
        return []
    
    items = event_list.find_all('a', class_='item')
    
    for item in items:
        try:
            # Extrahuj artist (H2)
            h2 = item.find('h2')
            artist = h2.get_text(strip=True) if h2 else ""
            
            # Extrahuj tag/subtitle (H3) - např. (SK), (DE), (CZ)
            h3 = item.find('h3')
            tag = h3.get_text(strip=True) if h3 else ""
            
            # Extrahuj datum z textu - formát "P.10/04 Artist..."
            text = item.get_text(strip=True)
            date_match = re.search(r'(\d{1,2})/(\d{2})', text)
            
            if not date_match or not artist:
                continue
            
            day = date_match.group(1)
            month = date_match.group(2)
            year = 2026  # Všechny items mají data-date="042026"
            
            date_str = f"{day}.{month}.{year}"
            
            # Href
            href = item.get('href', '')
            if href.startswith('/'):
                href = 'https://www.roxy.cz' + href
            
            # ExtrahujImage z background-image CSS
            image_url = ""
            divs = item.find_all('div')
            for div in divs:
                style = div.get('style', '')
                # Extrahuj URL z background-image:url(...)
                img_match = re.search(r'background-image:\s*url\(([^)]+)\)', style)
                if img_match:
                    rel_path = img_match.group(1).strip("'\"")
                    # Konvertuj na absolutní URL
                    if rel_path.startswith('/'):
                        image_url = 'https://www.roxy.cz' + rel_path
                    else:
                        image_url = 'https://www.roxy.cz/' + rel_path
                    break
            
            # Vytvoř název - Artist + tag
            title = artist
            if tag and tag != "":
                title = f"{artist} {tag}"
            
            events.append({
                "title": title,
                "date": date_str,
                "time": "",  # Časy nejsou v přehledu programu
                "venue": "Roxy",
                "category": "hudba",
                "url": href,
                "image": image_url,
            })
        except Exception as e:
            continue
    
    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  KAŠTAN  (kastan.cz)
# ─────────────────────────────────────────────────────────────
def scrape_kastan():
    """Scraper pro Kaštan.cz - pouze koncerty (stahuje všechny stránky)"""
    print("* Kaštan...")
    
    events = []
    base_url = "https://kastan.cz/"
    max_pages = 3  # Kaštan má max 3 stránky s akcemi
    
    for page in range(1, max_pages + 1):
        try:
            # Konstrukce URL se stránkováním
            url = base_url if page == 1 else f"{base_url}?paged={page}"
            
            soup = get_soup(url)
            if not soup:
                continue
            
            # Hledej všechny koncerty (elementy s akce_category-koncert NEBO akce_category-festival-koncertni-prehlidka)
            koncerty = soup.find_all(True, class_=re.compile('akce_category-koncert'))
            prehlidky = soup.find_all(True, class_=re.compile('festival-koncertni-prehlidka'))
            
            # Spojení - eliminuj duplikáty
            all_items = []
            seen_ids = set()
            for item in koncerty + prehlidky:
                item_id = item.get('data-id', item.get('id', str(item)))
                if item_id not in seen_ids:
                    all_items.append(item)
                    seen_ids.add(item_id)
            
            koncerty = all_items
            
            for koncert in koncerty:
                try:
                    # URL: z bc-link-whole-grid-card
                    link_div = koncert.find('div', class_='bc-link-whole-grid-card')
                    event_url = link_div.get('data-link-url', '') if link_div else ''
                    
                    # Obrázek
                    img = koncert.find('img')
                    image_src = img.get('src', '') if img else ''
                    
                    # Název: z h1 nebo program_nadpis
                    nadpis = koncert.find('h1') or koncert.find('div', class_='program_nadpis')
                    title = nadpis.get_text(strip=True) if nadpis else ''
                    
                    if not title or not event_url:
                        continue
                    
                    # Datum: z program_datum
                    datum_div = koncert.find('div', class_='program_datum')
                    datum_text = datum_div.get_text(strip=True) if datum_div else ''
                    
                    date_match = re.search(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})', datum_text)
                    date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}" if date_match else ""
                    
                    # Čas
                    time_match = re.search(r'(\d{1,2}):(\d{2})', datum_text)
                    time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ""

                    # Žánr: kratší <p> tagy v kontejneru, které nejsou datum ani název
                    event_genre = ""
                    for p in koncert.find_all('p'):
                        p_text = p.get_text(strip=True)
                        if (p_text and len(p_text) < 80
                                and p_text.lower() != title.lower()
                                and not re.search(r'\d{1,2}\.\s*\d{1,2}\.', p_text)):
                            event_genre = p_text
                            break

                    if not date_str:
                        continue

                    events.append({
                        "title": title,
                        "date": date_str,
                        "time": time_str,
                        "venue": "Kaštan",
                        "category": "hudba",
                        "url": event_url,
                        "image": image_src,
                        "genre": event_genre,
                    })
                
                except Exception as e:
                    print(f"  [WARN] Chyba při parsování jedné akce: {e}", file=sys.stderr)
                    continue
        
        except Exception as e:
            print(f"  [WARN] Chyba na stránce {page}: {e}", file=sys.stderr)
            continue
    
    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  MEET FACTORY  (meetfactory.cz)
# ─────────────────────────────────────────────────────────────
def scrape_meetfactory():
    """Scraper pro MeetFactory.cz - scrapuje hudbu, divadlo, atd."""
    print("* MeetFactory...")
    
    categories = [
        ('cs/program/hudba', 'hudba'),
        ('cs/program/divadlo', 'divadlo'),
        ('cs/program/ostatni', 'ostatni'),
        ('cs/program/galerie', 'galerie'),
        ('cs/program/rezidence', 'rezidence'),
    ]
    
    all_events = []
    
    ajax_headers = {**HEADERS, 'X-Requested-With': 'XMLHttpRequest'}

    seen_urls = set()

    for path, category in categories:
        page_num = 1
        while page_num <= 15:
            try:
                page_url = f"https://meetfactory.cz/{path}?page={page_num}"
                r = requests.get(page_url, headers=ajax_headers, timeout=20)
                if not r.ok:
                    break
                soup = BeautifulSoup(r.text, 'html.parser')
            except Exception as e:
                print(f"  [WARN] MeetFactory {path} p.{page_num}: {e}", file=sys.stderr)
                break

            # Hledej všechny ab-box divy (event items)
            event_boxes = soup.find_all('div', class_='ab-box')
            if not event_boxes:
                break

            new_on_page = 0
            for box in event_boxes:
                # Obrázek - seznam vrací miniatury 79x111, detail stránky má 320x426
                img = box.find('img', class_='program-image')
                image_url = ''
                if img:
                    image_url = img.get('src', '')
                    # Nahraď thumbnail velikost za plnou verzi používanou na detail stránce
                    image_url = image_url.replace('-79x111.jpg', '-320x426.jpg')
                # Konvertuj relativní cestu na absolutní URL
                if image_url and not image_url.startswith('http'):
                    image_url = 'https://meetfactory.cz' + image_url
                
                # Datum - v <p class="abb-date"><b>
                date_elem = box.find('b')
                date_text = date_elem.get_text(strip=True) if date_elem else ''
                
                # Čas - v <span> na řádku s datem
                date_p = box.find('p', class_='abb-date')
                time_text = ''
                if date_p:
                    spans = date_p.find_all('span')
                    if len(spans) >= 2:
                        time_text = spans[-1].get_text(strip=True)
                
                # Kategorie
                cat_link = box.find('a', class_='cat')
                actual_category = cat_link.get_text(strip=True).lower() if cat_link else category
                
                # Název - hledej <span class="h3_active"> NEBO <span itemprop="name">
                title = ""
                title_span = box.find('span', class_='h3_active')
                if not title_span:
                    title_span = box.find('span', {'itemprop': 'name'})
                if title_span:
                    title = title_span.get_text(strip=True)
                
                # URL
                detail_link = box.find('a', class_='abbl-detail')
                ev_url = detail_link.get('href', '') if detail_link else ''
                if ev_url and not ev_url.startswith('http'):
                    ev_url = 'https://meetfactory.cz' + ev_url

                # Pokud nemáme základní info nebo jsme to už viděli, přeskočme
                if not title or not date_text or ev_url in seen_urls:
                    continue
                seen_urls.add(ev_url)

                # Vytvoř datum ve správném formátu (např. "10. 4." -> "10.04.2026")
                date_match = re.match(r'(\d{1,2})\.\s*(\d{1,2})', date_text)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month = date_match.group(2).zfill(2)
                    date_formatted = f"{day}.{month}.2026"
                else:
                    date_formatted = ''

                if date_formatted:
                    new_on_page += 1
                    all_events.append({
                        "title": title,
                        "date": date_formatted,
                        "time": time_text,
                        "venue": "MeetFactory",
                        "category": actual_category,
                        "url": ev_url,
                        "image": image_url,
                    })

            # Pokud žádné nové akce, jsme na konci
            if new_on_page == 0:
                break
            page_num += 1

    print(f"   [OK] {len(all_events)} akcí")
    return all_events


# ─────────────────────────────────────────────────────────────
#  ATRIUM ŽIŽKOV  (atriumzizkov.cz)
# ─────────────────────────────────────────────────────────────
def scrape_atriumzizkov():
    """Scraper pro Atrium Žižkov - jen hudbu"""
    print("* Atrium Žižkov...")
    soup = get_soup("https://atriumzizkov.cz/program/")
    if not soup:
        return []

    events = []
    czech_months = {
        'ledna': '01', 'února': '02', 'března': '03', 'dubna': '04',
        'května': '05', 'června': '06', 'července': '07', 'srpna': '08',
        'září': '09', 'října': '10', 'listopadu': '11', 'prosince': '12'
    }

    items = soup.find_all('div', class_='loop-item')

    for item in items:
        try:
            # Opusť pokud není hudba
            link = item.find('a', class_='card-btn', href=True)
            url = link.get('href', '') if link else ''
            
            # Filtruj jen hudbu
            if '/hudba/' not in url:
                continue

            # Extrahuj nadpis
            title_div = item.find('div', class_='title')
            title = title_div.get_text(strip=True) if title_div else ''
            
            if not title or len(title) < 2:
                continue

            # Extrahuj datum
            date_div = item.find('div', class_='date')
            date_text = date_div.get_text(strip=True) if date_div else ''
            
            # Parsuj datum - formát "čtvrtek 16. 4. v 19.30"
            date_str = ''
            time_str = ''
            if date_text:
                # Extrahuj čas - hledej "19.30" nebo "19:30"
                time_match = re.search(r'(\d{1,2})[:.](\d{2})', date_text)
                if time_match:
                    time_str = f"{time_match.group(1)}:{time_match.group(2)}"
                
                # Extrahuj den, měsíc
                num_match = re.search(r'(\d{1,2})\.\s*(\d{1,2})', date_text)
                if num_match:
                    day = num_match.group(1)
                    month = num_match.group(2)
                    date_str = f"{day}.{month}.2026"

            # Extrahuj obrázek
            img = item.find('img')
            image = ''
            if img:
                src = img.get('src', '')
                if src:
                    # Vezmi základní URL bez velikostních variant
                    image = src.split('?')[0] if '?' in src else src
                    # Pokud je relativní URL, udělej ji absolutní
                    if not image.startswith('http'):
                        image = 'https://atriumzizkov.cz' + image

            # Extrahuj popis
            perex_div = item.find('div', class_='perex')
            perex = perex_div.get_text(strip=True) if perex_div else ''

            if date_str:
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Atrium Žižkov",
                    "category": "hudba",
                    "url": url,
                    "image": image,
                })

        except Exception as e:
            continue

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  FORUM KARLÍN  (forumkarlin.cz)
# ─────────────────────────────────────────────────────────────
def scrape_forum_karlin():
    """Scraper pro Forum Karlín"""
    print("* Forum Karlín...")
    soup = get_soup("https://www.forumkarlin.cz/program/")
    if not soup:
        return []
    
    events = []
    events_divs = soup.find_all('div', class_='event')
    
    for event_div in events_divs:
        try:
            # Nadpis
            h3 = event_div.find('h3')
            title = h3.get_text(strip=True) if h3 else ''
            
            if not title or len(title) < 2:
                continue
            
            # Datum - "12. 4. 2026ne" -> extrahuj só čísla
            date_div = event_div.find('div', class_='date')
            date_text = date_div.get_text(strip=True) if date_div else ''
            
            date_str = ''
            if date_text:
                date_match = re.search(r'(\d{1,2})\.\s+(\d{1,2})\.\s+(\d{4})', date_text)
                if date_match:
                    day = date_match.group(1)
                    month = date_match.group(2)
                    year = date_match.group(3)
                    date_str = f"{day}.{month}.{year}"
            
            # Obrázek - odstraň velikost z URL
            img = event_div.find('img')
            image = ''
            if img:
                img_src = img.get('src', '')
                if img_src:
                    # Nahraď -300x150. na .
                    image = re.sub(r'-\d+x\d+\.', '.', img_src)
            
            # Link
            link = event_div.find('a', href=True)
            url = link.get('href', '') if link else ''
            
            # Čas - zatím není na webu
            time_str = ''
            
            if date_str:
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Forum Karlín",
                    "category": "hudba",
                    "url": url,
                    "image": image,
                })
        
        except Exception as e:
            continue
    
    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  JAZZ DOCK  (jazzdock.cz)
# ─────────────────────────────────────────────────────────────
def scrape_jazz_dock():
    """Scraper pro Jazz Dock"""
    print("* Jazz Dock...")

    events = []
    seen_urls = set()
    today = datetime.now()

    # Procházej aktuální + 8 dalších měsíců
    months_to_fetch = []
    y, m = today.year, today.month
    for _ in range(9):
        months_to_fetch.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    for (year, month) in months_to_fetch:
        page_num = 1
        while True:
            url_page = f"https://www.jazzdock.cz/cs/program/{year}/{month}"
            if page_num > 1:
                url_page += f"?page={page_num}"
            soup = get_soup(url_page)
            if not soup:
                break

            items = soup.find_all('div', class_='program-item')
            if not items:
                break

            for item in items:
                try:
                    h2 = item.find('h2')
                    title = h2.get_text(strip=True) if h2 else ''
                    if not title or len(title) < 2:
                        continue

                    all_text = item.get_text(" ", strip=True)

                    time_str = ''
                    time_match = re.search(r'od\s+(\d{1,2}):(\d{2})', all_text)
                    if time_match:
                        time_str = f"{time_match.group(1)}:{time_match.group(2)}"

                    date_str = ''
                    if "DNES HRAJEME" in all_text:
                        date_str = today.strftime("%d.%m.%Y")
                    else:
                        date_match = re.search(r'(po|út|st|čt|pá|so|ne)\s+(\d{1,2})\.\s+(\d{1,2})\.', all_text)
                        if date_match:
                            date_str = f"{date_match.group(2)}.{date_match.group(3)}.{year}"

                    span = item.find('span', class_='label-gender')
                    category_raw = span.get_text(strip=True) if span else 'hudba'
                    if "theatre" in category_raw.lower() or "divadlo" in category_raw.lower():
                        category = "divadlo"
                    else:
                        category = "hudba"

                    img = item.find('img')
                    image = ''
                    if img:
                        img_src = img.get('src', '')
                        if img_src:
                            image = img_src if img_src.startswith('http') else 'https://www.jazzdock.cz' + img_src

                    link = item.find('a', href=True)
                    url = ''
                    if link:
                        href = link.get('href', '')
                        if href:
                            url = href if href.startswith('http') else 'https://www.jazzdock.cz' + href

                    if not date_str or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    events.append({
                        "title": title,
                        "date": date_str,
                        "time": time_str,
                        "venue": "Jazz Dock",
                        "category": category,
                        "url": url,
                        "image": image,
                    })

                except Exception:
                    continue

            # Pokud je méně než 20 položek, další stránka neexistuje
            if len(items) < 20 or not soup.find(class_='btn-next'):
                break
            page_num += 1

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  ARCHA+  (archa-plus.cz)
# ─────────────────────────────────────────────────────────────
def scrape_archa():
    print("* Archa+...")
    from datetime import date as _date

    today = _date.today()
    events = []
    seen_urls = set()

    # Build list of months to scrape: current month + next 8 months
    months_to_scrape = []
    y, m = today.year, today.month
    for _ in range(9):
        months_to_scrape.append(f"https://archa-plus.cz/cz/program/?dateFrom={y}-{m:02d}-01")
        m += 1
        if m > 12:
            m = 1
            y += 1

    for url in months_to_scrape:
        soup = get_soup(url)
        if not soup:
            continue

        for item in soup.find_all('div', class_='program-item'):
            tags = [t.get_text(strip=True).lower() for t in item.find_all('span', class_='tag')]
            if 'hudba' not in tags:
                continue

            link = item.find('a', href=True)
            if not link:
                continue
            href = link['href']
            if not href.startswith('http'):
                href = 'https://archa-plus.cz' + href

            if href in seen_urls:
                continue
            seen_urls.add(href)

            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', href)
            if not date_match:
                continue
            y2, m2, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
            if _date(y2, m2, d) < today:
                continue
            date_str = f"{d:02d}.{m2:02d}.{y2}"

            date_div = item.find('div', class_='performance-date')
            time_str = ''
            if date_div:
                tm = re.search(r'(\d{2}:\d{2})', date_div.get_text())
                if tm:
                    time_str = tm.group(1)

            title_div = item.find('div', class_='performance-title')
            title = title_div.get_text(strip=True) if title_div else ''
            if not title:
                continue

            img = item.find('img')
            image_url = ''
            if img:
                src = img.get('src', '')
                if src.startswith('/'):
                    src = 'https://archa-plus.cz' + src
                image_url = src

            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "Archa+",
                "category": "hudba",
                "url": href,
                "image": image_url,
            })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  REDUTA JAZZ CLUB  (redutajazzclub.cz)
# ─────────────────────────────────────────────────────────────
def scrape_reduta():
    print("* Reduta Jazz Club...")

    from datetime import date as _date
    today = _date.today()
    events = []
    seen_keys = set()

    api_headers = {**HEADERS, 'Referer': 'https://www.redutajazzclub.cz/program-cs'}

    # API volá web pro každý měsíc zvlášť — procházíme 9 měsíců
    cur_y, cur_m = today.year, today.month
    for _ in range(9):
        try:
            url = f"https://www.redutajazzclub.cz/core/tools/program.php?year={cur_y}&month={cur_m}&langs=cs"
            r = requests.get(url, headers=api_headers, timeout=15)
            r.raise_for_status()
            days = r.json() or []
        except Exception as e:
            print(f"  [WARN] Reduta {cur_y}-{cur_m:02d}: {e}", file=sys.stderr)
            days = []

        for day_data in days:
            if not day_data.get('badge'):
                continue  # den bez akce
            date_raw = day_data.get('date', '')
            body_html = day_data.get('body', '')
            if not date_raw or not body_html:
                continue

            dm = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_raw)
            if not dm:
                continue
            date_str = f"{dm.group(3)}.{dm.group(2)}.{dm.group(1)}"

            soup = BeautifulSoup(body_html, 'html.parser')
            times = [s.get_text(strip=True) for s in soup.find_all('span', class_='tt-time')]
            texts = [s.get_text(strip=True) for s in soup.find_all('span', class_='tt-text')]

            if not texts:
                full_text = soup.get_text(' ', strip=True)
                if full_text:
                    key = (date_str, full_text[:60])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        events.append({
                            "title": full_text[:100],
                            "date": date_str,
                            "time": "",
                            "venue": "Reduta Jazz Club",
                            "category": "hudba",
                            "url": "https://www.redutajazzclub.cz/program-cs",
                            "image": "",
                        })
                continue

            for i, title in enumerate(texts):
                if not title:
                    continue
                time_str = times[i] if i < len(times) else ""
                key = (date_str, title)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Reduta Jazz Club",
                    "category": "hudba",
                    "url": "https://www.redutajazzclub.cz/program-cs",
                    "image": "",
                })

        cur_m += 1
        if cur_m > 12:
            cur_m, cur_y = 1, cur_y + 1

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  MALOSTRANSKÁ BESEDA  (malostranska-beseda.cz)
# ─────────────────────────────────────────────────────────────
def scrape_malostranska():
    print("* Malostranská Beseda...")
    from datetime import date as _date

    today = _date.today()
    events = []
    seen = set()

    soup = get_soup("https://www.malostranska-beseda.cz/club/program?limit=200&do=loadMore")
    if not soup:
        return []

    # Načti také jednotlivé měsíce (loadMore vynechává poslední event v měsíci)
    months_soups = [soup]
    for i in range(12):
        m = (today.month - 1 + i) % 12 + 1
        y = today.year + ((today.month - 1 + i) // 12)
        s = get_soup(f"https://www.malostranska-beseda.cz/club/program?year={y}&month={m}")
        if s:
            months_soups.append(s)

    blocks = []
    for s in months_soups:
        for container in s.select('div.bg-khaki'):
            for child in container.find_all('div', recursive=False):
                if child.find('b') and child.find('h4'):
                    blocks.append(child)

    for block in blocks:
        date_b = block.find('b')
        if not date_b:
            continue
        dm = re.match(r'(\d{1,2})\.\s*(\d{2})\.\s*(\d{4})', date_b.get_text(strip=True))
        if not dm:
            continue
        d, mo, y = dm.groups()
        if _date(int(y), int(mo), int(d)) < today:
            continue
        date_str = f"{int(d):02d}.{int(mo):02d}.{y}"

        time_m = re.search(r'(\d{2}:\d{2})', date_b.parent.get_text())
        time_str = time_m.group(1) if time_m else ''

        h4 = block.find('h4')
        title = h4.get_text(strip=True) if h4 else ''
        if not title:
            continue

        key = (date_str, title)
        if key in seen:
            continue
        seen.add(key)

        btn = block.find('a', class_='btn')
        url = btn['href'] if btn else ''

        img = block.find('img')
        image = ''
        if img:
            mb_src = img.get('src', '')
            # MB vrací pouze miniatury 150x125 (grayscale). Obrázky pocházejí z GoOut CDN.
            # Vzor: /grayscale/8_150x125/HASH.{GOOUT_ID}-800.jpg
            # GoOut CDN: goout.net/i/{prvni_3_cifry}/{GOOUT_ID}-800.jpg
            goout_match = re.search(r'/([^/]+)\.(\d{7,8})-', mb_src)
            if goout_match:
                goout_id = goout_match.group(2)
                image = f'https://goout.net/i/{goout_id[:3]}/{goout_id}-800.jpg'
            else:
                image = mb_src

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Malostranská Beseda",
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  PRAGUE OPEN AIR  (pragueopenair.cz) — Energy Pub + Areál7
# ─────────────────────────────────────────────────────────────
def scrape_pragueopenair():
    print("* Prague Open Air (Energy Pub + Areál7 Holešovice)...")

    soup = get_soup("https://www.pragueopenair.cz/")
    if not soup:
        return []

    venue_map = {
        'energy pub': 'Energy Pub',
        'areál7': 'Areál7 Holešovice',
        'areal7': 'Areál7 Holešovice',
    }

    events = []
    for ev in soup.find_all('div', class_='eventon_list_event'):
        # Venue
        loc = ev.find(itemprop='location')
        if not loc:
            continue
        venue_raw = loc.find(itemprop='name')
        if not venue_raw:
            continue
        venue_raw = venue_raw.get_text(strip=True).lower()
        venue = next((v for k, v in venue_map.items() if k in venue_raw), None)
        if not venue:
            continue

        # Datum a čas ze schema startDate
        start = ev.find('meta', itemprop='startDate')
        if not start:
            continue
        m = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})T(\d{2}:\d{2})', start.get('content', ''))
        if not m:
            continue
        y, mo, d, t = m.groups()
        date_str = f"{int(d):02d}.{int(mo):02d}.{y}"
        time_str = t

        # Titulek
        title_el = ev.find('span', class_='evcal_event_title')
        title = title_el.get_text(strip=True) if title_el else ''
        if not title:
            continue

        # URL
        url_el = ev.find('a', itemprop='url')
        url = url_el['href'] if url_el else ''

        # Obrázek
        img_el = ev.find('meta', itemprop='image')
        image = img_el['content'] if img_el else ''

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": venue,
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  SALA TERRENA / KC KAMPA  (kckampa.cz)
# ─────────────────────────────────────────────────────────────
def scrape_sala_terrena():
    print("* Sala Terrena (KC Kampa)...")

    czech_months = {
        'ledna': '01', 'února': '02', 'března': '03', 'dubna': '04',
        'května': '05', 'června': '06', 'července': '07', 'srpna': '08',
        'září': '09', 'října': '10', 'listopadu': '11', 'prosince': '12',
    }

    ajax_url = "https://www.kckampa.cz/wp-admin/admin-ajax.php"
    ZIVA_HUDBA_ID = "75"

    def parse_articles(soup):
        events = []
        for art in soup.select("article.event"):
            # Název
            h1 = art.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
            if not title:
                continue

            # Datum a čas jsou v <ul><li>
            lis = art.find("ul")
            li_texts = [li.get_text(strip=True) for li in lis.find_all("li")] if lis else []

            date_str = ""
            time_str = ""
            for li in li_texts:
                # Datum: "12. dubna 2026, neděle"
                date_match = re.search(r'(\d{1,2})\.\s+(\w+)\s+(\d{4})', li)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month_name = date_match.group(2).lower()
                    year = date_match.group(3)
                    month = czech_months.get(month_name, "")
                    if month:
                        date_str = f"{int(day)}.{int(month)}.{year}"
                # Čas: "16.00" nebo "19.00"
                time_match = re.search(r'^(\d{1,2})\.(\d{2})$', li)
                if time_match:
                    time_str = f"{time_match.group(1)}:{time_match.group(2)}"

            if not date_str:
                continue

            # URL (Další info odkaz)
            a_tag = art.find("a", class_="btn")
            url = a_tag.get("href", "") if a_tag else "https://www.kckampa.cz/"

            # Obrázek
            img = art.find("img")
            image = img.get("src", "") if img else ""

            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "Sala Terrena",
                "category": "hudba",
                "url": url,
                "image": image,
            })
        return events

    try:
        events = []
        # Filtruj podle "živá hudba" (id=75)
        resp = requests.post(
            ajax_url,
            data={"action": "filter", "id": ZIVA_HUDBA_ID, "place": ""},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        events.extend(parse_articles(soup))

        # Zjisti celkový počet a dočti další stránky
        count_inp = soup.find(id="count")
        total = int(count_inp["value"]) if count_inp else len(events)
        page = 2
        while len(events) < total:
            resp2 = requests.post(
                ajax_url,
                data={"action": "loadmore", "id": ZIVA_HUDBA_ID, "place": "", "paged": page},
                headers=HEADERS,
                timeout=15,
            )
            resp2.raise_for_status()
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            new_events = parse_articles(soup2)
            if not new_events:
                break
            events.extend(new_events)
            page += 1

        print(f"   [OK] {len(events)} akcí")
        return events

    except Exception as e:
        print(f"  [WARN] Chyba Sala Terrena: {e}", file=sys.stderr)
        return []


# ─────────────────────────────────────────────────────────────
#  SPORTOVNÍ HALA FORTUNA  (sportovnihalafortuna.cz)
# ─────────────────────────────────────────────────────────────
def scrape_fortuna():
    print("* Sportovní hala Fortuna...")
    soup = get_soup("https://www.sportovnihalafortuna.cz/kalendar-akci")
    if not soup:
        return []

    base = "https://www.sportovnihalafortuna.cz"
    events = []

    for slide in soup.select("li.splide__slide"):
        title_el = slide.find("h2", class_="splide__headline")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        # Datum: "30/04/2026" → "30.4.2026"
        date_el = slide.find("p", class_="splide__date")
        time_el = slide.find("span", class_="splide__time")
        time_str = time_el.get_text(strip=True) if time_el else ""
        date_text = date_el.get_text(strip=True).replace(time_str, "").strip() if date_el else ""
        date_match = re.match(r"(\d{2})/(\d{2})/(\d{4})", date_text)
        if not date_match:
            continue
        date_str = f"{int(date_match.group(1))}.{int(date_match.group(2))}.{date_match.group(3)}"

        # URL
        a_tag = slide.find("a", class_="splide__button")
        href = a_tag.get("href", "") if a_tag else ""
        url = href if href.startswith("http") else base + href

        # Obrázek
        img = slide.find("img", class_="splide__image")
        src = img.get("src", "") if img else ""
        image = src if src.startswith("http") else base + src

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Sportovní hala Fortuna",
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  PRAGUE CONGRESS CENTRE  (praguecc.cz)
# ─────────────────────────────────────────────────────────────
def scrape_praguecc():
    print("* Prague Congress Centre...")
    soup = get_soup("https://www.praguecc.cz/cs/prehled-akci/kultura")
    if not soup:
        return []

    # Jen akce, kde popis nebo název obsahuje hudební klíčové slovo
    MUSIC_KEYWORDS = ["koncert", "hudebn", "zpěv", "zpěvač", "zpěvák", "tour", "tribute", "symphony", "symfonick"]

    events = []
    base = "https://www.praguecc.cz"

    for card in soup.select("div.blog-item"):
        title_el = card.find("span", class_="h4")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        desc_el = card.find("p")
        desc = desc_el.get_text(strip=True).lower() if desc_el else ""
        combined = (title + " " + desc).lower()

        if not any(kw in combined for kw in MUSIC_KEYWORDS):
            continue

        # Datum: "02. 05. 2026" nebo "16. 04. 2026 - 19. 04. 2026" (vezmi první)
        date_el = card.find("small")
        date_text = date_el.get_text(strip=True) if date_el else ""
        date_match = re.search(r"(\d{1,2})\.\s*(\d{2})\.\s*(\d{4})", date_text)
        if not date_match:
            continue
        date_str = f"{int(date_match.group(1))}.{int(date_match.group(2))}.{date_match.group(3)}"

        # URL — preferuj externí odkaz (vstupenky), jinak první absolutní odkaz v kartě
        url = "https://www.praguecc.cz/cs/prehled-akci/kultura"
        for a in card.find_all("a", href=True):
            href = a.get("href", "")
            if href.startswith("http") and "praguecc.cz" not in href:
                url = href
                break
        if url == "https://www.praguecc.cz/cs/prehled-akci/kultura":
            for a in card.find_all("a", href=True):
                href = a.get("href", "")
                if href.startswith("http"):
                    url = href
                    break

        # Obrázek
        img = card.find("img")
        image = ""
        if img:
            src = img.get("src", "")
            image = src if src.startswith("http") else base + src

        events.append({
            "title": title,
            "date": date_str,
            "time": "",
            "venue": "Prague Congress Centre",
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  O2 ARENA  (o2arena.cz)
# ─────────────────────────────────────────────────────────────
def scrape_o2arena():
    print("* O2 Arena...")
    soup = get_soup("https://www.o2arena.cz/events/")
    if not soup:
        return []

    # Klíčová slova nehudebních akcí
    EXCLUDE_KEYWORDS = [
        "hc sparta", "hc dynamo", "hc ", " hc ",
        "florbal", "nohejbal",
        "prohlídkové okruhy",
        "fmx",
        "global champions",
        "taneční skupina roku",
        "mistrovství světa",
        "reinhold messner",
        "superfinálu",
        "superfinále",
    ]

    events = []
    for ev in soup.select("div.event_preview"):
        h3 = ev.find("h3")
        if not h3:
            continue
        a_tag = h3.find("a")
        title = a_tag.get_text(strip=True) if a_tag else h3.get_text(strip=True)
        if not title:
            continue

        # Filtruj nehudební akce
        title_lower = title.lower()
        if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
            continue

        # Datum a čas: "20.4.2026 20:00" nebo "13.4.2026 18:30"
        time_el = ev.find("p", class_="time")
        time_text = time_el.get_text(strip=True) if time_el else ""
        # Vezmi první výskyt datumu (u vícedenních akcí bývají dva)
        date_match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", time_text)
        time_match = re.search(r"(\d{2}:\d{2})", time_text)
        if not date_match:
            continue
        date_str = date_match.group(1)
        # Normalizuj na "d.m.yyyy"
        parts = date_str.split(".")
        date_str = f"{int(parts[0])}.{int(parts[1])}.{parts[2]}"
        time_str = time_match.group(1) if time_match else ""

        url = a_tag.get("href", "") if a_tag else "https://www.o2arena.cz/events/"

        # Obrázek z background-image stylu
        eye = ev.find("div", class_="eye_catcher")
        image = ""
        if eye:
            style = eye.get("style", "")
            img_match = re.search(r"url\(([^)]+)\)", style)
            if img_match:
                image = img_match.group(1).strip("'\"")

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "O2 Arena",
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  SASAZU CLUB  (sasazu-club.com)
# ─────────────────────────────────────────────────────────────
def scrape_sasazu():
    print("* SaSaZu Club...")
    soup = get_soup("https://www.sasazu-club.com/events")
    if not soup:
        return []

    events = []
    base = "https://www.sasazu-club.com"

    for item in soup.select("a.grid-item"):
        text_el = item.find(class_="portfolio-text")
        text = text_el.get_text(strip=True) if text_el else ""
        if not text:
            continue

        # Formát: "17.4.2026 - Název" nebo "8. 4. 2026 - Název"
        m = re.match(r"(\d{1,2})\.?\s*(\d{1,2})\.?\s*(\d{4})\s*[-–]\s*(.+)", text)
        if not m:
            continue

        date_str = f"{int(m.group(1))}.{int(m.group(2))}.{m.group(3)}"
        title = m.group(4).strip()

        href = item.get("href", "")
        url = href if href.startswith("http") else base + href

        img = item.find("img")
        image = img.get("data-image", "") or img.get("src", "") if img else ""

        events.append({
            "title": title,
            "date": date_str,
            "time": "",
            "venue": "SaSaZu",
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  CARGO GALLERY  (cargogallery.cz)
# ─────────────────────────────────────────────────────────────
def scrape_cargogallery():
    print("* Cargo Gallery...")
    soup = get_soup("https://cargogallery.cz/program/")
    if not soup:
        return []

    events = []
    for ev in soup.select("div.eventon_list_event"):
        # Název
        title_el = ev.find("span", class_="evcal_event_title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        # Datum a čas ze schema.org meta
        start_meta = ev.find("meta", {"itemprop": "startDate"})
        date_str = ""
        time_str = ""
        if start_meta:
            # Formát: "2026-4-17T19:30+2:00"
            start_val = start_meta.get("content", "")
            dt_match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})T(\d{2}:\d{2})", start_val)
            if dt_match:
                date_str = f"{int(dt_match.group(3))}.{int(dt_match.group(2))}.{dt_match.group(1)}"
                time_str = dt_match.group(4)

        if not date_str:
            continue

        # URL
        a_tag = ev.find("a", class_="evcal_list_a")
        url = a_tag.get("href", "") if a_tag else "https://cargogallery.cz/program/"

        # Obrázek
        img_el = ev.find("span", class_="ev_ftImg")
        image = img_el.get("data-thumb", "") if img_el else ""
        if not image and img_el:
            image = img_el.get("data-img", "")

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Cargo Gallery",
            "category": "hudba",
            "url": url,
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  MUSIC CLUB JIŽÁK  (musicclubjizak.cz)
# ─────────────────────────────────────────────────────────────
def scrape_musicclubjizak():
    print("* Music Club Jižák...")
    soup = get_soup("https://www.musicclubjizak.cz/program/")
    if not soup:
        return []

    events = []
    posts = soup.select("div.oxy-post")

    for post in posts:
        title_el = post.find(class_="koncert-vystupujici")
        title = title_el.get_text(strip=True) if title_el else ""

        # Přeskoč "připravujeme" položky
        if not title or "připravujeme" in title.lower():
            continue

        # Datum: "02. 05. 2026" → "2.5.2026"
        date_el = post.find(class_="koncert-date")
        date_text = date_el.get_text(strip=True) if date_el else ""
        date_match = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", date_text)
        if not date_match:
            continue
        date_str = f"{int(date_match.group(1))}.{int(date_match.group(2))}.{date_match.group(3)}"

        # Čas
        time_el = post.find(class_="koncert-zacatek")
        time_str = time_el.get_text(strip=True) if time_el else ""

        # URL
        a_tag = post.find("a")
        url = a_tag.get("href", "").strip() if a_tag else ""
        if not url:
            url = "https://www.musicclubjizak.cz/program/"

        events.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Music Club Jižák",
            "category": "hudba",
            "url": url,
            "image": "",
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  FUCHS2  (fuchs2.cz/shows)  — Wix, vyžaduje Playwright
# ─────────────────────────────────────────────────────────────
def scrape_fuchs2():
    print("* Fuchs2...")

    if not HAS_PLAYWRIGHT:
        print("  [WARN] Playwright není nainstalován. Spusť: pip install playwright && playwright install chromium", file=sys.stderr)
        return []

    events = []

    eng_months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    def parse_wix_date(text):
        """Převede 'Wed 15 Apr' na 'DD.MM.YYYY' (rok = aktuální nebo příští)."""
        # Formát: "DayName D Mon" nebo "DayName DD Mon"
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})", text)
        if not m:
            return ""
        day = int(m.group(1))
        month_num = eng_months.get(m.group(2).lower())
        if not month_num:
            return ""
        today = datetime.now()
        year = today.year
        # Pokud datum (den+měsíc) v tomto roce již minulo, patří do příštího roku
        try:
            event_date = datetime(year, int(month_num), day)
            if event_date.date() < today.date():
                year += 1
        except ValueError:
            pass
        return f"{day}.{int(month_num)}.{year}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto("https://www.fuchs2.cz/shows", wait_until="load", timeout=45000)
            page.wait_for_timeout(4000)  # počkej na JS rendering karet
            # Klikej na "Load More" dokud existuje
            for _ in range(20):
                load_more = page.locator("button:has-text('Load More')")
                if load_more.count() == 0 or not load_more.first.is_visible():
                    break
                load_more.first.click()
                page.wait_for_timeout(2000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-hook='events-card']")

        for card in cards:
            title_el = card.select_one("[data-hook='title']")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            date_el = card.select_one("[data-hook='short-date']")
            date_str = parse_wix_date(date_el.get_text(strip=True)) if date_el else ""

            # URL — hledej v data-hook nebo první <a>
            link_el = card.select_one("[data-hook='item-link-wrapper']") or card.find("a")
            href = link_el.get("href", "") if link_el else ""
            if href and not href.startswith("http"):
                href = "https://www.fuchs2.cz" + href

            # Obrázek — z Wix URL odstraň blur a thumbnail parametry
            img = card.find("img")
            image_url = img.get("src", "") if img else ""
            if image_url and "wixstatic.com/media/" in image_url:
                # Extrahuj čistý název souboru a sestav URL bez transformací
                m = re.search(r"wixstatic\.com/media/([^/]+)", image_url)
                if m:
                    image_url = f"https://static.wixstatic.com/media/{m.group(1)}"

            events.append({
                "title": title,
                "date": date_str,
                "time": "",
                "venue": "Fuchs2",
                "category": "hudba",
                "url": href or "https://www.fuchs2.cz/shows",
                "image": image_url,
            })

    except Exception as e:
        print(f"  [WARN] Fuchs2: {e}", file=sys.stderr)

    print(f"   [OK] {len(events)} akcí")
    return events


def scrape_bikejesus():
    print("* Bike Jesus...")
    events = []

    def fetch_og_image(url):
        """Stáhne og:image ze statické stránky (GoOut, RA)."""
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            tag = soup.find("meta", property="og:image")
            return tag.get("content", "") if tag else ""
        except Exception:
            return ""

    def fetch_fb_image(url, pw_browser):
        """Stáhne og:image z FB eventu přes Playwright (FB blokuje requests)."""
        try:
            page = pw_browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1500)
            soup = BeautifulSoup(page.content(), "html.parser")
            page.close()
            tag = soup.find("meta", property="og:image")
            return tag.get("content", "") if tag else ""
        except Exception:
            return ""

    try:
        r = requests.get("https://bikejesus.com/events", headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        today = datetime.now().date()

        # Zjisti, které eventy budou potřebovat Playwright (FB-only bez GoOut/RA)
        raw_events = []
        needs_playwright = False
        for item in data:
            date_raw = item.get("Date", "")
            try:
                d = datetime.strptime(date_raw, "%Y-%m-%d").date()
                if d < today:
                    continue
                date_str = f"{d.day}.{d.month}.{d.year}"
            except (ValueError, TypeError):
                continue
            title = item.get("Title", "").strip()
            if not title:
                continue
            tickets = item.get("Tickets") or ""
            link = item.get("Link") or ""
            is_fb_only = bool(link and ("facebook.com" in link or "fb.me" in link)
                              and not ("goout.net" in tickets or "ra.co" in tickets))
            if is_fb_only:
                needs_playwright = True
            raw_events.append((item, date_str, title, tickets, link, is_fb_only))

        # Spusť Playwright jednou pro všechny FB eventy
        fb_images = {}
        if needs_playwright and HAS_PLAYWRIGHT:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    for item, date_str, title, tickets, link, is_fb_only in raw_events:
                        if is_fb_only and link:
                            fb_images[link] = fetch_fb_image(link, browser)
                    browser.close()
            except Exception as e:
                print(f"  [WARN] Bike Jesus Playwright: {e}", file=sys.stderr)

        for item, date_str, title, tickets, link, is_fb_only in raw_events:
            # URL: preferuj tickets (GoOut/RA), jinak FB link
            if tickets and any(d in tickets for d in ("goout.net", "ra.co")):
                url = tickets
            elif link:
                url = link
            else:
                url = tickets or "https://bikejesus.com/#program"

            # Obrázek: GoOut/RA staticky, FB přes Playwright
            image = ""
            if tickets and ("goout.net" in tickets or "ra.co" in tickets):
                image = fetch_og_image(tickets)
            elif is_fb_only and link:
                image = fb_images.get(link, "")

            genre = extract_genre_from_text(title)

            events.append({
                "title": title,
                "date": date_str,
                "time": "",
                "venue": "Bike Jesus",
                "category": "hudba",
                "url": url,
                "image": image,
                "genre": genre,
            })
    except Exception as e:
        print(f"  [WARN] Bike Jesus: {e}", file=sys.stderr)
    print(f"   [OK] {len(events)} akcí")
    return events


def _load_cached_modravopice():
    """Načte existující Modrá Vopice akce z concerts.json jako slovník url -> event."""
    cache = {}
    try:
        with open("concerts.json", encoding="utf-8") as f:
            data = json.load(f)
        for e in data.get("events", []):
            if e.get("venue") == "Modrá Vopice" and e.get("url"):
                cache[e["url"]] = e
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return cache


def scrape_modravopice():
    from concurrent.futures import ThreadPoolExecutor, as_completed

    print("* Modrá Vopice...")
    today = datetime.now().date()
    seen = set()
    events = []

    existing = _load_cached_modravopice()

    def fetch_event_page(link):
        try:
            resp = requests.get(link, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                try:
                    ld = json.loads(script.string)
                except (json.JSONDecodeError, ValueError):
                    continue
                if "startDate" not in ld:
                    continue
                return ld
        except Exception:
            pass
        return None

    def make_event(ld, link):
        title = ld.get("name", "").strip()
        if not title:
            return None
        start = ld.get("startDate", "")
        date_str = ""
        time_str = ""
        if start:
            m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})T(\d{2}:\d{2})", start)
            if m:
                y, mo, d, t = m.group(1), m.group(2), m.group(3), m.group(4)
                date_str = f"{int(d)}.{int(mo)}.{y}"
                time_str = t
        if date_str:
            try:
                parts = date_str.split(".")
                ev_date = datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
                if ev_date < today:
                    return None
            except (ValueError, IndexError):
                pass
        image = ld.get("image", "")
        if isinstance(image, dict):
            image = image.get("url", "")
        url = ld.get("url", link)
        desc_html = ld.get("description", "")
        desc_text = BeautifulSoup(desc_html, "html.parser").get_text(" ") if desc_html else ""
        genres_in_parens = re.findall(r"\(([^)]{3,60})\)", desc_text)
        genre_text = " ".join(genres_in_parens)
        genre = extract_genre_from_text(genre_text or title)
        return {
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Modrá Vopice",
            "category": "hudba",
            "url": url,
            "image": image,
            "genre": genre,
        }

    try:
        # Get all event links via WP REST API (paginated)
        all_links = []
        page = 1
        while True:
            resp = requests.get(
                "https://www.modravopice.cz/wp-json/wp/v2/ajde_events",
                params={"per_page": 100, "page": page, "_fields": "link"},
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code == 400:
                break
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            all_links.extend(ev["link"] for ev in batch)
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            if page >= total_pages:
                break
            page += 1

        new_links = [l for l in all_links if l not in existing]
        print(f"  Celkem {len(all_links)} záznamů, z toho {len(new_links)} nových (stahuju detaily)...")

        # Reuse cached future events
        for link, ev in existing.items():
            if link not in all_links:
                continue  # zmizelo z webu
            if not ev.get("date"):
                continue
            try:
                parts = ev["date"].split(".")
                ev_date = datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
                if ev_date < today:
                    continue
            except (ValueError, IndexError):
                pass
            key = (ev.get("title", "").lower(), ev.get("date", ""))
            if key not in seen:
                seen.add(key)
                events.append(ev)

        # Fetch only new event pages in parallel
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = {ex.submit(fetch_event_page, link): link for link in new_links}
            for fut in as_completed(futures):
                link = futures[fut]
                ld = fut.result()
                if not ld:
                    continue
                ev = make_event(ld, link)
                if not ev:
                    continue
                key = (ev["title"].lower(), ev["date"])
                if key not in seen:
                    seen.add(key)
                    events.append(ev)

    except Exception as e:
        print(f"  [WARN] Modrá Vopice: {e}", file=sys.stderr)

    events.sort(key=lambda x: (
        [int(p) for p in reversed(x["date"].split("."))] if x["date"] else [0, 0, 0]
    ))
    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  KLUB VARŠAVA  (klubvarsava.cz)
# ─────────────────────────────────────────────────────────────
def scrape_varsava():
    print("* Klub Varšava...")
    events = []
    today = datetime.now().date()

    try:
        r = requests.get("https://www.klubvarsava.cz/", headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string or '"Event"' not in script.string:
                continue
            try:
                ld = json.loads(script.string)
            except (json.JSONDecodeError, ValueError):
                continue
            if ld.get("@type") != "Event":
                continue

            title = ld.get("name", "").strip()
            if not title:
                continue
            if "kvíz" in title.lower() or "kviz" in title.lower():
                continue

            start = ld.get("startDate", "")
            date_text = ""
            time_text = ""
            if start:
                try:
                    # Format: 2026-4-20T18:15+2:00
                    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})T(\d{2}:\d{2})", start)
                    if m:
                        y, mo, d, t = m.group(1), m.group(2), m.group(3), m.group(4)
                        ev_date = datetime(int(y), int(mo), int(d)).date()
                        if ev_date < today:
                            continue
                        date_text = f"{int(d)}.{int(mo)}.{y}"
                        time_text = t
                except Exception:
                    pass

            events.append({
                "title": title,
                "date": date_text,
                "time": time_text,
                "venue": "Klub Varšava",
                "category": "hudba",
                "url": ld.get("url", "https://www.klubvarsava.cz/"),
                "image": ld.get("image", ""),
            })

    except Exception as e:
        print(f"  [WARN] Klub Varšava: {e}", file=sys.stderr)

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  SUBZERO  (goout.net/cs/subzero/vzraeg/events/)
# ─────────────────────────────────────────────────────────────
def scrape_subzero():
    """GoOut entities API s venueId=96267 (Subzero Praha)"""
    print("* Subzero...")
    events = []
    today = datetime.now().date()

    try:
        r = requests.get(
            "https://goout.net/services/entities/v1/schedules",
            params={
                "languages[]": "cs",
                "venueIds[]": "96267",
                "grouped": "true",
                "limit": "50",
                "include": "events,images,venues,cities,sales,performers,parents",
            },
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        included = data.get("included", {})
        events_map = {e["id"]: e for e in included.get("events", [])}
        images_map = {i["id"]: i for i in included.get("images", [])}

        for sched in data.get("schedules", []):
            attrs = sched.get("attributes", {})
            start = attrs.get("startAt", "")
            date_text = ""
            time_text = ""
            if start:
                try:
                    dt = datetime.fromisoformat(start)
                    if dt.date() < today:
                        continue
                    date_text = f"{dt.day}.{dt.month}.{dt.year}"
                    time_text = dt.strftime("%H:%M")
                except Exception:
                    pass

            # Název z included event
            event_id = (sched.get("relationships", {}).get("event") or {}).get("id")
            evt = events_map.get(event_id, {})
            title = (evt.get("locales", {}).get("cs", {}).get("name") or "").strip()
            if not title:
                continue

            # URL akce
            url = sched.get("locales", {}).get("cs", {}).get("siteUrl") or sched.get("url", "")

            # Obrázek: první image napojená na event
            image = ""
            img_refs = evt.get("relationships", {}).get("images", [])
            if img_refs:
                img = images_map.get(img_refs[0]["id"], {})
                image = img.get("attributes", {}).get("url", "")

            events.append({
                "title": title,
                "date": date_text,
                "time": time_text,
                "venue": "Subzero",
                "category": "hudba",
                "url": url,
                "image": image,
            })

    except Exception as e:
        print(f"  [WARN] Subzero: {e}", file=sys.stderr)

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  KC ZAHRADA + CHODOVSKÁ TVRZ  (kczahrada.cz)
# ─────────────────────────────────────────────────────────────
def scrape_kczahrada():
    print("* KC Zahrada / Chodovská tvrz...")
    events = []
    page = 1

    while True:
        url = "https://kczahrada.cz/program/rubrika/koncert/"
        if page > 1:
            url += f"?tribe_paged={page}"
        soup = get_soup(url)
        if not soup:
            break

        content = soup.find(id="tribe-events-content")
        if not content:
            break

        items = content.find_all("div", class_="tribe-events-border")
        if not items:
            break

        for ev in items:
            title_el = ev.find("b")
            link_el = ev.find("a")
            title = title_el.get_text(strip=True) if title_el else (link_el.get_text(strip=True) if link_el else "")
            if not title:
                continue

            href = link_el.get("href", "") if link_el else ""

            img_el = ev.find("img")
            image = img_el.get("src", "") if img_el else ""
            # WordPress thumbnail suffix -177x142 → plný rozměr
            image = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", image)

            # Druhý a třetí col-1 obsahují datum a čas
            col1s = ev.find_all("div", class_="col-1")
            date_raw = col1s[1].get_text(strip=True) if len(col1s) > 1 else ""
            time_str = col1s[2].get_text(strip=True) if len(col1s) > 2 else ""

            # Normalizuj datum "23.04.2026" → "23.4.2026"
            date_str = ""
            dm = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_raw)
            if dm:
                date_str = f"{int(dm.group(1))}.{int(dm.group(2))}.{dm.group(3)}"

            if not date_str:
                continue

            badges = [b.get_text(strip=True) for b in ev.find_all("span", class_="badge")]
            badges_lower = [b.lower() for b in badges]

            if any("chodovsk" in b for b in badges_lower):
                venue = "Chodovská tvrz"
            else:
                venue = "KC Zahrada"

            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": venue,
                "category": "hudba",
                "url": href,
                "image": image,
            })

        # Zkontroluj, zda existuje další stránka
        next_li = content.find("li", class_="tribe-events-nav-next")
        if not next_li or not next_li.find("a"):
            break
        page += 1

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  ČÍTÁRNA UNIJAZZ  (citarna.unijazz.cz)
# ─────────────────────────────────────────────────────────────
def scrape_citarna():
    print("* Čítárna Unijazz...")
    import time as _time

    ajax_url = "https://citarna.unijazz.cz/wp-admin/admin-ajax.php"
    ajax_headers = {
        **HEADERS,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://citarna.unijazz.cz/",
    }

    home_soup = get_soup("https://citarna.unijazz.cz/program/")
    if not home_soup:
        return []

    atts_m = re.search(r'atts:\s*"([^"]+)"', str(home_soup))
    if not atts_m:
        print("  [WARN] Čítárna: MEC atts nenalezeny", file=sys.stderr)
        return []
    atts = atts_m.group(1)

    def extract_concerts(soup):
        items = []
        for art in soup.find_all("article", class_="item"):
            header = art.find("div", class_="itemHeader")
            if not header or not header.get_text(strip=True).lower().startswith("koncert"):
                continue
            title_el = art.find("h2", class_="title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or title == "+Program+":
                continue
            link_el = art.find("a", class_="item__link") or art.find("a", href=True)
            url = link_el.get("href", "") if link_el else ""
            if url:
                items.append({"title": title, "url": url})
        return items

    def next_month_from_nav(soup):
        nav = soup.find(class_="mec-next-month")
        if not nav:
            return None
        y, m = nav.get("data-mec-year"), nav.get("data-mec-month")
        return (int(y), int(m)) if y and m else None

    seen_urls = set()
    concert_items = []
    current_soup = home_soup

    while True:
        for item in extract_concerts(current_soup):
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                concert_items.append(item)

        next_ym = next_month_from_nav(current_soup)
        if not next_ym:
            break
        y, m = next_ym
        try:
            post_data = f"action=mec_tile_load_month&mec_year={y}&mec_month={m:02d}&{atts}&apply_sf_date=1"
            resp = requests.post(ajax_url, data=post_data, headers=ajax_headers, timeout=15)
            resp.raise_for_status()
            month_html = resp.json().get("month", "")
            if not month_html:
                break
            current_soup = BeautifulSoup(month_html, "html.parser")
        except Exception as e:
            print(f"  [WARN] Čítárna AJAX {y}-{m:02d}: {e}", file=sys.stderr)
            break

    events = []
    for item in concert_items:
        _time.sleep(0.3)
        detail = get_soup(item["url"])
        if not detail:
            continue

        date_str, time_str = "", ""
        time_el = detail.find("div", class_="event-time")
        if time_el:
            raw = time_el.get_text(strip=True)
            dm = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s+(\d{2}:\d{2})", raw)
            if dm:
                d, mo, y, t = dm.groups()
                date_str = f"{int(d)}.{int(mo)}.{y}"
                time_str = t

        if not date_str:
            continue

        image = ""
        for div in detail.find_all("div", class_="ct-div-block"):
            bg = re.search(r"background-image:\s*url\(([^)]+)\)", div.get("style", ""))
            if bg:
                image = bg.group(1).strip("'\"")
                break
        if not image:
            og = detail.find("meta", property="og:image")
            if og:
                image = og.get("content", "")

        events.append({
            "title": item["title"],
            "date": date_str,
            "time": time_str,
            "venue": "Čítárna Unijazz",
            "category": "hudba",
            "url": item["url"],
            "image": image,
        })

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  KLUBOVNA POVALEC  (klubovna.povalec.cz)
# ─────────────────────────────────────────────────────────────
def scrape_klubovnapovalec():
    print("* Klubovna Povalec...")
    BASE = "https://www.klubovna.povalec.cz"
    MUSIC_CATS = {"koncert", "djs"}
    events = []
    seen_urls = set()

    def get_max_page(soup):
        """Zjistí počet stránek z paginačních tlačítek."""
        buttons = soup.find_all("button", attrs={"data-path": re.compile(r"/ajax/filter/program/\d+")})
        nums = []
        for btn in buttons:
            m = re.search(r"/program/(\d+)$", btn.get("data-path", ""))
            if m:
                nums.append(int(m.group(1)))
        return max(nums) if nums else 1

    def parse_page(soup):
        """Vrátí seznam akcí z jedné stránky listingu."""
        page_events = []
        for row in soup.find_all("tr"):
            day_cell = row.find("td", class_="day-cell")
            content_cell = row.find("td", class_="content-cell")
            cat_cell = row.find("td", class_="category-cell")
            if not (day_cell and content_cell and cat_cell):
                continue

            # Kategorie
            cat_span = cat_cell.find("span")
            category_raw = cat_span.get_text(strip=True).lower() if cat_span else ""
            if category_raw not in MUSIC_CATS:
                continue

            # URL a datum z odkazu obrázku
            img_link = day_cell.find("a", href=re.compile(r"^/\d+/program/"))
            if not img_link:
                continue
            href = img_link["href"]
            full_url = BASE + href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            dm = re.search(r"-(\d{2})-(\d{2})-(\d{4})-(\d{2})-(\d{2})$", href)
            if not dm:
                continue
            day, month, year, hh, mm = dm.groups()
            date_str = f"{int(day)}.{int(month)}.{year}"
            time_str = f"{hh}:{mm}"

            # Obrázek
            img_el = img_link.find("img")
            image = ""
            if img_el:
                src = img_el.get("src", "")
                image = src if src.startswith("http") else BASE + src

            # Název — odkaz s class no-decoration v content-cell
            title_link = content_cell.find("a", class_="no-decoration")
            if not title_link:
                continue
            title = title_link.get_text(strip=True)
            if not title:
                continue

            page_events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "Klubovna Povaleč",
                "category": "hudba",
                "url": full_url,
                "image": image,
            })
        return page_events

    # Stránka 1
    soup1 = get_soup(BASE + "/program")
    if not soup1:
        print(f"   [OK] {len(events)} akcí")
        return events

    events.extend(parse_page(soup1))
    max_page = get_max_page(soup1)

    # Další stránky
    for page in range(2, max_page + 1):
        soup = get_soup(f"{BASE}/program/{page}")
        if not soup:
            break
        events.extend(parse_page(soup))

    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  SALMOVSKÁ LITERÁRNÍ KAVÁRNA
# ─────────────────────────────────────────────────────────────
def scrape_salmovska():
    print("* Salmovská literární kavárna...")
    try:
        import pdfplumber
        import io as _io
    except ImportError:
        print("   [SKIP] pdfplumber není nainstalován (pip install pdfplumber)")
        return []

    if not HAS_PLAYWRIGHT:
        print("   [SKIP] playwright není k dispozici")
        return []

    BASE = "https://www.salmovska.cz"
    VENUE = "Salmovská literární kavárna"

    MONTH_SLUGS = [
        "leden", "unor", "brezen", "duben", "kveten", "cerven",
        "cervenec", "srpen", "zari", "rijen", "listopad", "prosinec",
    ]

    DATE_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.')
    TIME_RE = re.compile(r'(\d{1,2}):(\d{2})')
    MONTH_YEAR_RE = re.compile(r'(?:DUBEN|KV.TEN|LEDEN|.NOR|B.EZEN|.ERVEN.?|SRPEN|Z...[IÍ]|..JEN|LISTOPAD|PROSINEC)\s+(\d{4})', re.IGNORECASE)
    # Separator between title and description in the text cell
    TITLE_SEP = re.compile(
        r'\s*[-−–]\s+'                   # ASCII or Unicode dash with spaces
        r'|\.\.\s*'                       # double dot
        r'|,\s*(?=[a-z])'                 # comma before lowercase
        r'|\s+[^\x20-\x7e]\s+'           # single garbled char surrounded by spaces (em-dash)
        r'|\s+[^\x20-\x7e](?=[a-z]{2})'  # garbled char followed by 2+ lowercase ASCII (garbled lc word)
        r'|\s+(?=[a-z]{2})'              # space before 2+ lowercase ASCII chars
    )

    def _extract_title(text):
        """Extract performer title from first line of event cell."""
        first_line = text.split('\n')[0].strip()
        m = TITLE_SEP.search(first_line)
        title = first_line[:m.start()].strip() if m else first_line
        # Strip trailing noise: lone non-ASCII chars, noise keywords
        title = re.sub(r'\s*(VYPROD.NO|DOPORU.UJEME)\s*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'[\x80-\xff]+$', '', title).strip()  # trailing garbled char(s)
        return title[:100] if title else ""

    def _parse_pdf(pdf_bytes, fallback_year):
        events = []
        try:
            with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
                year = fallback_year

                # Try to get year from first page text
                first_text = pdf.pages[0].extract_text() or ""
                my = MONTH_YEAR_RE.search(first_text)
                if my:
                    year = int(my.group(1))

                for pg in pdf.pages:
                    for table in pg.extract_tables():
                        for row in table:
                            if not row or len(row) < 3:
                                continue
                            col_date, col_time, col_desc = row[0] or "", row[1] or "", row[2] or ""

                            # Skip rows without a recognisable date
                            dm = DATE_RE.search(col_date)
                            if not dm:
                                continue

                            day_n, mon_n = int(dm.group(1)), int(dm.group(2))
                            date_str = f"{day_n}.{mon_n}.{year}"

                            # Time from col_time or fallback
                            tm = TIME_RE.search(col_time)
                            time_str = f"{tm.group(1)}:{tm.group(2)}" if tm else "19:00"

                            title = _extract_title(col_desc)
                            if not title:
                                continue

                            genre = extract_genre_from_text(col_desc)

                            events.append({
                                "title": title,
                                "date": date_str,
                                "time": time_str,
                                "venue": VENUE,
                                "category": "hudba",
                                "url": BASE,
                                "image": "",
                                "genre": genre,
                            })

        except Exception as e:
            print(f"   [WARN] Chyba při parsování PDF: {e}", file=sys.stderr)
        return events

    events = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Visit main page to establish session/cookies
            page.goto(BASE + "/", timeout=15000)

            # Find all program pages to scrape (current + next month)
            now = datetime.now()

            months_to_try = []
            cur_slug = MONTH_SLUGS[now.month - 1]
            months_to_try.append((cur_slug, now.year))
            # Next month
            if now.month < 12:
                months_to_try.append((MONTH_SLUGS[now.month], now.year))
            else:
                months_to_try.append((MONTH_SLUGS[0], now.year + 1))

            for slug, yr in months_to_try:
                yr_short = str(yr)[2:]
                pdf_url = f"{BASE}/programy/{yr_short}/{slug}_{yr}.pdf"
                try:
                    resp = page.request.get(pdf_url, timeout=15000)
                    if resp.status == 200:
                        pdf_bytes = resp.body()
                        parsed = _parse_pdf(pdf_bytes, yr)
                        events.extend(parsed)
                        print(f"   {slug} {yr}: {len(parsed)} akcí")
                    else:
                        print(f"   [WARN] PDF nedostupné ({resp.status}): {pdf_url}")
                except Exception as e:
                    print(f"   [WARN] {slug}: {e}", file=sys.stderr)

            browser.close()
    except Exception as e:
        print(f"   [ERROR] {e}", file=sys.stderr)

    print(f"   [OK] {len(events)} akcí celkem")
    return events


# ─────────────────────────────────────────────────────────────
#  HLAVNÍ FUNKCE
# ─────────────────────────────────────────────────────────────
def main():
    print("\n* Praha Koncerty - Scraper")
    print("=" * 40)
    print(f"Spuštěno: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")

    # Načti cache žánrů z předchozího běhu (inkrementální scraping)
    print("* Načítám cache žánrů z concerts.json...")
    genre_url_cache, genre_key_cache = load_existing_genres()
    print(f"  Cache: {len(genre_url_cache)} URL, {len(genre_key_cache)} klíčů\n")

    all_events = []

    scrapers = [
        scrape_rockcafe,
        scrape_musicbar,
        scrape_futurum,
        scrape_klub007,
        scrape_citarna,
        scrape_crossclub,
        scrape_akropolis,
        scrape_vagon,
        scrape_cafevlese,
        scrape_kastan,
        scrape_meetfactory,
        scrape_goout,
        scrape_roxy,
        scrape_atriumzizkov,
        scrape_forum_karlin,
        scrape_jazz_dock,
        scrape_reduta,
        scrape_archa,
        scrape_pragueopenair,
        scrape_malostranska,
        scrape_sala_terrena,
        scrape_fortuna,
        scrape_praguecc,
        scrape_o2arena,
        scrape_cargogallery,
        scrape_sasazu,
        scrape_musicclubjizak,
        scrape_fuchs2,
        scrape_bikejesus,
        scrape_modravopice,
        scrape_subzero,
        scrape_varsava,
        scrape_kczahrada,
        scrape_citarna,
        scrape_klubovnapovalec,
        scrape_salmovska,
    ]

    for scraper in scrapers:
        try:
            events = scraper()
            all_events.extend(events)
        except Exception as e:
            print(f"  [ERROR] Neočekávaná chyba: {e}", file=sys.stderr)

    print(f"\nPřed deduplikací: {len(all_events)} akcí")
    
    # Počítáme Atrium eventy
    atrium_count = sum(1 for e in all_events if e.get("venue") == "Atrium Žižkov")
    if atrium_count > 0:
        print(f"  - Z toho Atrium Žižkov: {atrium_count} akcí")
        for e in all_events:
            if e.get("venue") == "Atrium Žižkov":
                print(f"    * {e['title']} ({e['date']}) - kategorie: {e.get('category', 'N/A')}")

    # Deduplikace podle názvu + data
    seen = set()
    unique_events = []
    for e in all_events:
        key = (e["title"].lower().strip(), e["date"])
        if key not in seen:
            seen.add(key)
            unique_events.append(e)
        else:
            # Debug: pokud je to Atrium, řekni si, že byla duplikace
            if e.get("venue") == "Atrium Žižkov":
                print(f"  [DUP] Odstraněn duplikát: {e['title']} ({e['date']})")
    
    print(f"Po deduplikaci: {len(unique_events)} akcí")

    # Seřadíme podle data
    def sort_key(e):
        try:
            parts = e["date"].replace(" ", "").split(".")
            if len(parts) >= 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            pass
        return datetime(9999, 1, 1)

    unique_events.sort(key=sort_key)

    # Počítáme Atrium eventy před filtrováním
    atrium_after_dedup = sum(1 for e in unique_events if e.get("venue") == "Atrium Žižkov")
    print(f"Před filtrováním divadel: Atrium = {atrium_after_dedup}")

    # Filtrujeme nehudební kategorie (divadlo, galerie, rezidence)
    unique_events = [e for e in unique_events if e.get("category", "").lower() not in ("divadlo", "galerie", "rezidence")]
    
    # Počítáme Atrium eventy po filtrování
    atrium_after_filter = sum(1 for e in unique_events if e.get("venue") == "Atrium Žižkov")
    print(f"Po filtrování divadel: Atrium = {atrium_after_filter}")

    # ── Inkrementální doplňování žánrů ──────────────────────────
    print("\n* Doplňuji žánry...")
    genre_fetched = 0
    genre_from_cache = 0
    genre_from_scraper = 0
    genre_missing = 0

    for event in unique_events:
        # 1) Žánr už má ze scraperu (Klub 007, Kaštan) — zachovat
        if event.get("genre"):
            genre_from_scraper += 1
            continue

        url = event.get("url", "")
        key = (event.get("title", "").lower().strip(), event.get("date", ""), event.get("venue", ""))

        # 2) Žánr v cache z minulého běhu (podle URL nebo klíče)
        cached = genre_url_cache.get(url) or genre_key_cache.get(key)
        if cached:
            event["genre"] = cached
            genre_from_cache += 1
            continue

        # 3) Žánr není k dispozici (Vagon) — přeskočit
        if url in _GENRE_SKIP_URLS or not url:
            event["genre"] = ""
            genre_missing += 1
            continue

        # 4) Nová akce — stáhnout detail stránku
        genre = fetch_genre_from_detail(url)
        event["genre"] = genre
        if genre:
            genre_fetched += 1
        else:
            genre_missing += 1

    print(f"  Ze scraperu (listing): {genre_from_scraper}")
    print(f"  Z cache (předchozí běh): {genre_from_cache}")
    print(f"  Nově staženo: {genre_fetched}")
    print(f"  Nedostupné: {genre_missing}")

    # Ukládáme do JSON
    output = {
        "updated": datetime.now().isoformat(),
        "count": len(unique_events),
        "events": unique_events,
    }

    with open("concerts.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Hotovo! Uloženo {len(unique_events)} akcí do concerts.json")
    print(f"   Soubor: concerts.json")


if __name__ == "__main__":
    main()

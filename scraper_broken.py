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
    
    # Czech month mapping
    czech_months = {
        'leden': '01', 'února': '02', 'březen': '03', 'duben': '04',
        'květen': '05', 'červen': '06', 'červenec': '07', 'srpen': '08',
        'září': '09', 'říjen': '10', 'listopadu': '11', 'prosinec': '12'
    }
    
    # Každá akce je v elementu s třídou .event
    event_divs = soup.select('.event')
    
    for event_div in event_divs:
        # Získej event ID
        event_id = event_div.get('data-event_id', '')
        
        # Získej URL z prvního <a> tagu
        link = event_div.find('a', href=True)
        url = link.get('href', '') if link else ''
        
        # Získej obrázek z meta tagu v schématu
        img_meta = event_div.find('meta', {'itemprop': 'image'})
        image = img_meta.get('content', '') if img_meta else ''
        
        # Získej den z <em class="date">
        date_elem = event_div.find('em', class_='date')
        day = date_elem.get_text(strip=True) if date_elem else ''
        
        # Získej celý text na analýzu
        text = event_div.get_text(' ', strip=True)
        
        # Extrahuj měsíc - najdi české jméno měsíce
        month_match = re.search(r'(leden|února|březen|duben|květen|červen|červenec|srpen|září|říjen|listopadu|prosinec)', text, re.I)
        month_val = ''
        if month_match:
            month_name = month_match.group(1).lower()
            month_val = czech_months.get(month_name, '')
        
        # Extrahuj čas (první výskyt HH:MM)
        time_match = re.search(r'(\d{2}):(\d{2})', text)
        time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ''
        
        # Extrahuj titul - text mezi "HH:MM HH:MM " a " Detail akce"
        title = ""
        title_match = re.search(r'\d{2}:\d{2}\s+\d{2}:\d{2}\s+(.+?)\s+Detail akce', text)
        if title_match:
            title = title_match.group(1)
            
            # Odstraň kódy zemí: (de), (cz), (fi/gr), (uk/us), atd.
            title = re.sub(r'\s*\([a-z]{2}(?:/[a-z]{2})*\)\s*', ' ', title, flags=re.I)
            
            # Odstraň žánry - slova jako "Metal", "Rock", "/", atd. včetně těch bez mezery předtím
            # Pattern: matchuje genre klíčová slova bez/se mezerou a všechno za ním
            genre_pattern = r'(?:\s|(?<=[A-Z]))+(metal|rock|punk|indie|pop|jazz|electronic|sludge|stoner|doom|grind|hardcore|folk|blues|reggae|rap|hip|house|techno|trance|dubstep|drum|bass|country|gospel|classical|experimental|noise|ambient|synth|alternative|screamo|prog|fusion|groove|funk|soul|disco|latin|salsa|tango|world|gothic|industrial|death|post|psychedelic|power|speed|black|heavy|crust|ska|rockroll|soulfunk|psychobilly|benefit).*$'
            title = re.sub(genre_pattern, '', title, flags=re.I)
            
            # Odstraň všechno po "/"
            title = re.sub(r'\s*/.*$', '', title)
            
            # Vyčisti: normalizuj mezery
            title = ' '.join(title.split()).strip()
        
        # Sestav datum
        if day and month_val:
            date_str = f"{day.zfill(2)}.{month_val}.2026"
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
        
        # Vytvoř mapování obrázků -> event_id z .image_box_auto prvků
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
            
            # Vyber správný obrázek (mapovaný nebo default)
            event_image = image_map.get(event_id, default_image)
            
            # Přijmi event (s korektním obrázkem)
            if title and len(title) > 2 and len(title) < 300 and date_str:
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Palác Akropolis",
                    "category": "hudba",
                    "url": f"https://palacakropolis.cz/work/33298?event_id={event_id}",
                    "image": event_image,  # Používáme mapovaný obrázek nebo default
                })
        
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
    soup = get_soup("https://cafevlese.cz/")
    if not soup:
        return []

    events = []
    
    # Czech month mapping - zkrácené měsíce
    czech_months_short = {
        'led': '01', 'úno': '02', 'břě': '03', 'dub': '04',
        'kvě': '05', 'čer': '06', 'čvc': '07', 'srp': '08',
        'zář': '09', 'říj': '10', 'lis': '11', 'pro': '12'
    }
    
    # Najdi všechny event articles z MEC (My Events Calendar) pluginu
    articles = soup.find_all('article', class_='mec-event-article')
    
    for article in articles:
        # Získej URL z data-href atributu
        url = article.get('data-href', '')
        
        # Získej obrázek z style atributu (background: url('...'))
        style = article.get('style', '')
        image_url = ''
        if style:
            img_match = re.search(r"url\('([^']+)'\)", style)
            if img_match:
                image_url = img_match.group(1)
        
        # Získej titul z odkazu
        title_link = article.find('a', class_='mec-color-hover')
        title = title_link.get_text(strip=True) if title_link else ''
        
        # Získej datum z .mec-start-date-label (formát: "10 Dub", "25 Kvě", atd.)
        date_label = article.find('span', class_='mec-start-date-label')
        date_text = date_label.get_text(strip=True) if date_label else ''
        
        # Získej čas z .mec-event-time
        time_div = article.find('div', class_='mec-event-time')
        time_str = ''
        if time_div:
            time_match = re.search(r'(\d{2}:\d{2})', time_div.get_text())
            if time_match:
                time_str = time_match.group(1)
        
        # Zparsuj datum (např. "10 Dub" -> "10.04.2026")
        date_str = ''
        if date_text:
            parts = date_text.split()
            if len(parts) == 2:
                day = parts[0].zfill(2)
                month_short = parts[1].lower()[:3]
                
                # Najdi měsíc v mapování
                for short, month_num in czech_months_short.items():
                    if short in month_short:
                        date_str = f"{day}.{month_num}.2026"
                        break
        
        # Přidej event pokud máme titul a datum
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
    print("🎵 Roxy...")
    
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
    print("🎭 MeetFactory...")
    
    categories = [
        ('cs/program/hudba', 'hudba'),
        ('cs/program/divadlo', 'divadlo'),
        ('cs/program/ostatni', 'ostatni'),
        ('cs/program/galerie', 'galerie'),
        ('cs/program/rezidence', 'rezidence'),
    ]
    
    all_events = []
    
    for path, category in categories:
        try:
            url = f"https://meetfactory.cz/{path}"
            soup = get_soup(url)
            if not soup:
                continue
            
            # Hledej všechny ab-box divy (event items)
            event_boxes = soup.find_all('div', class_='ab-box')
            
            for box in event_boxes:
                # Obrázek
                img = box.find('img', class_='program-image')
                image_url = img.get('src', '') if img else ''
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
                url = detail_link.get('href', '') if detail_link else ''
                if url and not url.startswith('http'):
                    url = 'https://meetfactory.cz' + url
                
                # Pokud nemáme základní info, přeskočimo
                if not title or not date_text:
                    continue
                
                # Vytvoř datum ve správném formátu (např. "10. 4." -> "10.04.2026")
                date_match = re.match(r'(\d{1,2})\.\s*(\d{1,2})', date_text)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month = date_match.group(2).zfill(2)
                    date_formatted = f"{day}.{month}.2026"
                else:
                    date_formatted = ''
                
                if date_formatted:
                    all_events.append({
                        "title": title,
                        "date": date_formatted,
                        "time": time_text,
                        "venue": "MeetFactory",
                        "category": actual_category,
                        "url": url,
                        "image": image_url,
                    })
        
        except Exception as e:
            print(f"  [WARN] Chyba kategorie {category}: {e}", file=sys.stderr)
            continue
    
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
                # Extrahuj čas
                time_match = re.search(r'(\d{1,2}):(\d{2})', date_text)
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
#  HLAVNÍ FUNKCE
# ─────────────────────────────────────────────────────────────
def main():
    print("\n* Praha Koncerty - Scraper")
    print("=" * 40)
    print(f"Spuštěno: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")

    all_events = []

    scrapers = [
        scrape_rockcafe,
        scrape_musicbar,
        scrape_futurum,
        scrape_klub007,
        scrape_crossclub,
        scrape_akropolis,  # ✨ Nová BeautifulSoup verze bez Playwright
        scrape_vagon,
        scrape_cafevlese,
        scrape_kastan,  # 🎸 Kaštan (jen koncerty)
        scrape_meetfactory,  # 🎭 MeetFactory
        scrape_goout,
        scrape_roxy,
        scrape_atriumzizkov,  # 🎤 Atrium Žižkov
        # scrape_modravopice,  # Modrá Vopice - přeskočeno (timeout)
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

    # Filtrujeme divadlo
    unique_events = [e for e in unique_events if e.get("category", "").lower() != "divadlo"]
    
    # Počítáme Atrium eventy po filtrování
    atrium_after_filter = sum(1 for e in unique_events if e.get("venue") == "Atrium Žižkov")
    print(f"Po filtrování divadel: Atrium = {atrium_after_filter}")

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
"""
Praha Koncerty â€“ Scraper
========================
Stahuje program z praĹľskĂ˝ch klubĹŻ a uklĂˇdĂˇ do concerts.json.

SpuĹˇtÄ›nĂ­:
    pip install requests beautifulsoup4
    python scraper.py

Pro automatickĂ© spouĹˇtÄ›nĂ­ kaĹľdĂ˝ den:
  - Linux/Mac: pĹ™idej do cronu:  0 6 * * * python3 /cesta/ke/scraper.py
  - Windows:   nastav v Task Scheduleru
"""

import json
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def get_soup(url, timeout=15):
    """StĂˇhne strĂˇnku a vrĂˇtĂ­ BeautifulSoup objekt."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [WARN] Chyba pĹ™i stahovĂˇnĂ­ {url}: {e}", file=sys.stderr)
        return None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  ROCK CAFĂ‰  (rockcafe.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_rockcafe():
    print("* Rock Cafe...")
    soup = get_soup("https://rockcafe.cz/cs/program/")
    if not soup:
        return []

    events = []
    base = "https://rockcafe.cz"
    cards = soup.select("a[href*='/program/']")

    for card in cards:
        # Karty majĂ­ obrĂˇzek + h2 + text s datem
        h2 = card.find("h2")
        img = card.find("img")
        if not h2 or not img:
            continue

        title = h2.get_text(strip=True)
        # Datum je v textu karty â€“ formĂˇt "PĂˇtek 17.4.2026, 16:30"
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

    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  LUCERNA MUSIC BAR  (musicbar.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # Datum â€“ formĂˇt "10/4" nebo "11/4" v textu
        date_match = re.search(r"(\d{1,2}/\d{1,2})", text)
        time_match = re.search(r"(\d{2}:\d{2})", text)

        # NĂˇzev â€“ vÄ›tĹˇinou nejvÄ›tĹˇĂ­ blok textu bez datumu
        title_raw = re.sub(r"(Dnes|ZĂ­tra|PondÄ›lĂ­|ĂšterĂ˝|StĹ™eda|ÄŚtvrtek|PĂˇtek|Sobota|NedÄ›le)", "", text)
        title_raw = re.sub(r"\d{1,2}/\d{1,2}", "", title_raw)
        title_raw = re.sub(r"\d{2}:\d{2}", "", title_raw)
        title_raw = re.sub(r"(Koupit vstupenky|Vstupenky na pokladnÄ›|VyprodĂˇno|VĂ­ce informacĂ­)", "", title_raw)
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

    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  KLUB 007 STRAHOV  (klub007strahov.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_klub007():
    print("* Klub 007 Strahov...")
    soup = get_soup("https://klub007strahov.cz/program/")
    if not soup:
        return []

    events = []
    
    # Czech month mapping
    czech_months = {
        'leden': '01', 'Ăşnora': '02', 'bĹ™ezen': '03', 'duben': '04',
        'kvÄ›ten': '05', 'ÄŤerven': '06', 'ÄŤervenec': '07', 'srpen': '08',
        'zĂˇĹ™Ă­': '09', 'Ĺ™Ă­jen': '10', 'listopadu': '11', 'prosinec': '12'
    }
    
    # KaĹľdĂˇ akce je v elementu s tĹ™Ă­dou .event
    event_divs = soup.select('.event')
    
    for event_div in event_divs:
        # ZĂ­skej event ID
        event_id = event_div.get('data-event_id', '')
        
        # ZĂ­skej URL z prvnĂ­ho <a> tagu
        link = event_div.find('a', href=True)
        url = link.get('href', '') if link else ''
        
        # ZĂ­skej obrĂˇzek z meta tagu v schĂ©matu
        img_meta = event_div.find('meta', {'itemprop': 'image'})
        image = img_meta.get('content', '') if img_meta else ''
        
        # ZĂ­skej den z <em class="date">
        date_elem = event_div.find('em', class_='date')
        day = date_elem.get_text(strip=True) if date_elem else ''
        
        # ZĂ­skej celĂ˝ text na analĂ˝zu
        text = event_div.get_text(' ', strip=True)
        
        # Extrahuj mÄ›sĂ­c - najdi ÄŤeskĂ© jmĂ©no mÄ›sĂ­ce
        month_match = re.search(r'(leden|Ăşnora|bĹ™ezen|duben|kvÄ›ten|ÄŤerven|ÄŤervenec|srpen|zĂˇĹ™Ă­|Ĺ™Ă­jen|listopadu|prosinec)', text, re.I)
        month_val = ''
        if month_match:
            month_name = month_match.group(1).lower()
            month_val = czech_months.get(month_name, '')
        
        # Extrahuj ÄŤas (prvnĂ­ vĂ˝skyt HH:MM)
        time_match = re.search(r'(\d{2}):(\d{2})', text)
        time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ''
        
        # Extrahuj titul - text mezi "HH:MM HH:MM " a " Detail akce"
        title = ""
        title_match = re.search(r'\d{2}:\d{2}\s+\d{2}:\d{2}\s+(.+?)\s+Detail akce', text)
        if title_match:
            title = title_match.group(1)
            
            # OdstraĹ kĂłdy zemĂ­: (de), (cz), (fi/gr), (uk/us), atd.
            title = re.sub(r'\s*\([a-z]{2}(?:/[a-z]{2})*\)\s*', ' ', title, flags=re.I)
            
            # OdstraĹ ĹľĂˇnry - slova jako "Metal", "Rock", "/", atd. vÄŤetnÄ› tÄ›ch bez mezery pĹ™edtĂ­m
            # Pattern: matchuje genre klĂ­ÄŤovĂˇ slova bez/se mezerou a vĹˇechno za nĂ­m
            genre_pattern = r'(?:\s|(?<=[A-Z]))+(metal|rock|punk|indie|pop|jazz|electronic|sludge|stoner|doom|grind|hardcore|folk|blues|reggae|rap|hip|house|techno|trance|dubstep|drum|bass|country|gospel|classical|experimental|noise|ambient|synth|alternative|screamo|prog|fusion|groove|funk|soul|disco|latin|salsa|tango|world|gothic|industrial|death|post|psychedelic|power|speed|black|heavy|crust|ska|rockroll|soulfunk|psychobilly|benefit).*$'
            title = re.sub(genre_pattern, '', title, flags=re.I)
            
            # OdstraĹ vĹˇechno po "/"
            title = re.sub(r'\s*/.*$', '', title)
            
            # VyÄŤisti: normalizuj mezery
            title = ' '.join(title.split()).strip()
        
        # Sestav datum
        if day and month_val:
            date_str = f"{day.zfill(2)}.{month_val}.2026"
        else:
            date_str = ''
        
        # PĹ™idej akci pokud mĂˇme titul a datum
        if title and date_str and len(title) > 2 and len(title) < 300:
            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "Klub 007 Strahov",
                "category": "hudba",
                "url": url,
                "image": image,
            })

    print(f"   [OK] {len(events)} akcĂ­")
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  CROSS CLUB  (crossclub.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_crossclub():
    print("* Cross Club...")
    soup = get_soup("https://www.crossclub.cz/cs/program/")
    if not soup:
        return []

    events = []
    base = "https://www.crossclub.cz"

    # Akce jsou v ÄŤlĂˇncĂ­ch nebo divcĂ­ch s odkazem na program
    items = soup.select("a[href*='/program/']")

    for item in items:
        h2 = item.find(["h2", "h3"])
        img = item.find("img")
        if not h2:
            continue

        title = h2.get_text(strip=True)
        text = item.get_text(" ", strip=True)

        # Datum â€“ formĂˇt "10.04.2026" nebo "10.04."
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

    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  PALĂC AKROPOLIS  (palacakropolis.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_akropolis():
    print("* Palác Akropolis...")
    try:
        # âś¨ Parsujeme HTML tabulku bez Playwright â€“ mnohem rychlejĹˇĂ­!
        soup = get_soup("https://palacakropolis.cz/work/33298")
        if not soup:
            return []
        
        events = []
        year = datetime.now().year
        
        # OdstraĹ script a style tagy
        for tag in soup(['script', 'style']):
            tag.decompose()
        
        # Hledej VĹ ECHNY TR s event_id â€“ tabulka obsahuje Seznam akcĂ­  
        all_trs = soup.find_all('tr')
        seen = set()
        
        # PostrannĂ­: Najdi Default image pro Akropolis (vĹˇechny eventy majĂ­ stejnĂ˝)
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
        
        # VytvoĹ™ mapovĂˇnĂ­ obrazkĹŻ -> event_id z .image_box_auto prvkĹŻ
        image_map = {}  # event_id -> image_url
        image_boxes = soup.find_all(True, class_='image_box_auto')
        for img in image_boxes:
            src = img.get('src', '')
            if not src:
                continue
            
            # Projdi nadĹ™azenĂ© prvky a hledej event_id
            current = img.parent
            for _ in range(10):
                if not current:
                    break
                
                parent_html = str(current)
                event_match = re.search(r'event_id=(\d+)', parent_html)
                
                if event_match:
                    event_id = event_match.group(1)
                    # VytvoĹ™ absolutnĂ­ URL
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
            
            # Hledej datum v TD se tĹ™Ă­dou banner_popup_date
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
            
            # Fallback: hledĂˇme datum v textu TR pokud jsme nenaĹˇli
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
            
            # Hledej nĂˇzev v <a> tagu s event_id
            a_tag = tr.find('a', href=re.compile(r'event_id'))
            title = a_tag.get_text(strip=True) if a_tag else ""
            
            # OÄŤisti nĂˇzev
            title = re.sub(r'[â–şâ–Ľâ—„âś“âś—]', '', title)
            title = " ".join(title.split()).strip()
            
            # Hledej ÄŤas v textu TR
            tr_text = tr.get_text(strip=True)
            time_match = re.search(r'(\d{2}):(\d{2})', tr_text)
            time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ""
            
            # Vyber sprĂˇvnĂ˝ obrĂˇzek (mapovanĂ˝ nebo default)
            event_image = image_map.get(event_id, default_image)
            
            # PĹ™ijmi event (s korektnĂ­m obrĂˇzkem)
            if title and len(title) > 2 and len(title) < 300 and date_str:
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Palác Akropolis",
                    "category": "hudba",
                    "url": f"https://palacakropolis.cz/work/33298?event_id={event_id}",
                    "image": event_image,  # Používáme mapovaný obrázek nebo default
                })
        
        print(f"   [OK] {len(events)} akcĂ­")
        return events

    except Exception as e:
        print(f"  [WARN] Chyba Akropolis: {e}", file=sys.stderr)
        return []


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  VAGON  (vagon.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        print(f"   [WARN] Zadne radky v tabulce")
        return []

    # Hledej mÄ›sĂ­c/rok v nadpisu strĂˇnky
    month, year = 4, datetime.now().year  # Default: duben letoĹˇnĂ­ho roku
    h3_tag = soup.find('h3')
    if h3_tag:
        text = h3_tag.get_text(strip=True)
        # Pokus se parsovat mÄ›sĂ­c a rok (napĹ™. "duben 2026")
        year_match = re.search(r'(\d{4})', text)
        if year_match:
            year = int(year_match.group(1))

    # Parsuj Ĺ™Ăˇdky (pĹ™eskoÄŤ header)
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

            # Filtruj ZAVĹENO
            if not nazev or nazev.upper() == "ZAVĹENO":
                continue

            # Parsuj ÄŤas
            time_match = re.search(r'(\d{2}):(\d{2})', cas_info)
            time_str = time_match.group(0) if time_match else ""

            # VytvoĹ™ datum (den_cislo.4.year)
            try:
                day_num = int(den_cislo)
                date_str = f"{day_num}.4.{year}"
            except:
                continue

            # Pokud je nĂˇzev jen ÄŤas (napĹ™. "20:00 MUSIC VIDEO PARTY"), 
            # extrahuj sprĂˇvnĂ˝ nĂˇzev (bez ÄŤasu)
            if re.match(r'^\d{2}:\d{2}', nazev):
                # NĂˇzev zaÄŤĂ­nĂˇ ÄŤasem, vezmi vĹˇe za prvnĂ­m ÄŤasem
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

    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  CAFE V LESE  (cafevlese.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_cafevlese():
    print("* Cafe v lese...")
    soup = get_soup("https://cafevlese.cz/")
    if not soup:
        return []

    events = []
    
    # Czech month mapping - zkrĂˇcenĂ© mÄ›sĂ­ce
    czech_months_short = {
        'led': '01', 'Ăşno': '02', 'bĹ™e': '03', 'dub': '04',
        'kvÄ›': '05', 'ÄŤer': '06', 'ÄŤvc': '07', 'srp': '08',
        'zĂˇĹ™': '09', 'Ĺ™Ă­j': '10', 'lis': '11', 'pro': '12'
    }
    
    # Najdi vĹˇechny event articles z MEC (My Events Calendar) pluginu
    articles = soup.find_all('article', class_='mec-event-article')
    
    for article in articles:
        # ZĂ­skej URL z data-href atributu
        url = article.get('data-href', '')
        
        # ZĂ­skej obrĂˇzek z style atributu (background: url('...'))
        style = article.get('style', '')
        image_url = ''
        if style:
            img_match = re.search(r"url\('([^']+)'\)", style)
            if img_match:
                image_url = img_match.group(1)
        
        # ZĂ­skej titul z odkazu
        title_link = article.find('a', class_='mec-color-hover')
        title = title_link.get_text(strip=True) if title_link else ''
        
        # ZĂ­skej datum z .mec-start-date-label (formĂˇt: "10 Dub", "25 KvÄ›", atd.)
        date_label = article.find('span', class_='mec-start-date-label')
        date_text = date_label.get_text(strip=True) if date_label else ''
        
        # ZĂ­skej ÄŤas z .mec-event-time
        time_div = article.find('div', class_='mec-event-time')
        time_str = ''
        if time_div:
            time_match = re.search(r'(\d{2}:\d{2})', time_div.get_text())
            if time_match:
                time_str = time_match.group(1)
        
        # Zparsuj datum (napĹ™. "10 Dub" -> "10.04.2026")
        date_str = ''
        if date_text:
            parts = date_text.split()
            if len(parts) == 2:
                day = parts[0].zfill(2)
                month_short = parts[1].lower()[:3]
                
                # Najdi mÄ›sĂ­c v mapovĂˇnĂ­
                for short, month_num in czech_months_short.items():
                    if short in month_short:
                        date_str = f"{day}.{month_num}.2026"
                        break
        
        # PĹ™idej event pokud mĂˇme titul a datum
        if title and date_str:
            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "CafĂ© v lese",
                "category": "hudba",
                "url": url,
                "image": image_url,
            })

    print(f"   [OK] {len(events)} akcĂ­")
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  FUTURUM  (futurum.musicbar.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            # Hledej datum s teÄŤkami pĹ™Ă­mĂ˝ pattern (PĂˇtek10.04.2026)
            match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', date_div.get_text(strip=True))
            if match:
                date_str = match.group(1)

        # Extrahuj ÄŤas z textu
        time_match = re.search(r"(\d{2}:\d{2})", card.get_text())
        time_str = time_match.group(1) if time_match else ""

        # Extrahuj nĂˇzev akce - vĹˇe po ÄŤase v textu
        text = card.get_text(" ", strip=True)
        
        # OdstraĹ den v tĂ˝dnu
        title_raw = re.sub(r"(Dnes|ZĂ­tra|PondÄ›lĂ­|ĂšterĂ˝|StĹ™eda|ÄŚtvrtek|PĂˇtek|Sobota|NedÄ›le)", "", text)
        
        # OdstraĹ datum
        title_raw = re.sub(r"\d{1,2}\.\d{1,2}\.\d{4}", "", title_raw)
        
        # OdstraĹ ÄŤas
        title_raw = re.sub(r"\d{2}:\d{2}", "", title_raw)
        
        # OdstraĹ specifickĂ© texty
        title_raw = re.sub(r"(Koupit vstupenky|Vstupenky na pokladnÄ›|VyprodĂˇno|VĂ­ce informacĂ­)", "", title_raw)
        
        # VyÄŤisti: normalizuj mezery
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

    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  GOOUT  (goout.net)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_goout():
    """
    GoOut je single-page aplikace (React) â€“ ÄŤistĂ˝ requests/BS4 nestaÄŤĂ­.
    Ale GoOut mĂˇ veĹ™ejnĂ© API! PouĹľijeme ho mĂ­sto scrapovĂˇnĂ­.
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

    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  ROXY  (roxy.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_roxy():
    """Scraper pro Roxy.cz - ÄŤte items z event-list"""
    print("đźŽŞ Roxy...")
    
    soup = get_soup("https://www.roxy.cz/#program")
    if not soup:
        return []
    
    events = []
    
    # Najdi event-list (hlavnĂ­ seznam s data-date atributy)
    event_list = soup.find('div', class_='event-list')
    if not event_list:
        return []
    
    items = event_list.find_all('a', class_='item')
    
    for item in items:
        try:
            # Extrahuj artist (H2)
            h2 = item.find('h2')
            artist = h2.get_text(strip=True) if h2 else ""
            
            # Extrahuj tag/subtitle (H3) - napĹ™. (SK), (DE), (CZ)
            h3 = item.find('h3')
            tag = h3.get_text(strip=True) if h3 else ""
            
            # Extrahuj datum z textu - formĂˇt "P.10/04 Artist..."
            text = item.get_text(strip=True)
            date_match = re.search(r'(\d{1,2})/(\d{2})', text)
            
            if not date_match or not artist:
                continue
            
            day = date_match.group(1)
            month = date_match.group(2)
            year = 2026  # VĹˇechny items majĂ­ data-date="042026"
            
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
                    # Konvertuj na absolutnĂ­ URL
                    if rel_path.startswith('/'):
                        image_url = 'https://www.roxy.cz' + rel_path
                    else:
                        image_url = 'https://www.roxy.cz/' + rel_path
                    break
            
            # VytvoĹ™ nĂˇzev - Artist + tag
            title = artist
            if tag and tag != "":
                title = f"{artist} {tag}"
            
            events.append({
                "title": title,
                "date": date_str,
                "time": "",  # ÄŚasy nejsou v pĹ™ehledu programu
                "venue": "Roxy",
                "category": "hudba",
                "url": href,
                "image": image_url,
            })
        except Exception as e:
            continue
    
    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  MODRĂ VOPICE  (modravopice.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_modravopice():
    """Scraper pro Modrá Vopice - čte items z eventon_list_event"""
    print("* Modrá Vopice...")
    
    soup = get_soup("https://www.modravopice.cz/program/", timeout=30)
    if not soup:
        return []
    
    events = []
    
    # Najdi event rows
    rows = soup.find_all('div', class_='eventon_list_event')
    
    for row in rows:
        try:
            # Filtruj popup/lightbox rows
            classes = row.get('class', [])
            if 'evo_lightbox_body' in classes or 'evo_pop_body' in classes:
                continue
            
            # Extrahuj z paragrafu (child 2) - formĂˇt: "den ÄŤĂ­slo mÄ›sĂ­c ÄŤas text"
            p = row.find('p')
            if not p:
                continue
            
            text = p.get_text(" ", strip=True)
            
            # Extrahuj ÄŤas - HH:MM
            time_match = re.search(r'(\d{2}):(\d{2})', text)
            time_str = time_match.group(0) if time_match else ""
            
            # Strategie: po ÄŤase a DOPORUÄŚUJEME je jmĂ©no akce
            # FormĂˇt: "xx NN MÄ›sĂ­c HH:MM DOPORUÄŚUJEME NĂZEV CENA HH:MM"
            
            # Pokus 1: Extrahuj text po "DOPORUÄŚUJEME"
            if 'DOPORUÄŚUJEME' in text:
                title = text.split('DOPORUÄŚUJEME', 1)[1].strip()
            else:
                # Pokus 2: Extrahuj text po nejpozdÄ›jĹˇĂ­m HH:MM (ÄŤase)
                # Najdi vĹˇechny ÄŤasy a vezmi text po poslednĂ­m
                time_matches = list(re.finditer(r'\d{2}:\d{2}', text))
                if time_matches:
                    last_time_pos = time_matches[-1].end()
                    title = text[last_time_pos:].strip()
                else:
                    title = text
            
            # OdstraĹ cenu na konci (###,- KÄŤ) - mĂˇ bĂ˝t alespoĹ jeden digit a KÄŤ
            title = re.sub(r'\s*\d+\s*,\s*-?\s*K.*$', '', title).strip()
            title = re.sub(r'\s+\d{2}:\d{2}\s*$', '', title).strip()  # OdstraĹ ÄŤas na konci
            
            if not title or len(title) < 3:
                continue
            
            # Extrahuj datum z child 3 div - hledej PM format "DD. M. YYYY, HH:MM"
            description_div = None
            children = list(row.children)
            if len(children) > 3:
                description_div = children[3]
            
            date_str = ""
            if description_div:
                desc_text = description_div.get_text(" ", strip=True)
                # Hledej "DD. M. YYYY" formĂˇt
                date_match = re.search(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})', desc_text)
                if date_match:
                    day = date_match.group(1)
                    month = date_match.group(2)
                    year = date_match.group(3)
                    date_str = f"{day}.{month}.{year}"
            
            # Fallback - pokud nemĂˇme datum, pĹ™eskoÄŤi
            if not date_str:
                continue
            
            # Extrahuj link
            a = row.find('a', href=True)
            href = a.get('href', '') if a else ""
            if href and not href.startswith('http'):
                href = 'https://www.modravopice.cz' + href if href.startswith('/') else 'https://www.modravopice.cz/' + href
            
            # Extrahuj image z background-image CSS
            image_url = ""
            for div in row.find_all('div'):
                style = div.get('style', '')
                if 'background-image' in style:
                    img_match = re.search(r'background-image:\s*url\(([^)]+)\)', style)
                    if img_match:
                        rel_path = img_match.group(1).strip("'\"")
                        if rel_path.startswith('/'):
                            image_url = 'https://www.modravopice.cz' + rel_path
                        elif rel_path.startswith('http'):
                            image_url = rel_path
                        else:
                            image_url = 'https://www.modravopice.cz/' + rel_path
                        break
            
            events.append({
                "title": title,
                "date": date_str,
                "time": time_str,
                "venue": "ModrĂˇ Vopice",
                "category": "hudba",
                "url": href,
                "image": image_url,
            })
        except Exception as e:
            continue
    
    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  KAĹ TAN  (kastan.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_kastan():
    """Scraper pro Kaštan.cz - pouze koncerty (stahuje všechny stránky)"""
    print("* Kaštan...")
    
    events = []
    base_url = "https://kastan.cz/"
    max_pages = 3  # Kaštan má max 3 stránky s akcemi
    
    for page in range(1, max_pages + 1):
        try:
            # Konstrukce URL s strĂˇnkovĂˇnĂ­m
            url = base_url if page == 1 else f"{base_url}?paged={page}"
            
            soup = get_soup(url)
            if not soup:
                continue
            
            # Hledej vĹˇechny koncerty (elementy s akce_category-koncert NEBO akce_category-festival-koncertni-prehlidka)
            koncerty = soup.find_all(True, class_=re.compile('akce_category-koncert'))
            prehlidky = soup.find_all(True, class_=re.compile('festival-koncertni-prehlidka'))
            
            # SpojenĂ­ - eliminuj duplikĂˇty
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
                    
                    # ObrĂˇzek
                    img = koncert.find('img')
                    image_src = img.get('src', '') if img else ''
                    
                    # NĂˇzev: z h1 nebo program_nadpis
                    nadpis = koncert.find('h1') or koncert.find('div', class_='program_nadpis')
                    title = nadpis.get_text(strip=True) if nadpis else ''
                    
                    if not title or not event_url:
                        continue
                    
                    # Datum: z program_datum
                    datum_div = koncert.find('div', class_='program_datum')
                    datum_text = datum_div.get_text(strip=True) if datum_div else ''
                    
                    date_match = re.search(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})', datum_text)
                    date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}" if date_match else ""
                    
                    # ÄŚas
                    time_match = re.search(r'(\d{1,2}):(\d{2})', datum_text)
                    time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ""
                    
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
                    })
                
                except Exception as e:
                    print(f"  [WARN] Chyba pĹ™i parsovĂˇnĂ­ jednĂ© akce: {e}", file=sys.stderr)
                    continue
        
        except Exception as e:
            print(f"  [WARN] Chyba na strĂˇnce {page}: {e}", file=sys.stderr)
            continue
    
    print(f"   [OK] {len(events)} akcĂ­")
    return events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  MEET FACTORY  (meetfactory.cz)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def scrape_meetfactory():
    """Scraper pro MeetFactory.cz - scrapuje hudbu, divadlo, atd."""
    print("đźŽ­ MeetFactory...")
    
    categories = [
        ('cs/program/hudba', 'hudba'),
        ('cs/program/divadlo', 'divadlo'),
        ('cs/program/ostatni', 'ostatni'),
        ('cs/program/galerie', 'galerie'),
        ('cs/program/rezidence', 'rezidence'),
    ]
    
    all_events = []
    
    for path, category in categories:
        try:
            url = f"https://meetfactory.cz/{path}"
            soup = get_soup(url)
            if not soup:
                continue
            
            # Hledej vĹˇechny ab-box divy (event items)
            event_boxes = soup.find_all('div', class_='ab-box')
            
            for box in event_boxes:
                # ObrĂˇzek
                img = box.find('img', class_='program-image')
                image_url = img.get('src', '') if img else ''
                # Konvertuj relativnĂ­ cestu na absolutnĂ­ URL
                if image_url and not image_url.startswith('http'):
                    image_url = 'https://meetfactory.cz' + image_url
                
                # Datum - v <p class="abb-date"><b>
                date_elem = box.find('b')
                date_text = date_elem.get_text(strip=True) if date_elem else ''
                
                # ÄŚas - v <span> na Ĺ™Ăˇdku s datem
                date_p = box.find('p', class_='abb-date')
                time_text = ''
                if date_p:
                    spans = date_p.find_all('span')
                    if len(spans) >= 2:
                        time_text = spans[-1].get_text(strip=True)
                
                # Kategorie
                cat_link = box.find('a', class_='cat')
                actual_category = cat_link.get_text(strip=True).lower() if cat_link else category
                
                # NĂˇzev - hledej <span class="h3_active"> NEBO <span itemprop="name">
                title = ""
                title_span = box.find('span', class_='h3_active')
                if not title_span:
                    title_span = box.find('span', {'itemprop': 'name'})
                if title_span:
                    title = title_span.get_text(strip=True)
                
                # URL
                detail_link = box.find('a', class_='abbl-detail')
                url = detail_link.get('href', '') if detail_link else ''
                if url and not url.startswith('http'):
                    url = 'https://meetfactory.cz' + url
                
                # Pokud nemĂˇme zĂˇkladnĂ­ info, pĹ™eskoÄŤimo
                if not title or not date_text:
                    continue
                
                # VytvoĹ™ datum ve sprĂˇvnĂ©m formĂˇtu (napĹ™. "10. 4." -> "10.04.2026")
                date_match = re.match(r'(\d{1,2})\.\s*(\d{1,2})', date_text)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month = date_match.group(2).zfill(2)
                    date_formatted = f"{day}.{month}.2026"
                else:
                    date_formatted = ''
                
                if date_formatted:
                    all_events.append({
                        "title": title,
                        "date": date_formatted,
                        "time": time_text,
                        "venue": "MeetFactory",
                        "category": actual_category,
                        "url": url,
                        "image": image_url,
                    })
        
        except Exception as e:
            print(f"  [WARN] Chyba kategorie {category}: {e}", file=sys.stderr)
            continue
    
    print(f"   [OK] {len(all_events)} akcĂ­")
    return all_events


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  HLAVNĂŤ FUNKCE
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    print("\n* Praha Koncerty - Scraper")
    print("=" * 40)
    print(f"Spusteno: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")

    all_events = []

    scrapers = [
        scrape_rockcafe,
        scrape_musicbar,
        scrape_futurum,
        scrape_klub007,
        scrape_crossclub,
        scrape_akropolis,  # âś¨ NovĂˇ BeautifulSoup verze bez Playwright
        scrape_vagon,
        scrape_cafevlese,
        scrape_kastan,  # 🎸 Kaštan (jen koncerty)
        scrape_meetfactory,  # đźŽ­ MeetFactory
        scrape_goout,
        scrape_roxy,
        # scrape_modravopice,  # Modrá Vopice - přeskočeno (timeout)
    ]

    for scraper in scrapers:
        try:
            events = scraper()
            all_events.extend(events)
        except Exception as e:
            print(f"  [ERROR] NeoÄŤekĂˇvanĂˇ chyba: {e}", file=sys.stderr)

    # Deduplikace podle nĂˇzvu + data
    seen = set()
    unique_events = []
    for e in all_events:
        key = (e["title"].lower().strip(), e["date"])
        if key not in seen:
            seen.add(key)
            unique_events.append(e)

    # SeĹ™adĂ­me podle data
    def sort_key(e):
        try:
            parts = e["date"].replace(" ", "").split(".")
            if len(parts) >= 3:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            pass
        return datetime(9999, 1, 1)

    unique_events.sort(key=sort_key)

    # Filtrujeme divadlo
    unique_events = [e for e in unique_events if e.get("category", "").lower() != "divadlo"]

    # UloĹľĂ­me do JSON
    output = {
        "updated": datetime.now().isoformat(),
        "count": len(unique_events),
        "events": unique_events,
    }

    with open("concerts.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Hotovo! Ulozeno {len(unique_events)} akci do concerts.json")
    print(f"   Soubor: concerts.json")


if __name__ == "__main__":
    main()

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
        
        image = ''  # klub007strahov.cz blokuje hotlinking
        
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
                    "url": f"https://palacakropolis.cz/work/33298?event_id={event_id}",
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
        'kvě': '05', 'čer': '06', 'čvc': '07', 'srp': '08',
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
    for i in range(1, 4):
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
    print("* MeetFactory...")
    
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
            # Zvýšený timeout pro MeetFactory - stránka je pomalejší
            soup = get_soup(url, timeout=30)
            if not soup:
                continue
            
            # Hledej všechny ab-box divy (event items)
            event_boxes = soup.find_all('div', class_='ab-box')
            
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
    soup = get_soup("https://www.jazzdock.cz/cs/program")
    if not soup:
        return []
    
    events = []
    program_items = soup.find_all('div', class_='program-item')
    
    for item in program_items:
        try:
            # Nadpis
            h2 = item.find('h2')
            title = h2.get_text(strip=True) if h2 else ''
            
            if not title or len(title) < 2:
                continue
            
            # Čas a datum - hledej "DNES HRAJEME od" nebo "ne 12. 04. od"
            all_text = item.get_text(" ", strip=True)
            
            date_str = ''
            time_str = ''
            
            # Extrahuj čas
            time_match = re.search(r'od\s+(\d{1,2}):(\d{2})', all_text)
            if time_match:
                time_str = f"{time_match.group(1)}:{time_match.group(2)}"
            
            # Extrahuj datum
            if "DNES HRAJEME" in all_text:
                # Dnes
                today = datetime.now().date()
                date_str = today.strftime("%d.%m.%Y")
            else:
                # Hledej vzor: "ne 12. 04." nebo "po 11. 04." atd.
                date_match = re.search(r'(po|út|st|čt|pá|so|ne)\s+(\d{1,2})\.\s+(\d{1,2})\.', all_text)
                if date_match:
                    day = date_match.group(2)
                    month = date_match.group(3)
                    year = "2026"
                    date_str = f"{day}.{month}.{year}"
            
            # Kategorie - v span
            span = item.find('span', class_='label-gender')
            category_raw = span.get_text(strip=True) if span else 'hudba'
            
            # Mapuj kategorie - všechno je hudba nebo divadlo
            if "theatre" in category_raw.lower() or "divadlo" in category_raw.lower():
                category = "divadlo"
            else:
                category = "hudba"
            
            # Obrázek
            img = item.find('img')
            image = ''
            if img:
                img_src = img.get('src', '')
                if img_src:
                    if not img_src.startswith('http'):
                        image = 'https://www.jazzdock.cz' + img_src
                    else:
                        image = img_src
            
            # Link
            link = item.find('a', href=True)
            url = ''
            if link:
                href = link.get('href', '')
                if href:
                    if not href.startswith('http'):
                        url = 'https://www.jazzdock.cz' + href
                    else:
                        url = href
            
            if date_str:
                events.append({
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                    "venue": "Jazz Dock",
                    "category": category,
                    "url": url,
                    "image": image,
                })
        
        except Exception as e:
            continue
    
    print(f"   [OK] {len(events)} akcí")
    return events


# ─────────────────────────────────────────────────────────────
#  ARCHA+  (archa-plus.cz)
# ─────────────────────────────────────────────────────────────
def scrape_archa():
    print("* Archa+...")
    from datetime import date as _date

    soup = get_soup("https://archa-plus.cz/cz/program/")
    if not soup:
        return []

    today = _date.today()
    events = []

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

        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', href)
        if not date_match:
            continue
        y, m, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        if _date(y, m, d) < today:
            continue
        date_str = f"{d:02d}.{m:02d}.{y}"

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

    soup = get_soup("https://www.redutajazzclub.cz/program-cs")
    if not soup:
        return []

    date_pattern = re.compile(r'^d\d{8}$')
    events = []

    for div in soup.find_all('div'):
        classes = div.get('class', [])
        date_cls = next((c for c in classes if date_pattern.match(c)), None)
        if not date_cls:
            continue

        day = date_cls[1:3]
        month = date_cls[3:5]
        year = date_cls[5:9]
        date_str = f"{day}.{month}.{year}"

        for lnk in div.find_all('a'):
            img = lnk.find('img')
            if not img:
                continue
            title = img.get('alt', '').strip()
            if not title:
                continue
            href = lnk.get('href', '')
            image_url = img.get('src', '')
            events.append({
                "title": title,
                "date": date_str,
                "time": "",
                "venue": "Reduta Jazz Club",
                "category": "hudba",
                "url": href,
                "image": image_url,
            })

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
        scrape_o2arena,
        scrape_cargogallery,
        scrape_sasazu,
        scrape_musicclubjizak,
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

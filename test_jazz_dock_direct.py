#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def get_soup(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [WARN] Chyba: {e}")
        return None

def scrape_jazz_dock():
    """Scraper pro Jazz Dock"""
    print("* Jazz Dock...")
    soup = get_soup("https://www.jazzdock.cz/cs/program")
    if not soup:
        return []
    
    events = []
    program_items = soup.find_all('div', class_='program-item')
    
    print(f"  Nalezeno program-item prvků: {len(program_items)}")
    
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
                print(f"    + {title[:40]}: {date_str}")
        
        except Exception as e:
            print(f"    Error: {e}")
            continue
    
    print(f"   [OK] {len(events)} akcí")
    return events

events = scrape_jazz_dock()
print(f"\nExtracted {len(events)} events")

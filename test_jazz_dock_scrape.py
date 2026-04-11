#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test extracting dates from Jazz Dock program items text
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

url = "https://www.jazzdock.cz/cs/program"
r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

program_items = soup.find_all("div", class_="program-item")
print(f"Počet events: {len(program_items)}\n")

# Mapping Czech day abbreviations to numbers
day_mapping = {
    'po': 1, 'út': 2, 'st': 3, 'čt': 4, 'pá': 5, 'so': 6, 'ne': 7
}

for i, item in enumerate(program_items[:5], 1):
    print(f"Event {i}:")
    
    # Nadpis
    h2 = item.find("h2")
    title = h2.get_text(strip=True) if h2 else ""
    print(f"  Nadpis: {title[:60]}")
    
    # Čas - hledej "od XX:XX" v textu
    text = item.get_text(" ", strip=True)
    
    # Hledej "DNES HRAJEME od" nebo "ne 12. 04. od"
    if "DNES HRAJEME" in text:
        # Oggi je dnes
        today = datetime.now().date()
        date_str = today.strftime("%d.%m.%Y")
        print(f"  Datum: {date_str} (DNES)")
    else:
        # Hledej vzor: "ne 12. 04." nebo "po 11. 04." atd.
        date_match = re.search(r'(po|út|st|čt|pá|so|ne)\s+(\d{1,2})\.\s+(\d{1,2})\.', text)
        if date_match:
            day_abbr = date_match.group(1)
            day = date_match.group(2)
            month = date_match.group(3)
            # Přidej rok
            year = "2026"
            date_str = f"{day}.{month}.{year}"
            print(f"  Datum: {date_str} ({day_abbr})")
        else:
            print(f"  Datum: nenalezeno")
    
    # Čas
    time_match = re.search(r'od\s+(\d{1,2}):(\d{2})', text)
    if time_match:
        time_str = f"{time_match.group(1)}:{time_match.group(2)}"
        print(f"  Čas: {time_str}")
    else:
        print(f"  Čas: nenalezeno")
    
    # Kategorie - hledej po kommu
    # Text often: "title[space]label date[space]description"
    span = item.find("span", class_="label-gender")
    category = span.get_text(strip=True) if span else "hudba"
    print(f"  Kategorie: {category}")
    
    # Obrázek
    img = item.find("img")
    image = img.get("src", "") if img else ""
    if image and not image.startswith("http"):
        image = "https://www.jazzdock.cz" + image
    print(f"  Obrázek: {image[:60]}...")
    
    print()

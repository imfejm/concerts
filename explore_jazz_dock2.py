#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed exploration of Jazz Dock event structure
"""

import requests
from bs4 import BeautifulSoup
import re

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

# Najdi program-item prvky
program_items = soup.find_all("div", class_="program-item")
print(f"Počet program-item: {len(program_items)}\n")

if program_items:
    print("=== Struktura prvního program-item ===\n")
    first = program_items[0]
    
    print(f"HTML:\n{first.prettify()[:1500]}\n")
    
    print("=== Extrahované údaje ===\n")
    
    # Nadpis
    h2 = first.find("h2")
    title = h2.get_text(strip=True) if h2 else ""
    print(f"Nadpis (h2): {title}")
    
    # Obrázek
    img = first.find("img")
    image = img.get("src", "") if img else ""
    if image and not image.startswith("http"):
        image = "https://www.jazzdock.cz" + image
    print(f"Obrázek: {image}")
    
    # Datum a čas - pravděpodobně v textu
    all_text = first.get_text(" ", strip=True)
    print(f"Všechen text: {all_text[:200]}")
    
    # Hledej datum ve tvaru XX.X.XXXX
    date_match = re.search(r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})', all_text)
    print(f"\nDatum (regex): {date_match.group(1) if date_match else 'Nenalezeno'}")
    
    # Hledej čas ve tvaru XX:XX
    time_match = re.search(r'(\d{1,2}):(\d{2})', all_text)
    print(f"Čas (regex): {time_match.group(0) if time_match else 'Nenalezeno'}")
    
    # Link
    link = first.find("a", href=True)
    href = link.get("href", "") if link else ""
    if href and not href.startswith("http"):
        href = "https://www.jazzdock.cz" + href
    print(f"Link: {href}")
    
    # Zkus nalézt jednotlivé prvky (div, p, span)
    print("\n=== Sub-prvky ===\n")
    
    # Najdi všechny p prvky
    ps = first.find_all("p")
    print(f"Počet <p> prvků: {len(ps)}")
    for i, p in enumerate(ps[:3], 1):
        print(f"  {i}. {p.get_text(strip=True)[:100]}")
    
    # Najdi všechny span prvky
    spans = first.find_all("span")
    print(f"\nPočet <span> prvků: {len(spans)}")
    for i, span in enumerate(spans[:3], 1):
        print(f"  {i}. {span.get_text(strip=True)[:100]}")
    
    # Najdi všechny div prvky
    divs = first.find_all("div", recursive=False)
    print(f"\nPříchází dvě úrovně div prvků: {len(divs)}")
    for i, div in enumerate(divs[:3], 1):
        class_attr = div.get("class", [])
        text = div.get_text(strip=True)[:60]
        print(f"  {i}. class={class_attr} text={text}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Look for date headers/groupings on Jazz Dock program page
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

# Najdi všechny nadpisy na stránce
headings = soup.find_all(["h1", "h2", "h3", "h4", "h5"])
print("=== Všechny nadpisy ===\n")
for i, h in enumerate(headings, 1):
    text = h.get_text(strip=True)[:100]
    if text:
        print(f"{i}. {h.name}: {text}")

print("\n=== Hledání datům podobných textů ===\n")

# Hledej všechny divs, které obsahují datum
main = soup.find("main") or soup.find("div", class_="container")
if main:
    # Najdi všechny divy, které obsahují čísla a tečky (datum-like)
    all_divs = main.find_all("div")
    date_like_divs = []
    
    for div in all_divs:
        text = div.get_text(strip=True)
        if re.search(r'\d{1,2}\.\s*\d{1,2}\.', text) and len(text) < 150:
            date_like_divs.append((div.get("class", []), text))
    
    if date_like_divs:
        print(f"Nalezeno {len(date_like_divs)} divů s čísly podobnými datumům:")
        for class_list, text in date_like_divs[:10]:
            print(f"  class={class_list}: {text[:80]}")

print("\n=== Struktura obsahu ===\n")

# Najdi program oddíl
prog_sections = soup.find_all(["section", "div"], class_=["program", "list", "events"])
print(f"Sekce s program/list/events: {len(prog_sections)}")

# Podívej se na strukturu okolo program-item
program_items = soup.find_all("div", class_="program-item")
if program_items:
    # Podívej se na prvky před a za prvním programem
    first_item = program_items[0]
    
    # Najdi parent, který obsahuje více items
    parent = first_item.parent
    while parent and parent.name != "main":
        # Podívej se na všechny siblings
        siblings = parent.find_all("div", recursive=False)
        if len(siblings) > 1:
            print(f"\nParent {parent.get('class', [])} má {len(siblings)} přímých potomků (divů)")
            # Podívej se, co je před prvním program-item
            for i, sibling in enumerate(siblings[:5]):
                class_attr = sibling.get("class", [])
                text_preview = sibling.get_text(strip=True)[:60]
                print(f"  {i}. class={class_attr} text={text_preview}")
            break
        parent = parent.parent

print("\n=== Hledání kalendáře/data v data- atributech ===\n")

# Hledej všechny elementy s data- atributy
elements_with_data_attrs = soup.find_all(True)
data_attrs = set()
for elem in elements_with_data_attrs:
    for attr in elem.attrs:
        if attr.startswith("data-") and "date" in attr.lower():
            data_attrs.add((attr, elem.get(attr, "")[:50]))

if data_attrs:
    for attr, val in sorted(data_attrs):
        print(f"  {attr}: {val}")
else:
    print("  Žádné data-date atributy nenalezeny")

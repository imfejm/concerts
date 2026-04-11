#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explore Forum Karlín HTML structure
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

url = "https://www.forumkarlin.cz/program/"
r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

# Hledaj hlavní kontejnery
print("=== Hledání hlavních prvků ===\n")

# Podívej se na články
articles = soup.find_all("article")
print(f"Počet <article> prvků: {len(articles)}")

# Hledaj .event nebo .program
events = soup.find_all("div", class_="event")
print(f"Počet <div class='event'> prvků: {len(events)}")

# Hledaj třídy s "item" v názvu
items = soup.find_all(class_="item")
print(f"Počet prvků s class='item': {len(items)}")

# Hledaj třídy s "card" v názvu
cards = soup.find_all(class_="card")
print(f"Počet prvků s class='card': {len(cards)}")

# Hledaj třídy s "program" v názvu
program = soup.find_all(class_="program")
print(f"Počet prvků s class='program': {len(program)}")

# Pokud je málo, zkus najít všechny dividers nebo nadpisy
divs_with_img = soup.find_all("div", recursive=True)
divs_with_img = [d for d in divs_with_img if d.find("img")]
print(f"Počet <div> s obrázky: {len(divs_with_img)}")

print("\n=== Hledání selektorů s daty ===\n")

# Hledaj první element s nadpisem a datem
for i, elem in enumerate(soup.find_all(["h2", "h3", "h4"]), 1):
    if i <= 5:
        print(f"{i}. {elem.name}: {elem.get_text(strip=True)[:60]}")

print("\n=== Hledání datumů ===\n")

# Hledaj prvky se slovy jako "duben", "květen" atd.
text = soup.get_text()
import re
dates = re.findall(r'\d{1,2}\.\s*\d{1,2}\.(\s*\d{4})?', text)
print(f"Počet nalezených datumů: {len(set(dates))}")
for d in sorted(set(dates))[:5]:
    print(f"  - {d}")

print("\n=== Prozkoumání struktury prvního event-like prvku ===\n")

# Zkus encontrar strukturu
main = soup.find("main") or soup.find("div", class_="content")
if main:
    print(f"Nalezen {main.name}")
    for child in main.find_all(recursive=False)[:3]:
        print(f"  - {child.name}")

# Pokud máš seznam, pokušej se porozumět struktuře
if divs_with_img:
    print(f"\nPrvní div s obrázkem:")
    first = divs_with_img[0]
    print(f"  Třída: {first.get('class')}")
    print(f"  Obrázek: {first.find('img').get('src', '')[:80]}")
    print(f"  Text: {first.get_text(strip=True)[:100]}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explore Jazz Dock HTML structure
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

url = "https://www.jazzdock.cz/cs/program"
r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

print("=== Hledání hlavních prvků ===\n")

# Hledej základní struktury
events_divs = soup.find_all("div", class_="event")
print(f"Počet <div class='event'> prvků: {len(events_divs)}")

events_li = soup.find_all("li", class_="event")
print(f"Počet <li class='event'> prvků: {len(events_li)}")

articles = soup.find_all("article")
print(f"Počet <article> prvků: {len(articles)}")

# Hledej třídy s "program" v názvu
program_items = soup.find_all(class_="program-item")
print(f"Počet prvků s class='program-item': {len(program_items)}")

# Hledej třídy s "event-item" v názvu
event_items = soup.find_all(class_="event-item")
print(f"Počet prvků s class='event-item': {len(event_items)}")

# Hledej všechny divy
divs = soup.find_all("div", recursive=True, limit=100)
print(f"Samplování prvních 100 divů - nalezeno {len(divs)}")

print("\n=== Hledání selektorů s nadpisy ===\n")

# Hledej h2, h3, h4
for tag in ["h2", "h3", "h4"]:
    elements = soup.find_all(tag)
    print(f"Počet <{tag}> prvků: {len(elements)}")
    if elements:
        for i, elem in enumerate(elements[:3], 1):
            text = elem.get_text(strip=True)[:60]
            print(f"  {i}. {text}")

print("\n=== Hledání dat a obrázků ===\n")

# Hledej prvky s daty
links = soup.find_all("a", href=True)
print(f"Počet <a> odkazů: {len(links)}")

imgs = soup.find_all("img")
print(f"Počet <img> prvků: {len(imgs)}")
if imgs:
    for i, img in enumerate(imgs[:3], 1):
        src = img.get("src", "")[:60]
        alt = img.get("alt", "")[:40]
        print(f"  {i}. src={src} alt={alt}")

print("\n=== Hledání celého obsahu ===\n")

# Najdi main content
main = soup.find("main")
if main:
    print(f"Nalezena značka <main>")
    # Podívej się na strukturu
    children = main.find_all(recursive=False)
    print(f"Přímých potomků: {len(children)}")
    for i, child in enumerate(children[:5], 1):
        print(f"  {i}. {child.name}")

# Pokud je obsah v sekci
section = soup.find("section")
if section:
    print(f"\nNalezena značka <section>")
    # Najdi seznam položek
    items = section.find_all(["div", "article", "li"])
    print(f"Položek v sekci: {len(items)}")

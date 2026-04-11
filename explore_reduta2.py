#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed exploration of Reduta Jazz Club structure
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

url = "https://www.redutajazzclub.cz/program-cs"
r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

# Hledej vše co obsahuje text o programu
print("=== Hledání relevantních prvků ===\n")

# Hledej všechny divy s určitými třídami
all_divs = soup.find_all("div")
print(f"Celkem divů: {len(all_divs)}")

# Hledej divy s specifickými třídami
class_set = set()
for div in all_divs:
    classes = div.get("class", [])
    if classes:
        class_set.update(classes)

print(f"Všechny CSS třídy divů: {sorted(class_set)[:20]}")

# Podívej se na seznam
print("\n=== Obsah UL ===\n")

ul_lists = soup.find_all("ul")
for i, ul in enumerate(ul_lists[:3], 1):
    print(f"UL {i}:")
    lis = ul.find_all("li")
    print(f"  Počet LI: {len(lis)}")
    for j, li in enumerate(lis[:3], 1):
        text = li.get_text(strip=True)[:80]
        print(f"    {j}. {text}")

# Hledej všechny a prvky (odkazy)
print("\n=== Odkazy ===\n")

links = soup.find_all("a")
print(f"Celkem odkazů: {len(links)}")

# Filtruj odkazy s "program" nebo "event"
relevant_links = [a for a in links if "program" in a.get("href", "").lower() or "event" in a.get("href", "").lower()]
print(f"Relevantních odkazů: {len(relevant_links)}")
for i, link in enumerate(relevant_links[:5], 1):
    href = link.get("href", "")
    text = link.get_text(strip=True)[:60]
    print(f"  {i}. href={href} text={text}")

# Hledej img prvky v kombinaci s ostatními
print("\n=== Obrázky v kontextu ===\n")

imgs = soup.find_all("img")
for i, img in enumerate(imgs[:3], 1):
    src = img.get("src", "")
    alt = img.get("alt", "")
    parent = img.parent
    parent_class = parent.get("class", [])
    parent_text = parent.get_text(strip=True)[:60]
    print(f"Img {i}:")
    print(f"  src={src[:60]}")
    print(f"  alt={alt[:60]}")
    print(f"  parent={parent.name} class={parent_class}")
    print(f"  parent text={parent_text}")

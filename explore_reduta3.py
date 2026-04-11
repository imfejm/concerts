#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explore date-based divs in Reduta
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

url = "https://www.redutajazzclub.cz/program-cs"
r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

# Hledej divy s třídami jako d01042026 (date format: ddMMYYYY)
date_pattern = re.compile(r'^d\d{8}$')
date_divs = []

for div in soup.find_all("div"):
    classes = div.get("class", [])
    for cls in classes:
        if date_pattern.match(cls):
            date_divs.append(div)
            break

print(f"Nalezeno {len(date_divs)} divů s datumem\n")

if date_divs:
    print("=== První div s datem ===\n")
    first = date_divs[0]
    
    classes = first.get("class", [])
    print(f"Třídy: {classes}")
    
    # Najdi datumovou část
    date_class = [c for c in classes if date_pattern.match(c)][0]
    print(f"Datum klíč: {date_class}")
    
    # Parsuj datum
    date_str = date_class[1:]  # Odstraň 'd' prefix
    day = date_str[0:2]
    month = date_str[2:4]
    year = date_str[4:8]
    print(f"Parsované datum: {day}.{month}.{year}")
    
    print(f"\nHTML obsah:\n{str(first)[:1500]}")
    
    print("\n=== Podívej se na event prvky uvnitř ===\n")
    
    # Najdi wszystkie child divy
    child_divs = first.find_all("div", recursive=False)
    print(f"Přímých potomků: {len(child_divs)}")
    
    for i, child in enumerate(child_divs[:3], 1):
        child_classes = child.get("class", [])
        child_text = child.get_text(strip=True)[:100]
        print(f"  {i}. class={child_classes} text={child_text}")
    
    # Hledej všechny a prvky (akcí)
    all_links = first.find_all("a")
    print(f"\nOdkazy v tomto datu: {len(all_links)}")
    
    for i, link in enumerate(all_links[:3], 1):
        href = link.get("href", "")
        text = link.get_text(strip=True)
        img = link.find("img")
        img_src = img.get("src", "") if img else ""
        print(f"  {i}. href={href[:60]} text={text[:60]} has_img={bool(img)}")
        if img:
            print(f"      img_src={img_src[:60]}")

print(f"\n=== Všechny datumové divy (prvních 10) ===\n")
for i, div in enumerate(date_divs[:10], 1):
    classes = div.get("class", [])
    date_class = [c for c in classes if date_pattern.match(c)][0]
    day = date_class[1:3]
    month = date_class[3:5]
    year = date_class[5:9]
    
    # Počet akcí
    links = div.find_all("a")
    event_links = [l for l in links if l.find("img")]
    
    print(f"{i}. {day}.{month}.{year} - {len(event_links)} akcí")

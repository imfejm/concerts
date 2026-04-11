#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find date information in Jazz Dock events
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

program_items = soup.find_all("div", class_="program-item")

print("=== Hledání datumů ===\n")

for i, item in enumerate(program_items[:3], 1):
    print(f"Event {i}:")
    
    # Nadpis
    h2 = item.find("h2")
    title = h2.get_text(strip=True) if h2 else ""
    print(f"  Nadpis: {title[:50]}")
    
    # Podívej se na všechny meta tagy
    metas = item.find_all("meta")
    print(f"  Meta tagy:")
    for meta in metas:
        name = meta.get("itemprop", meta.get("name", ""))
        content = meta.get("content", "")
        if name and content:
            print(f"    {name}: {content[:80]}")
    
    # Podívej se na všechny data-* atributy
    if item.get("data-packages"):
        print(f"  data-packages: {item.get('data-packages')}")
    
    # Najdi všechny texty/data v div.in
    in_div = item.find("div", class_="in")
    if in_div:
        # Hledej všechny divs s specifickými třídami
        date_divs = in_div.find_all("div")
        for div in date_divs:
            class_attr = div.get("class", [])
            if any("date" in str(c) for c in class_attr):
                print(f"  Found date div: {div.get_text(strip=True)[:100]}")
        
        # Hledej i v text obsahu
        text = in_div.get_text(" ", strip=True)
        # Hledej vzor s dnem/měsícem
        dates = re.findall(r'(\d{1,2}\.\s*\d{1,2}\.|\d{1,2}\s+[a-zá-ý]+)', text, re.I)
        if dates:
            print(f"  Nalezené datumové vzory: {dates[:3]}")
    
    print()

print("\n=== Nalezená data na stránce ===\n")

# Hledej všechny časy na stránce
all_text = soup.get_text()
times = re.findall(r'(\d{1,2}):(\d{2})', all_text)
print(f"Časy: {sorted(set(times))[:10]}")

# Hledej datumové vzory
dates_found = re.findall(r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})', all_text)
print(f"Datumové vzory (DD.M.YYYY): {sorted(set(dates_found))[:10]}")

# Hledaj měsíce
months_cz = ['ledna', 'února', 'března', 'dubna', 'května', 'června',
             'července', 'srpna', 'září', 'října', 'listopadu', 'prosince']
for month in months_cz:
    if month in all_text.lower():
        # Hledaj kontext
        matches = re.findall(f'(\\d{{1,2}}\\s+{month})', all_text, re.IGNORECASE)
        if matches:
            print(f"  Nalezeno: {month} - {matches[-1]}")

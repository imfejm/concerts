#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explore Reduta Jazz Club HTML structure
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

print("=== Hledání hlavních prvků ===\n")

# Hledej různé prvky
events = soup.find_all("div", class_="event")
print(f"Počet <div class='event'> prvků: {len(events)}")

items = soup.find_all("div", class_="item")
print(f"Počet <div class='item'> prvků: {len(items)}")

performances = soup.find_all(class_="performance")
print(f"Počet prvků s class='performance': {len(performances)}")

program_items = soup.find_all(class_="program-item")
print(f"Počet prvků s class='program-item': {len(program_items)}")

concerts = soup.find_all(class_="concert")
print(f"Počet prvků s class='concert': {len(concerts)}")

articles = soup.find_all("article")
print(f"Počet <article> prvků: {len(articles)}")

print("\n=== Hledání datumů ===\n")

# Hledej datumové vzory
import re
all_text = soup.get_text()
dates = re.findall(r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})', all_text)
print(f"Nalezené datumové vzory: {sorted(set(dates))[:5]}")

times = re.findall(r'(\d{1,2}):(\d{2})', all_text)
print(f"Nalezené časy: {sorted(set(times))[:5]}")

print("\n=== Hledání nadpisů ===\n")

for tag in ["h1", "h2", "h3", "h4"]:
    headers = soup.find_all(tag)
    print(f"Počet <{tag}> prvků: {len(headers)}")
    if headers:
        for i, h in enumerate(headers[:3], 1):
            text = h.get_text(strip=True)[:60]
            print(f"  {i}. {text}")

print("\n=== Hledání obrázků ===\n")

imgs = soup.find_all("img")
print(f"Celkem obrázků: {len(imgs)}")
for i, img in enumerate(imgs[:5], 1):
    src = img.get("src", "")[:60]
    alt = img.get("alt", "")[:40]
    print(f"  {i}. src={src} alt={alt}")

print("\n=== Hledání struktury ===\n")

# Podívej se na main content
main = soup.find("main")
if main:
    print("Nalezena <main> značka")
    children = main.find_all(recursive=False)
    print(f"Přímých potomků: {len(children)}")
    for i, child in enumerate(children[:5], 1):
        class_attr = child.get("class", [])
        text_preview = child.get_text(strip=True)[:40]
        print(f"  {i}. {child.name} class={class_attr} text={text_preview}")

# Podívej se na seznam
ul_lists = soup.find_all("ul")
ol_lists = soup.find_all("ol")
print(f"\nSeznam prvků: {len(ul_lists)} <ul>, {len(ol_lists)} <ol>")

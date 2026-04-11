#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed exploration of Forum Karlín events
"""

import requests
from bs4 import BeautifulSoup
import re
from pprint import pprint

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

# Najdi všechny .event prvky
events = soup.find_all("div", class_="event")
print(f"Počet events: {len(events)}\n")

if events:
    print("=== Struktura prvního event prvku ===\n")
    first = events[0]
    
    print(f"HTML:\n{first.prettify()[:1000]}\n")
    
    # Zkus extrahovat jednotlivé prvky
    print("=== Extrahované údaje ===\n")
    
    # Nadpis
    h3 = first.find("h3")
    title = h3.get_text(strip=True) if h3 else ""
    print(f"Nadpis (h3): {title}")
    
    # Datum
    date_div = first.find("div", class_="date")
    date_text = date_div.get_text(strip=True) if date_div else ""
    print(f"Datum: {date_text}")
    
    # Čas
    time_div = first.find("div", class_="time")
    time_text = time_div.get_text(strip=True) if time_div else ""
    print(f"Čas: {time_text}")
    
    # Obrázek
    img = first.find("img")
    image = img.get("src", "") if img else ""
    print(f"Obrázek: {image[:80]}")
    
    # Link
    link = first.find("a")
    href = link.get("href", "") if link else ""
    print(f"Link: {href}")
    
    # Opis/popis
    perex = first.find("div", class_="perex")
    perex_text = perex.get_text(strip=True) if perex else ""
    print(f"Popis: {perex_text[:100]}")
    
    # Kategorie
    category_div = first.find("div", class_="category")
    category = category_div.get_text(strip=True) if category_div else ""
    print(f"Kategorie: {category}")

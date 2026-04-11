#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test scraping Forum Karlín
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

url = "https://www.forumkarlin.cz/program/"
r = requests.get(url, headers=HEADERS, timeout=15)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

# Najdi všechny .event prvky
events = soup.find_all("div", class_="event")
print(f"Počet events: {len(events)}\n")

scraped = []

for i, event_div in enumerate(events[:3], 1):
    try:
        # Nadpis
        h3 = event_div.find("h3")
        title = h3.get_text(strip=True) if h3 else ""
        
        # Datum - je v <div class="date">
        date_div = event_div.find("div", class_="date")
        date_text = date_div.get_text(strip=True) if date_div else ""
        
        # Parsuj datum - "12. 4. 2026ne" -> extrahuj čísla
        date_match = re.search(r'(\d{1,2})\.\s+(\d{1,2})\.\s+(\d{4})', date_text)
        if date_match:
            day = date_match.group(1)
            month = date_match.group(2)
            year = date_match.group(3)
            date_str = f"{day}.{month}.{year}"
        else:
            date_str = ""
        
        # Obrázek - <img src="...">
        img = event_div.find("img")
        if img:
            img_src = img.get("src", "")
            # Odstraň velikost z URL - -300x150.jpg -> .jpg
            image = re.sub(r'-\d+x\d+\.', '.', img_src)
        else:
            image = ""
        
        # Link
        link = event_div.find("a", href=True)
        href = link.get("href", "") if link else ""
        
        # Popis - text pod nadpisem
        p = event_div.find("p")
        description = p.get_text(strip=True) if p else ""
        
        # Čas - zatím není
        time_str = ""
        
        scraped.append({
            "title": title,
            "date": date_str,
            "time": time_str,
            "venue": "Forum Karlín",
            "category": "hudba",
            "url": href,
            "image": image,
            "description": description,
        })
        
        print(f"{i}. {title}")
        print(f"   Datum: {date_str}")
        print(f"   Obrázek: {image[:60]}...")
        print(f"   URL: {href}")
        print(f"   Popis: {description[:60]}")
        print()
        
    except Exception as e:
        print(f"Chyba: {e}")

print(f"Celkem scraped: {len(scraped)}")

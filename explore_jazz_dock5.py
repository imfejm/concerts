#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test scraping first Jazz Dock event detail page to get the date
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

if program_items:
    first = program_items[0]
    
    # Najdi link na detail stránku
    link = first.find("a", href=True)
    detail_url = link.get("href", "")
    
    if detail_url:
        if not detail_url.startswith("http"):
            detail_url = "https://www.jazzdock.cz" + detail_url
        
        print(f"Detail URL: {detail_url}\n")
        
        # Stáhni detail stránku
        try:
            r2 = requests.get(detail_url, headers=HEADERS, timeout=15)
            r2.raise_for_status()
            
            soup2 = BeautifulSoup(r2.text, "html.parser")
            
            # Hledej datum na detail stránce
            all_text = soup2.get_text()
            
            # Hledej datum vzory
            dates = re.findall(r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})', all_text)
            print(f"Nalezené datumové vzory na detail stránce: {sorted(set(dates))}")
            
            # Hledej meta informace se schématem
            metas = soup2.find_all("meta", {"itemprop": "startDate"})
            print(f"\nMeta tagy se startDate:")
            for meta in metas:
                print(f"  {meta.get('content', '')}")
            
            # Hledej text s datem a časem
            date_patterns = re.findall(r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s+.*?(\d{1,2}:\d{2})', all_text)
            print(f"\nDatum + čas páry: {date_patterns[:3]}")
            
            # Hledej všechno s .4.
            april_dates = re.findall(r'(\d{1,2}\.\s*4\.\s*\d{4})', all_text)
            print(f"Dubnové datumové vzory: {sorted(set(april_dates))[:5]}")
            
        except Exception as e:
            print(f"Chyba při stahování detail stránky: {e}")

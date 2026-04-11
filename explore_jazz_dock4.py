#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full HTML inspection for Jazz Dock event
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

program_items = soup.find_all("div", class_="program-item")

if program_items:
    print("=== FULL HTML OF FIRST EVENT ===\n")
    first = program_items[0]
    html_str = str(first)
    print(html_str[:2000])
    print("\n...\n")
    print(html_str[-1000:])

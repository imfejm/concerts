#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    print("Stahování https://atriumzizkov.cz/program/...")
    r = requests.get('https://atriumzizkov.cz/program/', headers=headers, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    
    print("✓ Stránka stažena\n")
    
    # Zkus různé selektory
    print("=== Hledám event elementy ===")
    for selector in ['.event', '[class*=event]', '[class*=program]', 'article', '.card', '.item', '.akce', '.event-item']:
        items = soup.select(selector)
        if items:
            print(f'Nalezeno {len(items)} items se selektorem: {selector}')
            # Vytiskni první element (zkrácenos)
            first = str(items[0])[:300]
            print(f'  Příklad: {first}...\n')
            break
    
    # Najdi všechny divy s třídy, které obsahují "event" nebo "program"
    print("\n=== Třídy s 'event' nebo 'program' ===")
    divs = soup.find_all('div', class_=True)
    interesting_classes = set()
    for d in divs:
        cls = d.get('class', [])
        cls_str = ' '.join(cls)
        if any(term in cls_str.lower() for term in ['event', 'program', 'akce', 'card', 'item']):
            interesting_classes.add(cls_str)
    
    for cls in sorted(list(interesting_classes))[:10]:
        print(f'  - {cls}')
    
    # Hledej obrázky
    print("\n=== Hledám obrázky ===")
    imgs = soup.find_all('img')
    print(f'Celkem obrázků: {len(imgs)}')
    
    # Hledej data atributy
    print("\n=== Data atributy ===")
    elements_with_data = soup.find_all(attrs={'data-event': True}) or soup.find_all(attrs={'data-id': True})
    print(f'Elementy s data atributy: {len(elements_with_data)}')
    
    # Zkus JSON LD
    print("\n=== JSON LD struktury ===")
    scripts = soup.find_all('script', type='application/ld+json')
    print(f'LD+JSON skriptu: {len(scripts)}')
    if scripts:
        try:
            data = json.loads(scripts[0].string)
            print(f'  Typ: {data.get("@type", "unknown")}')
        except:
            pass
    
    # Hledej hlavní struktury
    print("\n=== Nadpisy ===")
    for tag in ['h1', 'h2', 'h3']:
        titles = soup.find_all(tag)[:3]
        if titles:
            print(f'{tag}: {[t.get_text(strip=True)[:40] for t in titles]}')
    
    # Pokus se najít container s eventy
    print("\n=== Hledám kontejner programu ===")
    main = soup.find('main') or soup.find('section') or soup.find('div', class_=lambda x: x and 'program' in x.lower())
    if main:
        print(f'Nalezeno main/section/program, HTML délka: {len(str(main))}')
        # Hledej všechny child divy
        child_divs = main.find_all('div', recursive=False)
        print(f'Child divů: {len(child_divs)}')
    
except Exception as e:
    import traceback
    print(f'Chyba: {e}')
    traceback.print_exc()

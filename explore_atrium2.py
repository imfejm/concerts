#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    print("Stahování https://atriumzizkov.cz/program/...")
    r = requests.get('https://atriumzizkov.cz/program/', headers=headers, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    
    print("✓ Stránka stažena\n")
    
    # Hledej loop-item
    print("=== Hledám loop-item elementy ===")
    items = soup.find_all('div', class_='loop-item')
    print(f'Nalezeno: {len(items)} loop-item')
    
    if items:
        # Zkus první item
        first = items[0]
        print(f'\nPrvní item HTML ({len(str(first))} bytů):\n')
        print(str(first)[:1500])
        
        # Hledej klíčové elementy v prvním itemě
        print("\n\n=== Struktura prvního itemu ===")
        
        # Hledej odkaz
        link = first.find('a', href=True)
        print(f'Odkaz: {link.get("href") if link else "Nenalezeno"}')
        
        # Hledej nadpis
        title = first.find('h3') or first.find('h2') or first.find('h4')
        if title:
            print(f'Nadpis: {title.get_text(strip=True)[:100]}')
        
        # Hledej obrázek
        img = first.find('img')
        if img:
            print(f'Obrázek src: {img.get("src", "NO SRC")}')
            print(f'Obrázek alt: {img.get("alt", "NO ALT")}')
        
        # Hledej datum/čas
        for attr in ['data-date', 'data-time', 'data-start']:
            val = first.get(attr)
            if val:
                print(f'{attr}: {val}')
        
        # Zkus najít všechny texty
        print("\nVšechen text v prvním itemu:")
        text = first.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines[:20]:
            print(f'  - {line[:80]}')
    
    # Hledej input fields nebo hidden data
    print("\n\n=== Hledám data v atributech ===")
    inputs = soup.find_all('input', type='hidden')
    if inputs:
        for inp in inputs[:3]:
            print(f'  {inp.get("name", "?")}={inp.get("value", "?")}')
    
except Exception as e:
    import traceback
    print(f'Chyba: {e}')
    traceback.print_exc()

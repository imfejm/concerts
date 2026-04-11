#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
# Najdi Atrium Žižkov akce
atrium_events = [e for e in data['events'] if e.get('venue') == 'Atrium Žižkov']
print(f'Atrium Žižkov akcí: {len(atrium_events)}\n')

# Vyprintuj první 5
for event in atrium_events[:5]:
    print(f'Nadpis: {event["title"]}')
    print(f'  Datum: {event["date"]}, čas: {event["time"]}')
    print(f'  URL: {event["url"][:60]}...')
    print(f'  Obrázek: {event["image"][:70] if event["image"] else "(žádný)"}...')
    print()

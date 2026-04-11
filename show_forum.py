import json
import pprint

with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

forum = [e for e in data['events'] if e.get('venue') == 'Forum Karlín']

if forum:
    print("📌 Příklad Forum Karlín akce:\n")
    e = forum[0]
    print(f"Název: {e['title']}")
    print(f"Datum: {e['date']}")
    print(f"Čas: {e.get('time', '(neuvedeno)')}")
    print(f"Místo: {e['venue']}")
    print(f"Kategorie: {e['category']}")
    print(f"URL: {e['url']}")
    print(f"Obrázek: {e['image']}")
    print(f"\nCelkem Forum Karlín akcí: {len(forum)}")

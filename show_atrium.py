import json

with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

atrium = [e for e in data['events'] if e.get('venue') == 'Atrium Žižkov']

if atrium:
    print("Příklad Atrium akce:")
    e = atrium[0]
    print(f"  Název: {e.get('title')}")
    print(f"  Datum: {e.get('date')}")
    print(f"  Čas: {e.get('time')}")
    print(f"  Místo: {e.get('venue')}")
    print(f"  Kategorie: {e.get('category')}")
    print(f"  URL: {e.get('url')}")
    print(f"  Obrázek: {e.get('image')[:50]}..." if e.get('image') else "  Obrázek: (žádný)")

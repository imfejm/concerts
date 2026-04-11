import json

with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

atrium = [e for e in data['events'] if e.get('venue') == 'Atrium Žižkov']

print(f'\n✅ Atrium Žižkov akcí: {len(atrium)}\n')
for i, e in enumerate(atrium, 1):
    time_str = f" v {e['time']}" if e.get('time') else ""
    print(f"{i}. {e['title']}")
    print(f"   Datum: {e['date']}{time_str}")
    print(f"   Kategorie: {e['category']}")
    print(f"   URL: {e['url']}")
    print()

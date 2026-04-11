import json

with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

forum = [e for e in data['events'] if e.get('venue') == 'Forum Karlín']

print(f'✅ Forum Karlín akcí: {len(forum)}\n')
if forum:
    for i, e in enumerate(forum[:5], 1):
        print(f"{i}. {e['title']}")
        print(f"   Datum: {e['date']}")
        print(f"   Obrázek: {e['image'][:50]}...")
        print()
else:
    print("Žádné akce!")

print(f"\nCelkem akcí v JSON: {len(data['events'])}")

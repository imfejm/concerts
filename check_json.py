import json

with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total events: {data['count']}")

atrium = [e for e in data['events'] if e.get('venue') == 'Atrium Žižkov']
print(f"Atrium events: {len(atrium)}")

for e in atrium:
    print(f"  - {e['title']} ({e['date']})")

# Also check total count
print(f"\nTotal events in file: {len(data['events'])}")

import json

data = json.load(open('concerts.json', 'r', encoding='utf-8'))
print(f'Celkem akcí: {data["count"]}')

jazz = [e for e in data['events'] if e.get('venue') == 'Jazz Dock']
print(f'Jazz Dock akcí: {len(jazz)}')

forum = [e for e in data['events'] if e.get('venue') == 'Forum Karlín']
print(f'Forum Karlín akcí: {len(forum)}')

atrium = [e for e in data['events'] if e.get('venue') == 'Atrium Žižkov']
print(f'Atrium Žižkov akcí: {len(atrium)}')

if jazz:
    print('\nPrvní Jazz Dock akce:')
    e = jazz[0]
    print(f'  Název: {e["title"]}')
    print(f'  Datum: {e["date"]}')
    print(f'  Čas: {e["time"]}')
    print(f'  Kategorie: {e["category"]}')

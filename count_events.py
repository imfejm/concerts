import json

data = json.load(open('concerts.json', 'r', encoding='utf-8'))
print(f'Celkem akcí: {data["count"]}')

mf = [e for e in data['events'] if e.get('venue') == 'MeetFactory']
print(f'MeetFactory akcí: {len(mf)}')

forum = [e for e in data['events'] if e.get('venue') == 'Forum Karlín']
print(f'Forum Karlín akcí: {len(forum)}')

atrium = [e for e in data['events'] if e.get('venue') == 'Atrium Žižkov']
print(f'Atrium Žižkov akcí: {len(atrium)}')

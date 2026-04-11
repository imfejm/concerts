"""
Merge Reduta Jazz Club concerts into the main concerts.json
"""

import json
from datetime import datetime

# Load existing concerts
with open('concerts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Load Reduta concerts
with open('concerts_full.json', 'r', encoding='utf-8') as f:
    reduta_concerts = json.load(f)

# Convert Reduta format to concerts.json format
new_events = []
for concert in reduta_concerts:
    # Extract time from datetime
    time = ""
    if concert.get('datetime'):
        time = concert['datetime'].split('T')[1] if 'T' in concert['datetime'] else ""
        time = time[:5]  # HH:MM
    
    event = {
        'title': concert.get('title', ''),
        'date': concert.get('date', ''),
        'time': time,
        'venue': 'Reduta Jazz Club',
        'category': 'hudba',
        'url': concert.get('link', ''),
        'image': concert.get('image_url', '') if concert.get('image_url') != 'N/A' else ''
    }
    new_events.append(event)

# Merge with existing events
all_events = data.get('events', []) + new_events

# Sort by date
def parse_date(date_str):
    try:
        parts = date_str.split('.')
        return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except:
        return datetime(9999, 1, 1)

all_events_sorted = sorted(all_events, key=lambda x: parse_date(x.get('date', '')))

# Update data
data['events'] = all_events_sorted
data['count'] = len(all_events_sorted)
data['updated'] = datetime.now().isoformat()

# Save
with open('concerts.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ Added {len(new_events)} Reduta concerts")
print(f"✓ Total events: {len(all_events_sorted)}")
print(f"✓ concerts.json updated")

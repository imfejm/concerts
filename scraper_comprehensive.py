"""
Comprehensive scraper for Reduta Jazz Club
Handles both single and multiple events per day
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

url = "https://www.redutajazzclub.cz/program-cs"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Fetching page...")
response = requests.get(url, headers=headers)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.content, 'html.parser')

# Find all divs with date class pattern
date_divs = soup.find_all('div', class_=re.compile(r'.*\sd\d{8}.*'))

print(f"Found {len(date_divs)} date divs\n")

events = []

for date_div in date_divs:
    # Extract date from class
    classes = date_div.get('class', [])
    date_class = None
    for cls in classes:
        if re.match(r'^d\d{8}$', cls):
            date_class = cls
            break
    
    if not date_class:
        continue
    
    # Parse date
    date_str = date_class[1:]
    day = date_str[0:2]
    month = date_str[2:4]
    year = date_str[4:8]
    date_formatted = f"{day}.{month}.{year}"
    
    # Find all event containers within this date div
    # These can be either:
    # 1. Direct children divs with 'col s12 row' class (for single events)
    # 2. Direct children divs with 'progitem col s12 row' class (for multiple events)
    
    event_containers = date_div.find_all('div', class_=['progitem'], recursive=False)
    
    if not event_containers:
        # Try finding col s12 row divs (single event case)
        event_containers = date_div.find_all('div', class_=['col'], recursive=False)
        event_containers = [e for e in event_containers if 's12' in e.get('class', []) and 'row' in e.get('class', [])]
    
    # If still nothing found, skip
    if not event_containers:
        continue
    
    # Extract data from each event container
    for event_elem in event_containers:
        # Check if this is actually an event (not empty)
        if not event_elem.find('div', class_='progheader'):
            continue
        
        # Get datetime
        data_time = event_elem.get('data-time', '')
        
        # Get title
        title_elem = event_elem.find('div', class_='progheader')
        title = title_elem.text.strip() if title_elem else "N/A"
        
        # Get performer/artist
        performer_elem = event_elem.find('div', class_='progabouttxt')
        performer = performer_elem.text.strip() if performer_elem else ""
        
        # Get description
        desc_elem = event_elem.find('div', class_='progaddtext')
        if desc_elem:
            # Get text from paragraphs
            paragraphs = desc_elem.find_all('p')
            description = ' '.join([p.text.strip() for p in paragraphs]) if paragraphs else desc_elem.text.strip()
        else:
            description = ""
        
        # Get link (from title or image)
        link = "N/A"
        title_link = event_elem.find('div', class_='progheader').find('a')
        if title_link:
            link = title_link.get('href', 'N/A')
        else:
            # Try to find any link in the event
            any_link = event_elem.find('a', href=True)
            if any_link:
                link = any_link.get('href', 'N/A')
        
        # Get image
        img_elem = event_elem.find('img')
        image_url = img_elem.get('src', 'N/A') if img_elem else "N/A"
        
        event = {
            'date': date_formatted,
            'datetime': data_time,
            'title': title,
            'performer': performer,
            'description': description,
            'link': link,
            'image_url': image_url
        }
        
        events.append(event)

print(f"Extracted {len(events)} events\n")

# Sort by datetime
events_sorted = sorted(events, key=lambda x: x['datetime'] if x['datetime'] else '')

# Show sample
print("Sample of extracted events:")
for event in events_sorted[:10]:
    print(f"- {event['date']} {event['datetime']}: {event['title']}")

# Save to JSON
with open('concerts_full.json', 'w', encoding='utf-8') as f:
    json.dump(events_sorted, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(events)} events to concerts_full.json")

# Also save a summary
summary = {}
for event in events_sorted:
    date = event['date']
    if date not in summary:
        summary[date] = []
    summary[date].append({
        'time': event['datetime'].split('T')[1] if 'T' in event['datetime'] else 'TBA',
        'title': event['title']
    })

with open('concerts_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Saved summary to concerts_summary.json")

"""
Fixed comprehensive scraper for Reduta Jazz Club
Properly handles both single and multiple events per day
"""

import requests
from bs4 import BeautifulSoup
import json
import re

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
    
    # Determine if single or multiple events per day
    # Multiple events have 'doubleprog' class, single events don't
    is_multiple = 'doubleprog' in classes
    
    if is_multiple:
        # Multiple events: find all progitem children with first/second classes
        progitem_children = date_div.find_all('div', class_='progitem', recursive=False)
        event_containers = progitem_children
    else:
        # Single event: use col s12 row children, but get data-time from parent date_div
        col_children = date_div.find_all('div', class_='col', recursive=False)
        event_containers = [c for c in col_children if 's12' in c.get('class', []) and 'row' in c.get('class', [])]
        
        # For single events, store the parent's data-time to apply to the event
        parent_data_time = date_div.get('data-time', '')
    
    # Extract data from each event container
    for event_elem in event_containers:
        # Check if this is actually an event (has a title)
        title_elem = event_elem.find('div', class_='progheader')
        if not title_elem:
            continue
        
        # Get datetime
        if is_multiple:
            data_time = event_elem.get('data-time', '')
        else:
            data_time = parent_data_time
        
        # Get title
        title = title_elem.text.strip()
        
        # Get performer/artist
        performer_elem = event_elem.find('div', class_='progabouttxt')
        performer = performer_elem.text.strip() if performer_elem else ""
        
        # Get description
        desc_elem = event_elem.find('div', class_='progaddtext')
        if desc_elem:
            paragraphs = desc_elem.find_all('p')
            description = ' '.join([p.text.strip() for p in paragraphs]) if paragraphs else desc_elem.text.strip()
        else:
            description = ""
        
        # Get link
        link = "N/A"
        title_link = event_elem.find('div', class_='progheader').find('a')
        if title_link:
            link = title_link.get('href', 'N/A')
        else:
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
for event in events_sorted[:15]:
    time_str = event['datetime'].split('T')[1] if 'T' in event['datetime'] else 'TBA'
    print(f"- {event['date']} {time_str}: {event['title'][:60]}...")

# Save to JSON
with open('concerts_full.json', 'w', encoding='utf-8') as f:
    json.dump(events_sorted, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(events)} events to concerts_full.json")

# Create summary by date with times
summary = {}
for event in events_sorted:
    date = event['date']
    if date not in summary:
        summary[date] = []
    
    time_str = event['datetime'].split('T')[1] if 'T' in event['datetime'] else 'TBA'
    summary[date].append({
        'time': time_str,
        'title': event['title'],
        'link': event['link']
    })

with open('concerts_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Saved summary to concerts_summary.json")

# Print statistics
event_counts = {}
for event in events_sorted:
    date = event['date']
    event_counts[date] = event_counts.get(date, 0) + 1

multiple_day_events = sum(1 for count in event_counts.values() if count > 1)
single_day_events = sum(1 for count in event_counts.values() if count == 1)

print(f"\nStatistics:")
print(f"- Total events: {len(events)}")
print(f"- Days with 1 event: {single_day_events}")
print(f"- Days with 2+ events: {multiple_day_events}")

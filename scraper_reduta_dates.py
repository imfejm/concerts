"""
Scraper for Reduta Jazz Club using date-based structure
Extracts events from divs with date class (d01042026 = 01.04.2026)
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# Fetch the page
url = "https://www.redutajazzclub.cz/program-cs"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Fetching page...")
response = requests.get(url, headers=headers)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.content, 'html.parser')

# Find all divs with date class pattern (d + date)
event_divs = soup.find_all('div', class_=re.compile(r'^d\d{8}'))

print(f"Found {len(event_divs)} date divs\n")

events = []

for idx, date_div in enumerate(event_divs[:5], 1):  # First 5 for testing
    # Extract date from class
    classes = date_div.get('class', [])
    date_class = None
    for cls in classes:
        if re.match(r'^d\d{8}$', cls):
            date_class = cls
            break
    
    if not date_class:
        continue
    
    # Parse date: d01042026 -> 01.04.2026
    date_str = date_class[1:]  # Remove 'd'
    day = date_str[0:2]
    month = date_str[2:4]
    year = date_str[4:8]
    date_formatted = f"{day}.{month}.{year}"
    
    # Get data-time attribute for full datetime
    data_time = date_div.get('data-time', '')
    
    # Find all program items (akce) within this date div
    # The structure seems to be: each date div contains one or more events
    
    # Try to find event title
    title_elem = date_div.find('div', class_='progheader')
    title = title_elem.text.strip() if title_elem else "N/A"
    
    # Find description
    desc_elem = date_div.find('div', class_='progabouttxt')
    desc = desc_elem.text.strip() if desc_elem else "N/A"
    
    # Find detailed description
    detailed_desc_elem = date_div.find('div', class_='progaddtext')
    detailed_desc = detailed_desc_elem.text.strip() if detailed_desc_elem else "N/A"
    
    # Find link
    link_elem = date_div.find('a', href=True)
    link = link_elem['href'] if link_elem else "N/A"
    
    # Find image
    img_elem = date_div.find('img')
    image_url = img_elem.get('src', 'N/A') if img_elem else "N/A"
    
    event = {
        'date_class': date_class,
        'date': date_formatted,
        'datetime': data_time,
        'title': title,
        'description': desc,
        'detailed_description': detailed_desc,
        'link': link,
        'image_url': image_url
    }
    
    events.append(event)
    
    print(f"\n=== Event {idx} ({date_formatted}) ===")
    print(f"Class: {date_class}")
    print(f"Title: {title}")
    print(f"DateTime: {data_time}")
    print(f"Link: {link}")

# Save to JSON
with open('concerts_reduta_dates.json', 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=2)

print(f"\n\nSaved {len(events)} events to concerts_reduta_dates.json")

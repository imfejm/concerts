"""
Deep dive into HTML structure to understand how multiple events per day are organized
"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://www.redutajazzclub.cz/program-cs"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.content, 'html.parser')

# Find divs with date class
event_divs = soup.find_all('div', class_=re.compile(r'^d\d{8}'))

print(f"Sample of structure for dates with multiple events:\n")

# Look at the 02.04.2026 which had 2 events
for idx, date_div in enumerate(event_divs[:8]):
    classes = date_div.get('class', [])
    date_class = [cls for cls in classes if re.match(r'^d\d{8}$', cls)][0]
    
    date_str = date_class[1:]
    day = date_str[0:2]
    month = date_str[2:4]
    year = date_str[4:8]
    date_formatted = f"{day}.{month}.{year}"
    
    # Count nested divs that might be events
    rows = date_div.find_all('div', class_='row')
    
    # Find all progheader divs (each should be an event)
    program_headers = date_div.find_all('div', class_='progheader')
    
    # Find all divs with class 'col s12 row' - might be individual events
    event_containers = date_div.find_all('div', class_='col s12 row')
    
    # Find all data-time attributes
    data_times = []
    current = date_div
    for elem in date_div.find_all(attrs={'data-time': True}):
        data_times.append(elem.get('data-time', 'N/A'))
    
    print(f"Date: {date_formatted}")
    print(f"  - date_class: {date_class}")
    print(f"  - class attribute has 's12 row': {'s12 row' in ' '.join(classes)}")
    print(f"  - data-time on date_div: {date_div.get('data-time', 'NONE')}")
    print(f"  - All data-time attrs in subtree: {data_times}")
    print(f"  - progheader count: {len(program_headers)}")
    print(f"  - 'col s12 row' divs: {len(event_containers)}")
    
    # Show all direct children and their classes
    print(f"  - Direct children:")
    for i, child in enumerate(date_div.children):
        if hasattr(child, 'name') and child.name == 'div':
            child_classes = child.get('class', [])
            child_text = child.get_text(strip=True)[:100] if child.get_text(strip=True) else "[empty]"
            print(f"    {i}: class={child_classes}, text={child_text}")
    
    print()

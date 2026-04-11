"""
Debug script to understand why data-times are not being extracted
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

# Find date divs
date_divs = soup.find_all('div', class_=re.compile(r'.*\sd\d{8}.*'))

print(f"Total date divs: {len(date_divs)}\n")

# Check the first 5 divs
for i, date_div in enumerate(date_divs[:5]):
    classes = date_div.get('class', [])
    date_class = [cls for cls in classes if re.match(r'^d\d{8}$', cls)][0]
    
    date_str = date_class[1:]
    day = date_str[0:2]
    month = date_str[2:4]
    year = date_str[4:8]
    date_formatted = f"{day}.{month}.{year}"
    
    print(f"\n=== Date div {i+1}: {date_formatted} ===")
    print(f"Classes on date_div: {classes}")
    print(f"data-time on date_div itself: '{date_div.get('data-time', '')}'")
    
    # Find all progitem children
    progitem_children = date_div.find_all('div', class_='progitem', recursive=False)
    print(f"progitem children (recursive=False): {len(progitem_children)}")
    
    # Find all divs with col s12 row
    col_children = date_div.find_all('div', class_='col', recursive=False)
    col_children = [c for c in col_children if 's12' in c.get('class', []) and 'row' in c.get('class', [])]
    print(f"col s12 row children: {len(col_children)}")
    
    # Get ALL direct children
    all = list(date_div.children)
    div_children = [c for c in all if hasattr(c, 'name') and c.name == 'div']
    print(f"Total div children (all): {len(div_children)}")
    
    for j, child in enumerate(div_children):
        child_classes = child.get('class', [])
        child_data_time = child.get('data-time', '')
        print(f"  Child {j}: class={child_classes}, data-time='{child_data_time}'")

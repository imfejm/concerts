with open('scraper.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
    
# Find the line with 'if __name__ == "__main__":'
for i, line in enumerate(lines):
    if 'if __name__' in line:
        print(f'Found at line {i+1}')
        # Keep lines up to and including the main() call
        lines = lines[:i+2]
        break

with open('scraper.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
    
print(f'Soubor zkrácen na {len(lines)} řádků')
